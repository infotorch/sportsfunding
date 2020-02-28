"""

encode business names to geolocation using Google Places API

"""
import os
import sys
import pandas as pd
import geopandas as gpd
import requests
import logging
import time
import requests_cache
from shapely.geometry import Point
from geopandas.tools import sjoin

logging.basicConfig(level=logging.INFO)

requests_cache.install_cache(".geocode")

API_KEY = os.environ.get("GOOGLE_API_KEY", None)
BACKOFF_TIME = 30
QUERY_LIMIT = 0
OUTPUT_FILENAME_FOUND = "data/grants_geocoded.csv"
OUTPUT_FILENAME_MISSED = "data/grants_geocoded_missed.csv"
INPUT_FILENAME = "data/grants.csv"
ADDRESS_COLUMN_NAME = "club"
ELECTORAL_BOUNDARIES_2019 = "data/boundaries/2019/COM_ELB_region.shp"
ELECTORAL_BOUNDARIES_2016 = "data/boundaries/2016/COM_ELB.TAB"

RETURN_FULL_RESULTS = False

if not API_KEY:
    raise Exception("Require API KEY")

if not INPUT_FILENAME or not os.path.isfile(INPUT_FILENAME):
    raise Exception("Require input file, run scrape_sportsdata.py first")

if not ELECTORAL_BOUNDARIES_2016 or not os.path.isfile(ELECTORAL_BOUNDARIES_2016):
    raise Exception("Require electoral boundaries shapefile .. check README")

data = pd.read_csv(INPUT_FILENAME, encoding="utf8")

if ADDRESS_COLUMN_NAME not in data.columns:
    raise ValueError(
        "Missing Address column {} in input data".format(ADDRESS_COLUMN_NAME)
    )

addresses = data[ADDRESS_COLUMN_NAME].tolist()
# addresses = (data[ADDRESS_COLUMN_NAME] + "," + data["state"] + ", Australia").tolist()

boundaries = gpd.read_file(ELECTORAL_BOUNDARIES_2016)


def normalize_electorate(name):
    if type(name) is not str:
        return ""
    name = " ".join(map(str.capitalize, str(name).split(" ")))
    if name == "Mcmahon":
        return "McMahon"
    if name == "Eden-monaro":
        return "Eden-Monaro"
    if name == "Mcpherson":
        return "McPherson"
    if name == "Mcewen":
        return "McEwen"
    if name == "O'connor":
        return "O'Connor"
    if name == "Mcmillan":
        return "McMillan"
    return name


def get_electorate(lng, lat):
    p = Point(lng, lat)

    for _, electorate in boundaries.iterrows():
        if p.within(electorate.geometry):
            logging.debug("{} in {}".format(record["name"], electorate["Sortname"]))
            if "Elect_div" in electorate:
                return normalize_electorate(electorate["Sortname"])
            if "Sortname" in electorate:
                return normalize_electorate(electorate["Sortname"])
            logging.error("Could not find electorate in shapefile")
            return ""

    return None


def get_google_results(query, return_full_response=False):
    GOOGLE_PLACES_URL = (
        "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    )
    url_params = {
        "key": API_KEY,
        "fields": "name,types,formatted_address,geometry",
        "inputtype": "textquery",
        "input": query,
    }

    results = requests.get(GOOGLE_PLACES_URL, params=url_params).json()

    logging.debug(results)

    if not "status" in results:
        raise Exception("Invalid response")

    if results["status"] == "REQUEST_DENIED":
        raise Exception("API Key or other request denied error")

    if results["status"] == "OVER_QUERY_LIMIT":
        logging.warn("Hit Query Limit! Backing off for a bit.")
        time.sleep(5)  # sleep for 30 minutes
        return get_google_results(query)

    if results["status"] == "ZERO_RESULTS":
        raise Exception("No address returned for {}".format(query))

    if not results["status"] == "OK":
        raise Exception(
            "Bad response for query ({}): {}".format(query, results["status"])
        )

    if len(results["candidates"]) == 0:
        raise Exception("No candidate address returned for {}".format(query))

    cand = results["candidates"][0]

    output = {
        "address": cand["formatted_address"],
        "lat": cand["geometry"]["location"]["lat"],
        "lng": cand["geometry"]["location"]["lng"],
        "name": cand["name"],
        "types": (",").join(cand["types"]),
    }

    return output


results = []
missed = []
queries = 0

for index, record in data.iterrows():
    address = record[ADDRESS_COLUMN_NAME]
    logging.debug("Geocoding location %s", address)

    # assist the geolocation by providing record state and country
    address += ", " + record["state"] + ", Australia"

    # Geocode the address with google
    try:
        queries += 1
        geocode_result = get_google_results(address)
        record = {**record, **geocode_result}
        logging.debug(geocode_result)
    except Exception as e:
        # logging.exception(e)
        logging.error("No geocode result for {}".format(address))
        missed.append(
            {
                **record,
                **{
                    "address": None,
                    "lat": None,
                    "lng": None,
                    "name": None,
                    "types": None,
                    "electorate": None,
                },
            }
        )
        continue

    electorate = get_electorate(record["lng"], record["lat"])

    record = {**record, **{"electorate": electorate}}
    logging.info(
        "{} - {} found electorate {}".format(
            record["club"], record["address"], record["electorate"]
        )
    )
    results.append(record)

    if QUERY_LIMIT and QUERY_LIMIT > 0 and queries >= QUERY_LIMIT:
        logging.info("Hit query limit of {}".format(QUERY_LIMIT))
        break

    # Print status every 100 addresses
    if (len(results) + len(missed)) % 10 == 0:
        logging.info(
            "Completed {} of {} address".format(
                len(results) + len(missed), len(addresses)
            )
        )

    # Every 500 addresses, save progress to file(in case of a failure so you have something!)
    if (len(results) + len(missed)) % 100 == 0:
        pd.DataFrame(results).to_csv("{}_bak".format(OUTPUT_FILENAME_FOUND))

# All done
logging.info(
    "Finished geocoding {} addresses using {} queries, missed {}".format(
        len(results), queries, len(missed)
    )
)

if os.path.isfile("{}_bak".format(OUTPUT_FILENAME_FOUND)):
    os.remove("{}_bak".format(OUTPUT_FILENAME_FOUND))

pd.DataFrame(results).to_csv(OUTPUT_FILENAME_FOUND, encoding="utf8")
pd.DataFrame(missed).to_csv(OUTPUT_FILENAME_MISSED, encoding="utf8")

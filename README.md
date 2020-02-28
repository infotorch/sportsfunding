# Data Analysis of Australian Government 2019 Sports Grant Awards

Data analysis of sports funding awarded in 2019 prior to the election

## Scripts

- `scrape_sportsdata.py` - Scrapes all the sports funding data from the [sportsaus.gov.au](https://www.sportaus.gov.au/grants_and_funding/community_sport_infrastructure_grant_program/successful_grant_recipient_list) website.

## Geocoding Results

Results are geocoded against federal electoral boundaries shape file

Download from

https://www.aec.gov.au/Electorates/gis/files/national-esri-fe2019.zip

and unzip into `data`

## Install

Requires `Python >= 3.7` and `poetry` for package and environment management

Install poetry from:

https://python-poetry.org/docs/

```sh
$ poetry install
```

Run the environment:

```sh
$ poetry shell
```

To update the data run:

```sh
$ python climate_vote_data.py
```

To start the Jupyter notebook:

```sh
$ jupyter notebook
```

## Licenses

This product incorporates data that is:

© Commonwealth of Australia (Australian Electoral Commission) 2020

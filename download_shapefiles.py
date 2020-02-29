#!/usr/bin/env python
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

import coloredlogs
import requests
from coloredlogs import parse_encoded_styles
from fastprogress.fastprogress import master_bar, progress_bar

DEBUG = True


DOWNLOADS = [
    {
        "uri": "https://aec.gov.au/Electorates/gis/files/national-midmif-09052016.zip",
        "path": "data/boundaries/2016",
    },
    {
        "uri": "https://www.aec.gov.au/Electorates/gis/files/national-esri-fe2019.zip",
        "path": "data/boundaries/2019",
    },
]


def get_logger():
    import logging

    logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

    coloredlogs.install(
        level=logging.DEBUG if DEBUG else logging.INFO,
        logger=logger,
        fmt="%(name)s %(levelname)s %(message)s",
        level_styles=parse_encoded_styles(
            "debug=green;warning=yellow;error=red;critical=red,bold"
        ),
        # field_styles=parse_encoded_styles('debug=green;warning=yellow;error=red;critical=red,bold')
    )

    return logger


logging = get_logger()


def rm_mapinfo(dir_path):
    if not os.path.isdir(dir_path):
        dir_path = os.path.dirname(dir_path)

    remove_count = 0

    for f in os.listdir(dir_path):
        if "." in f and os.path.splitext(f.upper())[1] in [
            ".DAT",
            ".ID",
            ".IND",
            ".MAP",
            ".TAB",
        ]:
            os.remove(os.path.join(dir_path, f))
            remove_count += 1
    if remove_count:
        logging.info("Removed Mapinfo TAB file")


def has_mapinfo(dir_path):
    for file in os.listdir(dir_path):
        if file.lower().endswith(".tab"):
            return os.path.realpath(os.path.join(dir_path, file))
    return None


def to_shapefile(dir_path):
    COMMAND = "ogr2ogr"

    if not shutil.which(COMMAND):
        logging.info("ogr2ogr not installed so not converting files")
        return None

    logging.info("Found Mapinfo TAB file in directory path so converting")

    dest_path = os.path.basename(dir_path).split(".")[0]
    dest_file = os.path.join(os.path.dirname(dir_path), f"{dest_path}.shp")

    flags = ["-f", "ESRI Shapefile", dest_file, dir_path]

    r = subprocess.run([COMMAND] + flags, text=True, stdout=subprocess.PIPE)

    if r.returncode != 0:
        print(r)
        raise Exception("Bad output from intel")

    logging.info(f"Converted file to {dest_file}")

    rm_mapinfo(dir_path)

    return True


def download_file(url, retries=3, timeout=60, chunk_size=1024 * 1024, pbar=None):
    save_path = os.path.join(tempfile.mkdtemp(), url.split("/")[-1])

    logging.info("Getting {} and saving to {}".format(url, save_path))

    s = requests.Session()
    s.mount("http://", requests.adapters.HTTPAdapter(max_retries=retries))
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:71.0) Gecko/20100101 Firefox/71.0"
        }
    )
    with s.get(url, stream=True, timeout=timeout) as r:

        try:
            file_size = int(u.headers["Content-Length"])
        except:
            show_progress = False

        r.raise_for_status()
        with open(save_path, "wb") as f:
            nbytes = 0
            if show_progress:
                pbar = progress_bar(range(file_size), leave=False, parent=pbar)
            try:
                if show_progress:
                    pbar.update(0)
                for chunk in r.iter_content(chunk_size=chunk_size):
                    nbytes += len(chunk)
                    if show_progress:
                        pbar.update(nbytes)
                    f.write(chunk)
            except requests.exceptions.ConnectionError as e:
                # fname = url.split("/")[-1]

                logging.error(
                    f"Download of {url} failed after {retries} attempts with error {e}"
                )

                # @TODO faster file streaming
                # shutil.copyfileobj(r.raw, f)

    return save_path


def download(dl):
    mb = master_bar(range(10))
    download_file_path = download_file(dl["uri"], pbar=mb)

    if not os.path.isfile(download_file_path):
        logging.error("No file found at {}".format(download_file_path))
        shutil.rmtree(os.path.dirname(download_file_path))
        sys.exit(-1)

    if os.path.isdir(dl["path"]):
        shutil.rmtree(dl["path"])
        logging.info(f"Removed existing directory at {dl['path']}")

    with zipfile.ZipFile(download_file_path) as zf:
        zf.extractall(dl["path"])
        logging.info(f"Extracted zip to {dl['path']}")

    mi = has_mapinfo(dl["path"])
    if mi:
        to_shapefile(mi)

    shutil.rmtree(os.path.dirname(download_file_path))
    logging.info("Extracted to {}".format(dl["path"]))


if __name__ == "__main__":
    try:
        for d in DOWNLOADS:
            download(d)
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt. Exiting.")
    except Exception as e:
        if DEBUG:
            logging.exception(e)
        logging.error(e)

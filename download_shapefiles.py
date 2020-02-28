#!/usr/bin/env python
import os
import sys
import requests
import zipfile
import shutil
import logging
import tempfile
from pprint import pprint

logging.basicConfig(level=logging.DEBUG)

SHAPEFILE_URI = "https://www.aec.gov.au/Electorates/gis/files/national-esri-fe2019.zip"
TARGET_PATH = "data/boundaries"


def download_file(url):
    save_path = os.path.join(tempfile.mkdtemp(), url.split("/")[-1])

    logging.info("Getting {} and saving to {}".format(url, save_path))

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

    return save_path


if __name__ == "__main__":
    file_name = download_file(SHAPEFILE_URI)
    if not os.path.isfile(file_name):
        logging.error("No file found at {}".format(file_name))
        os.rmdir(os.path.dirname(file_name))
        sys.exit(-1)
    with zipfile.ZipFile(file_name) as zf:
        zf.extractall(TARGET_PATH)
    logging.info("Extracted to {}".format(TARGET_PATH))

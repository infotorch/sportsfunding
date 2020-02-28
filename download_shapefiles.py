#!/usr/bin/env python
import os
import sys
import requests
import zipfile
import shutil
import logging
import tempfile

logging.basicConfig(level=logging.DEBUG)

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


def download_file(url):
    save_path = os.path.join(tempfile.mkdtemp(), url.split("/")[-1])

    logging.info("Getting {} and saving to {}".format(url, save_path))

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

    return save_path


def download(dl):
    file_name = download_file(dl["uri"])
    if not os.path.isfile(file_name):
        logging.error("No file found at {}".format(file_name))
        os.rmdir(os.path.dirname(file_name))
        sys.exit(-1)
    with zipfile.ZipFile(file_name) as zf:
        zf.extractall(dl["path"])
    logging.info("Extracted to {}".format(dl["path"]))


if __name__ == "__main__":
    for d in DOWNLOADS:
        download(d)

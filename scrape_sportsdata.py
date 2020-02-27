import os
import re
import json
import locale
from scrapy.crawler import CrawlerProcess
from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, MapCompose, Join
from scrapy import Spider, Item, Field
from scrapy.settings import Settings

OUTPUT_FILENAME = "data/grants.csv"

locale.setlocale(locale.LC_ALL, "en_AU.UTF8")


def parse_money(money=None):
    return locale.atoi(money.strip("$")) if money else None


def parse_name(name=None):
    if not name:
        return None

    name = name.replace(os.linesep, "").replace("\r", "")
    return re.sub(r"\s+", " ", name).strip().title()


class SportsGrantItem(Item):
    club = Field()
    amount = Field()
    state = Field()
    rnd = Field()


class SportsGrantItemLoader(ItemLoader):
    default_input_processor = MapCompose(str.strip)
    default_output_processor = TakeFirst()

    club_in = MapCompose(parse_name)
    amount_in = MapCompose(str.strip, parse_money)
    rnd_in = MapCompose(int)


class SportsGrantSpider(Spider):
    name = "sportsgrant"
    allowed_domains = ["www.sportaus.gov.au"]
    start_urls = [
        "https://www.sportaus.gov.au/grants_and_funding/community_sport_infrastructure_grant_program/successful_grant_recipient_list"
    ]

    def parse(self, response):
        for sel in response.xpath("//table/tbody/tr"):
            loader = SportsGrantItemLoader(
                SportsGrantItem(), selector=sel, response=response
            )
            loader.add_xpath("club", "td[1]//text()")
            loader.add_xpath("amount", "td[2]//text()")
            loader.add_xpath("state", "td[3]//text()")
            loader.add_xpath("rnd", "td[4]//text()")
            yield loader.load_item()


settings = Settings(
    {
        # 'ITEM_PIPELINES': {
        #     '__main__.WriterPipeline': 100,
        # },
        "DOWNLOADER_MIDDLEWARES": {
            # 'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
        },
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
        "FEED_FORMAT": "csv",
        "FEED_URI": OUTPUT_FILENAME,
    }
)

if os.path.isfile(OUTPUT_FILENAME):
    os.remove(OUTPUT_FILENAME)
    print("Removed file {}".format(OUTPUT_FILENAME))

process = CrawlerProcess(settings)

process.crawl(SportsGrantSpider)
process.start()

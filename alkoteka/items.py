import scrapy


class AlkotekaItem(scrapy.Item):
    timestamp = scrapy.Field()
    RPC = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    marketing_tags = scrapy.Field()
    brand = scrapy.Field()
    section = scrapy.Field()
    price_data = scrapy.Field()
    stock = scrapy.Field()
    metadata = scrapy.Field()
    assets = scrapy.Field()

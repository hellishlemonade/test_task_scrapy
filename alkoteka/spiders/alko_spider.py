import datetime
import json
from urllib.parse import urlencode, parse_qs, urlparse

import scrapy


BASE_URL = 'https://alkoteka.com/web-api/v1/product/'
BASE_MAIN_URL = 'https://alkoteka.com/catalog/'
KRACNODAR_UUID = '4a70f9e0-46ae-11e7-83ff-00155d026416'
ROOT_CATEGORY_SLUG = 'krepkiy-alkogol'
START_URLS = [
    'https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&options%5Bcvet%5D[]=beloe&page=1&per_page=20&root_category_slug=vino',
    'https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&options%5Bcvet%5D[]=rozovoe&page=1&per_page=20&root_category_slug=vino',
    'https://alkoteka.com/web-api/v1/product?city_uuid=4a70f9e0-46ae-11e7-83ff-00155d026416&options%5Bcategories%5D[]=konyak-brendi&page=1&per_page=20&root_category_slug=krepkiy-alkogol'
]


class AlkoSpider(scrapy.Spider):
    name = 'alko_spider'
    start_urls = START_URLS

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.city_uuid = kwargs.get('city_uuid', KRACNODAR_UUID)
        self.root_slug = kwargs.get('root_slug', ROOT_CATEGORY_SLUG)

    # def __init__(self, name=None, **kwargs):
    #     super().__init__(name, **kwargs)
    #     self.start_urls_list = ('start_urls', START_URLS)
    #     self.city_uuid = kwargs.get('city_uuid', KRACNODAR_UUID)
    #     self.categories = (
    #         kwargs.get('categories', '')
    #         if kwargs.get('categories')
    #         else []
    #     )
    #     self.root_slug = kwargs.get('root_slug', 'vino')
    #     self.per_page = int(kwargs.get('per_page', 20))

    # async def start(self):
    #     """Генерация начальных запросов"""
    #     if len(self.start_urls_list) == 0:
    #         params = {
    #             'city_uuid': self.city_uuid,
    #             'page': 1,
    #             'per_page': 20,
    #             'root_category_slug': self.root_slug
    #         }
    #         if self.categories:
    #             params['options[categories][]'] = self.categories
    #         url = (
    #             'https://alkoteka.com/web-api/v1/product?'
    #             f'{urlencode(params, doseq=True)}'
    #         )
    #         yield scrapy.Request(url, callback=self.parse)
    #     else:
    #         for url in self.start_urls_list:
    #             yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        try:
            data = json.loads(response.body)
        except json.JSONDecodeError:
            self.logger.error('Ошибка загрузки JSON из ответа')
            return
        for item in data.get('results', []):
            product_slug = item.get('slug')
            if product_slug:
                product_api_url = (
                    f'{BASE_URL}{product_slug}?city_uuid={self.city_uuid}'
                )
                marketing_labels = item.get('action_labels', None)
                market_labels_list = []
                if marketing_labels:
                    for label in marketing_labels:
                        market_labels_list.append(label.get('title'))
                yield scrapy.Request(
                    product_api_url,
                    callback=self.product_parse,
                    meta={
                        'product_url': item.get('product_url'),
                        'marketing_tags': market_labels_list
                    }
                )
        if data['meta']['has_more_pages']:
            next_page = data['meta']['current_page'] + 1
            parsed_url = urlparse(response.url)
            params_dict = parse_qs(parsed_url.query)
            root_category_slug = params_dict['root_category_slug']
            params = {
                'city_uuid': self.city_uuid,
                'page': next_page,
                'per_page': 20,
                'root_category_slug': root_category_slug
            }
            next_url = (
                f'https://alkoteka.com/web-api/v1/product?{urlencode(params)}'
            )
            yield scrapy.Request(
                next_url,
                callback=self.parse
            )

    def product_parse(self, response):
        try:
            data = json.loads(response.body)
        except json.JSONDecodeError:
            self.logger.error('Ошибка загрузки JSON из ответа')
            return
        data = data.get('results')
        description = data.get('description_blocks')
        description_dict = {}
        if description:
            for item in description:
                title = item.get('title')
                values = item.get('values')
                if values:
                    description_dict[title] = values[0].get('name')
                else:
                    max = item.get('max')
                    unit = item.get('unit')
                    description_dict[title] = f'{max}{unit}'
        price = data.get('price')
        prev_price = data.get('prev_price')
        price_data = {
            'current': price
        }
        if prev_price:
            discount = (prev_price - price) / prev_price * 100
            price_data['sale_tag'] = discount
        else:
            prev_price = price
            discount = 0
        price_data['original'] = prev_price
        availability = data.get('availability')
        availability_dict = {}
        if availability:
            availability_dict['in_stock'] = availability.get('title')
            availability_dict['count'] = data.get('availability_title')
        image_url = data.get('image_url')
        assets_dict = {}
        if image_url:
            assets_dict['main_image'] = image_url
        yield {
                'timestamp': datetime.datetime.now().timestamp(),
                'RPC': data.get('uuid'),
                'url': response.meta.get('product_url'),
                'title': data.get('name'),
                'marketing_tags': response.meta.get('marketing_tags'),
                'brand': description_dict['Бренд'],
                'price_data': price_data,
                'stock': availability_dict,
                'metadata': description_dict,
                'assets': assets_dict
            }

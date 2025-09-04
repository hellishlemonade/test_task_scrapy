import datetime
import json
from urllib.parse import urlencode, parse_qs, urlparse

import scrapy

from alkoteka import items


BASE_URL = 'https://alkoteka.com/web-api/v1/product/'
BASE_MAIN_URL = 'https://alkoteka.com/catalog/'
KRACNODAR_UUID = '4a70f9e0-46ae-11e7-83ff-00155d026416'
START_URLS = [
    f'https://alkoteka.com/web-api/v1/product?city_uuid={KRACNODAR_UUID}&options%5Bcvet%5D[]=beloe&page=1&per_page=20&root_category_slug=vino',
    f'https://alkoteka.com/web-api/v1/product?city_uuid={KRACNODAR_UUID}&options%5Bcvet%5D[]=rozovoe&page=1&per_page=20&root_category_slug=vino',
    f'https://alkoteka.com/web-api/v1/product?city_uuid={KRACNODAR_UUID}&options%5Bcategories%5D[]=konyak-brendi&page=1&per_page=20&root_category_slug=krepkiy-alkogol'
]


class AlkoSpider(scrapy.Spider):
    name = 'alko_spider'
    start_urls = START_URLS

    def parse(self, response):
        try:
            data = json.loads(response.body)
        except json.JSONDecodeError:
            self.logger.error('Ошибка загрузки JSON из ответа')
            return
        parsed_url = urlparse(response.url)
        params_dict = parse_qs(parsed_url.query)
        for item in data.get('results', []):
            product_slug = item.get('slug')
            if product_slug:
                city_uuid = params_dict.get('city_uuid')[0]
                product_api_url = (
                    f'{BASE_URL}{product_slug}?'
                    f'city_uuid={city_uuid}'
                )
                marketing_labels = item.get('action_labels', None)
                market_labels_list = []
                if marketing_labels:
                    for label in marketing_labels:
                        market_labels_list.append(label.get('title'))
                section = [
                    value[0] for key, value in params_dict.items() if
                    key != 'city_uuid' and key != 'page' and key != 'per_page'
                ]
                yield scrapy.Request(
                    product_api_url,
                    callback=self.product_parse,
                    meta={
                        'product_url': item.get('product_url'),
                        'marketing_tags': market_labels_list,
                        'section': section
                    }
                )
        if data['meta']['has_more_pages']:
            next_page = data['meta']['current_page'] + 1
            params_dict['page'] = next_page
            next_url = (
                'https://alkoteka.com/web-api/v1/product?'
                f'{urlencode(params_dict, doseq=True)}'
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
        else:
            self.logger.error(
                f'Отсутствет описание у продукта: {response.url}'
            )
        brand = description_dict.get('Бренд')
        if brand is None:
            self.logger.error(
                f'Отсутствует Бренд у товара: {response.url}'
            )
        price = data.get('price')
        price_data = {
            'current': price
        }
        if price:
            prev_price = data.get('prev_price')
            if prev_price:
                discount = (prev_price - price) / prev_price * 100
                price_data['sale_tag'] = round(discount, 2)
            else:
                prev_price = price
                discount = 0
            price_data['original'] = prev_price
        else:
            self.logger.error(
                f'Отсутствет цена у продукта: {response.url}'
            )
        availability = data.get('availability')
        availability_dict = {}
        if availability:
            availability_dict['in_stock'] = availability.get('title')
            availability_dict['count'] = data.get('availability_title')
        else:
            self.logger.error(
                f'Отсутствует информация о наличии товара: {response.url}'
            )
        image_url = data.get('image_url')
        assets_dict = {}
        if image_url:
            assets_dict['main_image'] = image_url
        else:
            self.logger.error(
                f'Отсутствует изображение товара: {response.url}'
            )
        result_data = {
                'timestamp': datetime.datetime.now().timestamp(),
                'RPC': data.get('uuid'),
                'url': response.meta.get('product_url'),
                'title': data.get('name'),
                'marketing_tags': response.meta.get('marketing_tags'),
                'brand': brand,
                'section': response.meta.get('section'),
                'price_data': price_data,
                'stock': availability_dict,
                'metadata': description_dict,
                'assets': assets_dict
            }
        yield items.AlkotekaItem(result_data)

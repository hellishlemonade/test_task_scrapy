BOT_NAME = "alkoteka"

RESULTS_DIR = 'results'

FEEDS = {
    f'{RESULTS_DIR}/results.json': {
        'format': 'json',
        'fields': [
            'timestamp',
            'RPC',
            'url',
            'title',
            'marketing_tags',
            'brand',
            'section',
            'price_data',
            'stock',
            'assets',
            'metadata',
        ],
        'overwrite': True
    }
}

SPIDER_MODULES = ["alkoteka.spiders"]
NEWSPIDER_MODULE = "alkoteka.spiders"

ADDONS = {}

LOG_LEVEL = 'INFO'

ROBOTSTXT_OBEY = True

CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

FEED_EXPORT_ENCODING = "utf-8"

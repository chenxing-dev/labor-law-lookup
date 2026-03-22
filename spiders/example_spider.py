from scrapy import Spider

class ExampleSpider(Spider):
    name = 'example'
    start_urls = ['https://example.com']

    def parse(self, response):
        self.log(f"Visited: {response.url}")
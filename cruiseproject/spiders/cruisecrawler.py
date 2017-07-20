# -*- coding: utf-8 -*-
import scrapy
import json
from scrapy.shell import inspect_response


class CruiseSpider(scrapy.Spider):
    name = "cruisespider"
    start_urls = [
        'https://www.hurtigruten.com/api/travelfilter?destinationId=&departureMonthYear=&shipId=&marketCode=UK&languageCode=en']

    def parse(self, response):
        json_response = json.loads(response.body)
        for link in json_response['voyages']:
            full_link = response.urljoin(link['voyageUrl'])
            yield scrapy.Request(full_link, callback=self.parse_codes)

    def parse_codes(self, response):
        sold_out = response.xpath('//div[@class="top-image-promotion"]').extract_first()
        if sold_out is not None:
            print('This cruise is SOLD OUT! {}'.format(response.url))
        codes = response.xpath(
            '//script[contains(.,"packageCodes")]').re_first(r'"packageCodes": \[(.*)\],')
        url = "https://shadowprodapi.hurtigruten.com/api//travelsuggestions/gateways"
        payload = {"travelSuggestionCodes": None, "marketCode": "UK", "languageCode": "en"}
        payload["travelSuggestionCodes"] = codes.replace('"', '').split(',')
        data = json.dumps(payload)
        yield scrapy.Request(url, method="POST", body=data, callback=self.parse_grouped, meta={'link': response.url})

    def parse_grouped(self, response):
        link = response.meta['link']
        json_res = json.loads(response.body)
        payload = {"packageCode": None, "searchFromDateTime": None, "cabins": [{"passengers": [{"ageCategory": "ADULT", "guestType": "REGULAR"}, {
            "ageCategory": "ADULT", "guestType": "REGULAR"}]}], "currencyCode": "EUR", "marketCode": "UK", "languageCode": "en", "quoteId": None, "bookingSourceCode": "TDL_B2C_ROW_EURO"}
        url = 'https://shadowprodapi.hurtigruten.com/api/availability/travelsuggestions/grouped'
        for item in json_res["gateways"]:
            date = item["firstAvailableDate"].split('T')[0]
            payload["searchFromDateTime"] = date
            payload["packageCode"] = item["packageCode"]
            cruise_name = item["displayName"]
            duration = item["durationText"]
            data = json.dumps(payload)
            yield scrapy.Request(url, method="POST", body=data, callback=self.parse_price,
                                 meta={'cruise_name': cruise_name, 'duration': duration, 'link': link})

    def parse_price(self, response):
        json_res = json.loads(response.body)
        quote_id = json_res["quoteId"]
        url = 'https://shadowprodapi.hurtigruten.com/api/quotes/{}/packagePrices?date={}&voyageId={}'
        for item in json_res["calendar"]:
            if item["voyages"] is not None:
                voyage_date = item["date"].split('T')[0]
                voyage_id = item["voyages"][0]["voyageId"]
                full_url = url.format(quote_id, voyage_date, voyage_id)
                yield scrapy.Request(full_url, callback=self.final_result, meta=response.meta)

    def final_result(self, response):
        meta = response.meta
        json_res = json.loads(response.body)
        item = dict()
        try:
            item['cruise_name'] = meta['cruise_name']
            item['link_to_cruise'] = meta['link']
            item['duration'] = meta['duration']
            item['date'] = json_res['date'].split('T')[0]
            item['code'] = json_res['packageCode']
            item['cabins_prices'] = []
            for i in json_res['categoryPrices']:
                d = {'name': i['localizedName']}
                d['price'] = i['price']['localizedPrice'].replace("\xa0", "")
                item['cabins_prices'].append(d)
            yield item
        except Exception as e:
            print('Got a {}'.format(e))
            inspect_response(response, self)

# -*- coding: utf-8 -*-
import scrapy
import json


class CruiseSpider(scrapy.Spider):
    name = "cruisespider"
    start_urls = [
        'https://www.hurtigruten.com/api/travelfilter?destinationId=&departureMonthYear=&shipId=&marketCode=UK&languageCode=en']

    def parse(self, response):
        """Initially, we make request to API and parse links to all voyages from response.
        """
        json_response = json.loads(response.body)
        for link in json_response['voyages']:
            full_link = response.urljoin(link['voyageUrl'])
            yield scrapy.Request(full_link, callback=self.parse_single_page)

    def parse_single_page(self, response):
        """We check if voyages are not sold out
        and after extracts voyages unique ids from the page source
        and make a first post request with ids as payload.
        """
        sold_out = response.xpath('//div[@class="top-image-promotion"]').extract_first()
        if sold_out is not None:
            print('This cruise is SOLD OUT! {}'.format(response.url))
        codes_string = response.xpath('//script[contains(.,"packageCodes")]/text()').extract_first()
        codes_dict = json.loads(codes_string.replace("var __PAGECONTENT = ", ""))
        codes = codes_dict['tourPackageDetails']['packageCodes']
        if codes is not None:
            url = "https://shadowprodapi.hurtigruten.com/api//travelsuggestions/gateways"
            payload = {"travelSuggestionCodes": codes, "marketCode": "UK", "languageCode": "en"}
            data = json.dumps(payload)
            yield scrapy.Request(url, method="POST", body=data, callback=self.parse_dates, meta={'link': response.url})
        else:
            print('Page don\'t have codes!')

    def parse_dates(self, response):
        """We extract available departure dates from the response and simulate JavaScript Ajax call
        with second post request with a properly payload
        (on the original page we need to click a button "Select date" to make similar request).
        """
        link = response.meta['link']
        json_res = json.loads(response.body)
        payload = {"packageCode": None, "searchFromDateTime": None,
                   "cabins": [{"passengers": [{"ageCategory": "ADULT", "guestType": "REGULAR"}, {
                       "ageCategory": "ADULT", "guestType": "REGULAR"}]}], "currencyCode": "EUR", "marketCode": "UK",
                   "languageCode": "en", "quoteId": None, "bookingSourceCode": "TDL_B2C_ROW_EURO"}
        url = 'https://shadowprodapi.hurtigruten.com/api/availability/travelsuggestions/grouped'
        for item in json_res["gateways"]:
            date = item["firstAvailableDate"].split('T')[0]
            payload["searchFromDateTime"] = date
            payload["packageCode"] = item["packageCode"]
            cruise_name = item["displayName"]
            duration = item["durationText"]
            data = json.dumps(payload)
            yield scrapy.Request(url, method="POST", body=data, callback=self.parse_ids,
                                 meta={'cruise_name': cruise_name, 'duration': duration, 'link': link})

    def parse_ids(self, response):
        """We parse the response and extract two vital code  that we need to construct url for making
        a final get request to all available prices for that voyage
        (this is a second request that page makes when you click "Select date" button).
        """
        meta = response.meta
        json_res = json.loads(response.body)
        quote_id = json_res["quoteId"]
        url = 'https://shadowprodapi.hurtigruten.com/api/quotes/{}/packagePrices?date={}&voyageId={}'
        for item in json_res["calendar"]:
            if item["voyages"] is not None:
                voyage_date = item["date"].split('T')[0]
                voyage_id = item["voyages"][0]["voyageId"]
                meta['ship'] = item["voyages"][0]["ship"]['name']
                full_url = url.format(quote_id, voyage_date, voyage_id)
                yield scrapy.Request(full_url, callback=self.final_result, meta=response.meta)

    def final_result(self, response):
        """Finally, after we successfully simulate a click on the button
        we can parse all info about the voyage and extract different cabins prices
        (without all previous complicated requests we only was able to get a standard price from the initial page).
        """
        meta = response.meta
        json_res = json.loads(response.body)
        item = dict()
        item['cruise_name'] = meta['cruise_name']
        item['code'] = json_res['packageCode']
        item['ship'] = meta['ship']
        item['link_to_cruise'] = meta['link']
        item['departure_date'] = json_res['date'].split('T')[0]
        item['duration'] = meta['duration']
        item['price'] = json_res['price']['localizedPrice'].replace("\xa0", "")
        for i in json_res['categoryPrices']:
            item[i['localizedName']] = i['price']['localizedPrice'].replace("\xa0", "")
        yield item

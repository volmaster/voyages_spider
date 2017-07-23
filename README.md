# voyages_spider
This spider checks availability and extract info about all prices for voyages from [hurtigruten.com](https://www.hurtigruten.com/find-a-cruise/?destinationId=&departureMonthYear=&shipId=&marketCode=UK&languageCode=en).
The site heavy use of a JavaScript and on the [single voyages page](https://www.hurtigruten.com/destinations/antarctica/adventure-to-the-chilean-fjords-and-antarctica/) 
in order to obtain desired info we need to click on the button "Check availability" and after that click on the button 
"Select date" and wait some time (site uses a complicated Ajax calls behind the scenes).
With help of this spider, we can simulate those JavaScripts requests and quickly parse all returning info.

The short demo of spider work:
https://youtu.be/Z1y85PeRMJc

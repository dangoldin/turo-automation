from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import datetime, time, re, csv, sys

import config

RE_REMOVE_HTML = re.compile('<.+?>')

SLEEP_SECONDS = 3

class TuroCrawler:
    def __init__(self):
        self.driver = webdriver.Chrome()
        self.driver.set_page_load_timeout(30)

    def crawl(self, outfile):
        self.login()
        time.sleep(SLEEP_SECONDS)
        trips = self.get_trips()
        self.write_to_file(trips, outfile)
        self.stop()

    def login(self):
        self.driver.get('https://turo.com/login')

        username = self.driver.find_element_by_id('username')
        username.send_keys(config.TURO_USERNAME)

        password = self.driver.find_element_by_name('password')
        password.send_keys(config.TURO_PASSWORD)

        self.driver.find_element_by_id("submit").click()

    def write_to_file(self, rows, out):
        print 'Writing to file', out
        with open(out, 'w') as f:
            w = csv.DictWriter(f,
                    fieldnames = rows[0].keys(),
                    delimiter=',')
            w.writeheader()
            w.writerows(rows)

    def stop(self):
        self.driver.close()

    def get_datetime(self, raw_string):
        # Remove the header text
        cleaned_str = re.sub('.*\n', '', 
                raw_string, count = 1)

        return datetime.datetime.strptime(cleaned_str, '%a, %b %d, %Y\n%I:%M %p')

    def get_trip(self, reservation_url):
        print 'Getting trip', reservation_url

        self.driver.get(reservation_url + '/receipt/')

        pickup, dropoff = [self.get_datetime(x.text) for x in self.driver.find_elements_by_class_name('receiptSchedule')]

        line_items = self.driver.find_elements_by_class_name('line-item')

        results = {'URL': reservation_url,
                'PICKUP': pickup,
                'DROPOFF': dropoff}
        for item in line_items:
            name = item.find_element_by_class_name('label').text
            if name == 'YOU PAID': # Ignore trips where I didn't host
                continue
            value = item.find_element_by_class_name('value').text
            if name != 'GUEST':
                value = float(re.search('[\d|\.]+', value).group())
            results[name] = value


# This code is almost certainly wrong, but I don't have 
# any examples with reimbursements to test.
        try:
            reimbursements = self.driver.find_element_by_class_name('reimbursements').find_elements_by_class_name('line-item--longLabel')
            for r in reimbursements:
                if 'tolls' in r.text.lower():
                    reimbursement_tolls = float(r.text.lower().split(' ')[-1])
                if 'additional miles driven' in r.text.lower():
                    reimbursement_mileage = float(r.text.lower().split(' ')[-1])
        except Exception, e:
            print 'No reimbursements found for', reservation_url

        return results

    # Only trips that have a receipt and have already happened
    def is_valid_trip(self, el):
        return 'completed' in el.get_attribute('class') or 'cancelled' in el.get_attribute('class')

    def process_cancelled_trip(self, cancelled_trip):
        print 'Processing ', cancelled_trip.text

        if 'You cancelled this trip' in cancelled_trip.text:
            earnings = 0.0
        elif '$' in cancelled_trip.text:
            earnings = float(re.findall('\$\d+\.\d+', cancelled_trip.text)[0].replace('$',''))
        else:
            earnings = 0.0

        return {
            'url_snippet': '',
            'pickup': '',
            'dropoff': '',
            'cost': 0.0,
            'earnings': earnings,
            'reimbursement_tolls': 0.0,
            'reimbursement_mileage': 0.0,
        }

    def get_trips(self, page_slug = None):
        if page_slug is None:
            self.driver.get('https://turo.com/dashboard/history')
        else:
            print 'Getting https://turo.com/dashboard/history?' + page_slug
            self.driver.get('https://turo.com/dashboard/history?' + page_slug)

        # Wait for the page to load
        time.sleep(SLEEP_SECONDS)

        # Get this now and use this later so we don't have to go back
        next_page = None
        try:
            last_page = self.driver.find_elements_by_class_name('paginator-link')[-1]
            if ord(last_page.text) == 8250:
                next_page = last_page.get_attribute('href').split('?')[-1]
        except IndexError:
            print "Only one page"

        trip_elements = self.driver.find_elements_by_class_name('dashboardActivityFeed-link')

        trip_slugs = [te.get_attribute('href') for te in trip_elements]

        print 'Trip Slugs', trip_slugs

        trip_details = [self.get_trip(trip_slug) for trip_slug in trip_slugs]

        print trip_details

        # Get the last page link and see if there's more
        if next_page is not None:
            trip_details += self.get_trips(next_page)

        return trip_details

if __name__ == '__main__':
    outfile = 'stats.csv'
    if len(sys.argv) > 1:
        outfile = sys.argv[1]

    crawler = TuroCrawler()
    crawler.crawl(outfile)

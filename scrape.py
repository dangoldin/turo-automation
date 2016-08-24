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
            w = csv.DictWriter(f, delimiter=',', fieldnames=rows[0].keys())
            w.writeheader()
            for row in rows:
                w.writerow(row)

    def stop():
        self.driver.close()

    def get_datetime(self, el):
        date = el.find_element_by_class_name('scheduleDate').text
        time = el.find_element_by_class_name('scheduleTime').text

        date_str = datetime.datetime.now().strftime('%Y') + ' ' + date + ' ' + time

        return datetime.datetime.strptime(date_str, '%Y %b %d %I:%M %p')

    def get_trip(self, reservation_url_snippet):
        print 'Getting trip', reservation_url_snippet

        self.driver.get('https://turo.com' + reservation_url_snippet + '/receipt/')

        pickup = self.driver.find_element_by_class_name('reservationSummary-schedulePickUp')
        dropoff = self.driver.find_element_by_class_name('reservationSummaryDropOff')

        cost = float(self.driver.find_element_by_class_name('cost-details').find_element_by_class_name('value').text.replace('$', '').strip())
        earnings = float(self.driver.find_element_by_class_name('payment-details').find_element_by_class_name('total').text.replace('$', '').strip())
        reimbursement_tolls = 0.0
        reimbursement_mileage = 0.0

        try:
            reimbursements = self.driver.find_element_by_class_name('reimbursements').find_elements_by_class_name('line-item--longLabel')
            for r in reimbursements:
                if 'tolls' in r.text.lower():
                    reimbursement_tolls = float(r.text.lower().split(' ')[-1])
                if 'additional miles driven' in r.text.lower():
                    reimbursement_mileage = float(r.text.lower().split(' ')[-1])
        except Exception, e:
            print 'No reimbursements found for', reservation_url_snippet

        return {
            'url_snippet': reservation_url_snippet,
            'pickup': self.get_datetime(pickup),
            'dropoff': self.get_datetime(dropoff),
            'cost': cost,
            'earnings': earnings,
            'reimbursement_tolls': reimbursement_tolls,
            'reimbursement_mileage': reimbursement_mileage,
        }

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
            self.driver.get('https://turo.com/trips')
        else:
            print 'Getting https://turo.com/trips?' + page_slug
            self.driver.get('https://turo.com/trips?' + page_slug)

        # Get this now and use this later so we don't have to go back
        next_page = None
        last_page = self.driver.find_elements_by_class_name('paginator-link')[-1]
        if ord(last_page.text) == 8250:
            next_page = last_page.get_attribute('href').split('?')[-1]

        trip_elements = [te for te in self.driver.find_elements_by_class_name('reservationSummary') if self.is_valid_trip(te)]

        cancelled_trips = [te for te in trip_elements if 'cancelled' in te.get_attribute('class')]

        trip_slugs = [te.find_element_by_class_name('reservation').get_attribute('data-href') for te in trip_elements if 'completed' in te.get_attribute('class')]

        print 'Trip Slugs', trip_slugs
        print 'Cancelled Trips', [ct.text for ct in cancelled_trips]

        trip_details = [self.process_cancelled_trip(ct) for ct in cancelled_trips] + [self.get_trip(trip_slug) for trip_slug in trip_slugs]

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
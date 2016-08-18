from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import datetime, time, re, csv, sys

import config

RE_REMOVE_HTML = re.compile('<.+?>')

SLEEP_SECONDS = 3

def login(driver):
    driver.get('https://turo.com/login')

    username = driver.find_element_by_id('username')
    username.send_keys(config.TURO_USERNAME)

    password = driver.find_element_by_name('password')
    password.send_keys(config.TURO_PASSWORD)

    driver.find_element_by_id("submit").click()

def write_to_file(rows, out):
    print 'Writing to file', out
    with open(out, 'w') as f:
        w = csv.DictWriter(f, delimiter=',', fieldnames=rows[0].keys())
        w.writeheader()
        for row in rows:
            w.writerow(row)

def get_datetime(el):
    date = el.find_element_by_class_name('scheduleDate').text
    time = el.find_element_by_class_name('scheduleTime').text

    date_str = datetime.datetime.now().strftime('%Y') + ' ' + date + ' ' + time

    return datetime.datetime.strptime(date_str, '%Y %b %d %I:%M %p')

def get_trip(driver, reservation_url_snippet):
    driver.get('https://turo.com' + reservation_url_snippet + '/receipt/')

    pickup = driver.find_element_by_class_name('reservationSummary-schedulePickUp')
    dropoff = driver.find_element_by_class_name('reservationSummaryDropOff')

    cost = float(driver.find_element_by_class_name('cost-details').find_element_by_class_name('value').text.replace('$', '').strip())
    earnings = float(driver.find_element_by_class_name('payment-details').find_element_by_class_name('total').text.replace('$', '').strip())
    reimbursement_tolls = 0.0
    reimbursement_mileage = 0.0

    try:
        reimbursements = driver.find_element_by_class_name('reimbursements').find_elements_by_class_name('line-item--longLabel')
        for r in reimbursements:
            if 'tolls' in r.text.lower():
                reimbursement_tolls = float(r.text.lower().split(' ')[-1])
            if 'additional miles driven' in r.text.lower():
                reimbursement_mileage = float(r.text.lower().split(' ')[-1])
    except Exception, e:
        print 'No reimbursements found'

    return {
        'url_snippet': reservation_url_snippet,
        'pickup': get_datetime(pickup),
        'dropoff': get_datetime(dropoff),
        'cost': cost,
        'earnings': earnings,
        'reimbursement_tolls': reimbursement_tolls,
        'reimbursement_mileage': reimbursement_mileage,
    }

# Only trips that have a receipt and have already happened
def valid_trip(el):
    return 'completed' in el.get_attribute('class')

def get_trips(driver, page_slug = None):
    if page_slug is None:
        driver.get('https://turo.com/trips')
    else:
        print 'Getting https://turo.com/trips?' + page_slug
        driver.get('https://turo.com/trips?' + page_slug)

    # Get this now and use this later so we don't have to go back
    next_page = None
    last_page = driver.find_elements_by_class_name('paginator-link')[-1]
    if ord(last_page.text) == 8250:
        next_page = last_page.get_attribute('href').split('?')[-1]

    trip_elements = [te.find_element_by_class_name('reservation') for te in driver.find_elements_by_class_name('reservationSummary') if valid_trip(te)]

    trip_slugs = [te.get_attribute('data-href') for te in trip_elements]

    trip_details = [get_trip(driver, trip_slug) for trip_slug in trip_slugs]

    print trip_details

    # Get the last page link and see if there's more
    if next_page is not None:
        trip_details += get_trips(driver, next_page)

    return trip_details

def init_driver():
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(30)
    return driver

def get_ride_info(outfile):
    driver = init_driver()

    login(driver)

    time.sleep(SLEEP_SECONDS)

    trips = get_trips(driver)

    write_to_file(trips, 'out.csv')

    driver.close()

if __name__ == '__main__':
    outfile = 'stats.csv'
    if len(sys.argv) > 1:
        outfile = sys.argv[1]

    get_ride_info(outfile)


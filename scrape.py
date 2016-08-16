from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import time, re, csv, sys

import config

RE_REMOVE_HTML = re.compile('<.+?>')

SLEEP_SECONDS = 3

def login(driver):
    driver.get('https://turo.com/login')

    # login_button = driver.find_element_by_xpath('//*[@id="pageContainer"]/header/div/ul/li[4]/a')
    # login_button.click()

    # time.sleep(1)

    username = driver.find_element_by_id('username')
    username.send_keys(config.TURO_USERNAME)

    password = driver.find_element_by_name('password')
    password.send_keys(config.TURO_PASSWORD)

    driver.find_element_by_id("submit").click()

def write_stats(stats, out):
    print 'Writing to file', out
    with open(out, 'w') as f:
        w = csv.DictWriter(f, delimiter=',', fieldnames=fields)
        w.writeheader()
        for row in stats:
            w.writerow(row)

def get_trip(driver, reservation_url_snippet):
    driver.get('https://turo.com' + reservation_url_snippet)

    pickup = driver.find_element_by_class_name('reservationSummary-schedulePickUp')
    pickup_date = pickup.find_element_by_class_name('scheduleDate').text
    pickup_time = pickup.find_element_by_class_name('scheduleTime').text

    dropoff = driver.find_element_by_class_name('reservationSummaryDropOff')
    dropoff_date = dropoff.find_element_by_class_name('scheduleDate').text
    dropoff_time = dropoff.find_element_by_class_name('scheduleTime').text

    cost = float(driver.find_element_by_class_name('reservationSummary-cost').find_element_by_class_name('amount').text.replace('$', '').strip())

    return {
        'pickup': (pickup_date, pickup_time),
        'dropoff': (dropoff_date, dropoff_time),
        'cost': cost,
    }

def get_trips(driver, page = None):
    if page is None:
        driver.get('https://turo.com/trips')
    else:
        # TODO: Get other pages
        driver.get('https://turo.com/trips')

    trip_elements = driver.find_elements_by_class_name('reservation')

    trips = [te.get_attribute('data-href') for te in trip_elements]

    # TODO: Get other pages


def get_ride_info(outfile):
    driver = webdriver.Chrome()
    driver.set_page_load_timeout(30)

    login(driver)

    time.sleep(SLEEP_SECONDS)

    get_trips(driver)

    driver.close()

if __name__ == '__main__':
    outfile = 'stats.csv'
    if len(sys.argv) > 1:
        outfile = sys.argv[1]

    get_ride_info(outfile)


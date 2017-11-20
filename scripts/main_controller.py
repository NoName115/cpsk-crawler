from bs4 import BeautifulSoup
from classes import Spojenie, Saver
from datetime import datetime, timedelta
import re
import time
import requests
import os
import sys


cp_url_with_datetime = "https://cp.hnonline.sk/{0}/spojenie/?date={1}&time={2}&f={3}&t={4}&fc=100003&tc=100003&direct=true&submit=true"
cp_url_actual_datetime = "https://cp.hnonline.sk/{0}/spojenie/?f={1}&t={2}&direct=true&submit=true"

def download_mainsite_with_datetime(input_datetime):
    station_from = 'Ko%c5%a1ice'
    station_to = 'Bratislava+hl.st.'
    transport = 'vlak'

    # Download website
    final_url = cp_url_with_datetime.format(
        transport,
        input_datetime.strftime("%d.%m.%Y"),
        input_datetime.strftime("%H:%M"),
        station_from,
        station_to
    )

    print(final_url)

    return requests.get(final_url).content

def load_from_file_mainsite(filename):
    with open(filename, 'r') as inputfile:
        return inputfile.read()

def resolve_mainsite(website_content):
    # Remove everything between '<!-- zobrazeni vysledku start -->' & <!-- zobrazeni vysledku end-->
    remove_before = '<!-- zobrazeni vysledku start -->'
    remove_after = '<!-- zobrazeni vysledku end-->'
    trim_data = website_content[
        website_content.find(remove_before): website_content.find(remove_after)
    ]
    soup = BeautifulSoup(
        trim_data,
        'html.parser'
    )

    all_links = {}
    # Parse links
    for table in soup.find_all('table'):
        new_link = Spojenie(table.find_all('tr'))
        new_link.resolve_main_data()
        all_links.update({
            new_link.train_name: new_link
        })
        #print(new_link)
    return all_links


def load_fewhours_back_mainsite(hours):
    all_links = {}
    for i in range(hours, 0, -1):
        site_content = download_mainsite_with_datetime(
            datetime.now() - timedelta(hours=i)
        )
        new_links = resolve_mainsite(site_content.decode('UTF-8'))
        for train_name, link_object in new_links.items():
            if (train_name not in all_links):
                all_links.update({
                    train_name: link_object
                })
    return all_links


update_time = 5*60
site_content = ""

# Nacitat predchadzajuce vlaky
actual_links = load_fewhours_back_mainsite(6)
while (1):
    try:
        print("--------- START RESOLVE ---------")
        print("------ " + str(datetime.now()))
        #site_content = load_from_file_mainsite('output_0.txt')        

        site_content = download_mainsite_with_datetime(
            datetime.now()
        )
        new_links = resolve_mainsite(site_content.decode('UTF-8'))

        for train_name, link_object in new_links.items():
            if (train_name not in actual_links):
                actual_links.update({
                    train_name: link_object
                })
                Saver.save_link_info(link_object)
                print("Nove spojenie: " + train_name)
            else:
                # Already in dict
                if (not actual_links[train_name].location_url):
                    actual_links[train_name].update_info(
                        link_object
                    )

        print("--------- DELAY RESOLVE ---------")
        train_to_remove = set()
        for train_name, link_object in actual_links.items():
            link_object.resolve_delay()
            if (link_object.datetime_to < datetime.now()):
                train_to_remove.add(train_name)

        for tr_remove in train_to_remove:
            actual_links.pop(tr_remove, None)
            print('Train removed: ' + tr_remove)

        time.sleep(update_time)

    except Exception as err:
        error_file = open("../logs/error_log.err", "a")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_file.write(
            str(datetime.now()) + ": \n" +
            "\t" + str(exc_type) + " " + str(fname) +
            " " + str(exc_tb.tb_lineno) + "\n"
        )
        error_file.close()

        error_log = open("../logs/" + str(datetime.now()) + "_content.err", "a")
        error_log.write(site_content.decode('UTF-8') + "\n\n")
        error_log.close()

        time.sleep(update_time)

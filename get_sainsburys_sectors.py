import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from Heroku_functions import postgres_execute, postgres_update, postgres_connect
from datetime import date
import time

def heroku_upload():
    print("uploading", len(leaf_sectors), "rows to heroku")
    records = leaf_sectors.itertuples(index=False)
    result = list(records)
    records_list_template = ','.join(['%s'] * len(result))

    insert_query = '''INSERT INTO "sainsburys_sectors" (
        "name", 
        "path", 
        "link", 
        "num_products",
        "date_updated",
        "products_scraped",
        "required")
                    VALUES {}'''.format(records_list_template)

    conn = postgres_connect()
    cur = conn.cursor()
    cur.execute(insert_query, result)
    conn.commit()

URL = 'https://www.sainsburys.co.uk/shop/gb/groceries'

page = requests.get(URL)
bad_urls = []

soup = bs(page.content, "html.parser")
all_sectors = soup.find('ul', id='megaNavLevelOne').find_all('li')[3:]
all_sectors = [[[x.a.text.strip()], x.a['href']] for x in all_sectors]
leaf_sectors = pd.DataFrame(columns=['name', 'path', 'link', 'num_products', 'date_updated', 'products_scraped', 'required'])
print(all_sectors)
for depth in ['departments', 'aisles', 'shelf']:
    print()
    print('looking for', depth, 'in', len(all_sectors), 'places')
    new_sectors = []
    for sector in all_sectors:
        print('>'.join(sector[0]))
        URL = sector[1]
        if 'sainsburys.co.uk' not in URL:
            URL = 'https://www.sainsburys.co.uk' + URL

        reboots = 0
        bad_url = False
        accessed = False
        while accessed is False:
            try:
                page = requests.get(URL)
                accessed = True
            except ConnectionError:
                if reboots < 3:
                    print("Remote Disconnect, rebooting...")
                    time.sleep(200)
                    reboots += 1
                else:
                    print("bad URL", URL)
                    accessed = True
                    bad_url = True
                    bad_urls.append(URL)
        if not bad_url:
            soup = bs(page.content, "html.parser")
            new = soup.find_all('ul', class_=depth)
            if new:
                new = new[0]
                for new_link in new.find_all('li'):
                    new_sectors.append([sector[0]+[new_link.a.text.strip()], new_link.a['href']])
            else:
                leaf_sectors = leaf_sectors.append({'name':sector[0][-1], 'path':'>'.join(sector[0]), 'link':sector[1], 'num_products':0, 'date_updated':date.today().strftime('%d-%m-%Y')}, ignore_index=True)
                print('appended')
            time.sleep(1)
    all_sectors = new_sectors



for sector in all_sectors:
    query_text = '''SELECT path FROM sainsburys_sectors
    WHERE path = **path**'''.replace('**path**','>'.join(sector[0]))
    result = postgres_execute(query_text)
    if len(result) == 0:
        leaf_sectors = leaf_sectors.append({'name': sector[0][-1], 'path': '>'.join(sector[0]), 'link': sector[1], 'num_products': 0,
                             'date_updated': date.today().strftime('%d-%m-%Y'), 'products_scraped': 0, 'required': 1}, ignore_index=True)

#heroku_upload()
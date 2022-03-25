import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from Heroku_functions import postgres_execute, postgres_connect
from datetime import date
import time


def heroku_upload():
    """upload database of new-found sectors to heroku"""
    print("uploading", len(new_leafs), "rows to heroku")
    records = new_leafs.itertuples(index=False)
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


# Get Sainsbury's home page
URL = 'https://www.sainsburys.co.uk/shop/gb/groceries'
page = requests.get(URL)
bad_urls = []

# Get HTML
soup = bs(page.content, "html.parser")

# Get level 1 sectors
all_sectors = soup.find('ul', id='megaNavLevelOne').find_all('li')[3:]
all_sectors = [[[x.a.text.strip()], x.a['href']] for x in all_sectors]

# Create dataframe of leaf sectors
# Leaf sector is a sector without any subsectors
leaf_sectors = pd.DataFrame(
    columns=['name', 'path', 'link', 'num_products', 'date_updated', 'products_scraped', 'required'])
new_leafs = leaf_sectors.copy()

print(all_sectors)
# Get subsectors of all current sectors
for depth in ['departments', 'aisles', 'shelf']:
    print()
    print('looking for', depth, 'in', len(all_sectors), 'places')
    new_sectors = []
    for sector in all_sectors:
        print('>'.join(sector[0]))
        URL = sector[1]
        if 'sainsburys.co.uk' not in URL:
            URL = 'https://www.sainsburys.co.uk' + URL

        # Load page
        reboots = 0
        bad_url = False
        accessed = False
        while accessed is False:
            try:
                page = requests.get(URL)
                accessed = True
            except:
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
                    new_sectors.append([sector[0] + [new_link.a.text.strip()], new_link.a['href']])
            else:
                leaf_sectors = leaf_sectors.append(
                    {'name': sector[0][-1], 'path': '>'.join(sector[0]), 'link': URL, 'num_products': 0,
                     'date_updated': date.today().strftime('%Y-%m-%d'), 'products_scraped': 0, 'required': 1},
                    ignore_index=True)
                print('appended')
            time.sleep(1)
    all_sectors = new_sectors

#Get previous sectors already in sectors database
query_text = '''SELECT path FROM sainsburys_sectors'''
previous_paths = list(postgres_execute(query_text)['path'])

# Delete any old sectors which no longer exist
for path in previous_paths:
    if path not in list(leaf_sectors['path']):
        query_text = '''SELECT uuid from sainsburys_sectors 
        WHERE path==**path**'''.replace('**path**', path)
        result = list(postgres_execute(query_text)['uuid'])
        query_text = '''DELETE from sainsburys_sectors 
        WHERE path=**path**'''.replace('**path**', path)
        _ = postgres_execute(query_text)
        for sector_id in result:
            query_text = '''DELETE from sainsburys_products 
            WHERE sector_id=**sector_id**'''.replace('**sector_id**', sector_id)
            _ = postgres_execute(query_text)

# Add new sectors
for index, sector in leaf_sectors.iterrows():
    if sector['path'] not in previous_paths:
        new_leafs = new_leafs.append(sector)

# upload to heroku
heroku_upload()

sql_text = '''UPDATE sainsburys_sectors
SET real_date_updated = CAST(date_updated AS DATE)'''
_ = postgres_execute(sql_text)

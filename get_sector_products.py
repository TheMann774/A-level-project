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


num_sectors = 5

query_text = '''
SELECT name, path, link FROM sainsburys_sectors
WHERE required = 1
ORDER BY products_scraped ASC, date_updated ASC, num_products DESC
'''
result = postgres_execute(query_text)

for i in range(min(num_sectors, len(result))):
    sector = result.iloc[i]
    URL = sector['link']
    if 'https://www.sainsburys.co.uk' not in URL:
        URL = 'https://www.sainsburys.co.uk/' + URL
    page = requests.get(URL)
    soup = bs(page.content, "html.parser")
    pages_left = True
    all_products = []
    while pages_left:
        all_products += [x.h3.a['href'] for x in soup.find_all('div', class_='productNameAndPromotions')]
        if soup.find('li', class_='next') is None:
            pages_left = False
        elif soup.find('li', class_='next').a is None:
            pages_left = False
        else:
            URL = soup.find('li', class_='next').a['href']
            if 'https://www.sainsburys.co.uk' not in URL:
                URL = 'https://www.sainsburys.co.uk/' + URL
            page = requests.get(URL)
            soup = bs(page.content, "html.parser")
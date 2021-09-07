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



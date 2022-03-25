import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from Heroku_functions import postgres_execute, postgres_connect
from datetime import date
import time
import re

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

global driver

units = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def initialise_chrome():
    """Initialise a chrome browser and returns a driver object"""
    chrome_options = Options()
    chrome_options.headless = True
    new_driver = webdriver.Chrome(ChromeDriverManager().install())
    if chrome_options.headless is False:
        driver.maximize_window()
    return new_driver


def accept_cookies(chrome_driver):
    """try to accept cookies on the page"""
    elements = chrome_driver.find_elements_by_xpath("//*[contains(text(), 'Accept')]")

    for element in elements:
        try:
            element.send_keys(Keys.RETURN)
            print('cookie accept victory')
        except:
            pass
    time.sleep(0.5)
    return


def heroku_upload():
    """upload database of new-found products to heroku"""
    print("uploading", len(new_products), "rows to heroku")
    records = new_products.itertuples(index=False)
    result = list(records)
    records_list_template = ','.join(['%s'] * len(result))
    insert_query = '''INSERT INTO "sainsburys_products" (
        "name",
        "date_updated",
        "url",
        "sector_id",
        "price",
        "rating",
        "num_reviews",
        "expiry_duration",
        "vegetarian",
        "vegan",
        "religious_info",
        "organic",
        "description",
        "nutrition_100",
        "pack_servings",
        "mass",
        "ingredients",
        "allergens",
        "info",
        "cook_info",
        "origin_country",
        "recycling")
                    VALUES {}'''.format(records_list_template)
    conn = postgres_connect()
    cur = conn.cursor()
    cur.execute(insert_query, result)
    conn.commit()
    print("rows uploaded")


query_text = '''
SELECT uuid, name, path, link FROM sainsburys_sectors
WHERE required = 1
ORDER BY products_scraped ASC, real_date_updated ASC, num_products DESC
'''
result = postgres_execute(query_text)
num_sectors = 5 # Number of sectors to update at a time

new_products = pd.DataFrame(columns=["name",
                                     "date_updated",
                                     "url",
                                     "sector_id",
                                     "price",
                                     "rating",
                                     "num_reviews",
                                     "expiry_duration",
                                     "vegetarian",
                                     "vegan",
                                     "religious_info",
                                     "organic",
                                     "description",
                                     "nutrition_100",
                                     "pack_servings",
                                     "mass",
                                     "ingredients",
                                     "allergens",
                                     "info",
                                     "cook_info",
                                     "origin_country",
                                     "recycling"])

for i in range(min(num_sectors, len(result))):
    new_products = new_products[0:0] # Empty DataFrame
    sector = result.iloc[i]
    # Get HTML of page:
    URL = sector['link']
    if 'https://www.sainsburys.co.uk' not in URL:
        URL = 'https://www.sainsburys.co.uk/' + URL
    page = requests.get(URL)
    page_soup = bs(page.content, "html.parser")
    pages_left = True
    all_products = []
    while pages_left: # Get all the products in the sector
        all_products += [x.h3.a['href'] for x in page_soup.find_all('div', class_='productNameAndPromotions')]
        if page_soup.find('li', class_='next') is None:
            pages_left = False
        elif page_soup.find('li', class_='next').a is None:
            pages_left = False
        else:
            URL = page_soup.find('li', class_='next').a['href']
            if 'https://www.sainsburys.co.uk' not in URL:
                URL = 'https://www.sainsburys.co.uk/' + URL
            page = requests.get(URL)
            page_soup = bs(page.content, "html.parser")
    if not len(all_products):
        # Delete a sector if there are no products in the sector
        sql_text = '''
        DELETE FROM sainsburys_sectors
        WHERE path = '**path**'
        '''.replace('**path**', sector['path'])
        _ = postgres_execute(sql_text)
    else:
        # Open each product and get the relevant data
        driver = initialise_chrome()
        print(sector['name'])
        for product in all_products:
            time.sleep(1)
            counter = 0
            found = False
            while not found:
                # Keep trying initialisation until successful or 3 tries have passed
                if counter >= 2:
                    driver.close()
                    driver = initialise_chrome()
                try:
                    driver.get(product)
                    elem = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "pd__header"))
                    )
                    found = True
                except Exception as e:
                    print(e)
                    counter += 1
                    print(counter)
            print("accepting cookies")
            accept_cookies(driver)
            soup_file = driver.page_source
            page_soup = bs(soup_file, "html.parser")

            new_product = {'name': page_soup.find('h1', class_="pd__header").text,
                           'date_updated': date.today().strftime('%Y-%m-%d'),
                           'url': product,
                           'sector_id': sector['uuid'],
                           'price': page_soup.find('div', class_="pd__cost").div.text}

            # Get price
            if '/' in new_product['price'] and 'kg' in new_product:
                new_product['mass'] = 1
            if '£' in new_product['price']:
                new_product['price'] = float(
                    new_product['price'][1:].replace(' ', '').replace('/', '').replace('kg', ''))
            else:
                new_product['price'] = float(
                    new_product['price'][:-1].replace(' ', '').replace('/', '').replace('kg', '')) / 100

            # Get rating
            new_product['rating'] = float(
                len(page_soup.find('div', class_='star-rating').find_all('path', class_="star-rating-icon--full")))

            # Get num reviews
            try:
                new_product['num_reviews'] = int(
                    page_soup.find('span', class_='pd__reviews__read').text.split('(')[1][:-1])
            except:
                new_product['num_reviews'] = 0

            new_product['expiry_duration'] = 0

            # Get vegetarian and vegan information:
            if len(page_soup.find_all(text=[re.compile('Not suitable for vegetarians', re.IGNORECASE),
                                            re.compile('Not vegetarian', re.IGNORECASE)])):
                new_product['vegetarian'], new_product['vegan'] = 0, 0
            elif len(page_soup.find_all(text=[re.compile('Not suitable for vegans', re.IGNORECASE),
                                              re.compile('Not vegan', re.IGNORECASE)])):
                new_product['vegetarian'], new_product['vegan'] = 1, 0
            elif len(page_soup.find_all(
                    text=[re.compile('Suitable for vegans', re.IGNORECASE), re.compile('Vegan', re.IGNORECASE)])):
                new_product['vegetarian'], new_product['vegan'] = 1, 1
            elif len(page_soup.find_all(text=[re.compile('Suitable for vegetarians', re.IGNORECASE),
                                              re.compile('Vegetarian', re.IGNORECASE)])):
                new_product['vegetarian'], new_product['vegan'] = 1, 0
            else:
                new_product['vegetarian'], new_product['vegan'] = 0, 0

            # Get religious information
            new_product['religious_info'] = []
            if len(page_soup.find_all(text=re.compile('Kosher', re.IGNORECASE))):
                new_product['religious_info'].append(
                    page_soup.find(text=re.compile('Kosher', re.IGNORECASE)).parent.text)
            if len(page_soup.find_all(text=re.compile('Halal', re.IGNORECASE))):
                new_product['religious_info'].append(
                    page_soup.find(text=re.compile('Halal', re.IGNORECASE)).parent.text)
            new_product['religious_info'] = str(new_product['religious_info'])

            # Get organic information
            if len(page_soup.find_all(text=re.compile('Organic', re.IGNORECASE))):
                new_product['organic'] = 1
            else:
                new_product['organic'] = 0

            # Get product description
            product_description = []
            description_heading = page_soup.find('h3', text=re.compile('Description', re.IGNORECASE))
            if description_heading:
                flag = False
                while not flag:
                    try:
                        description_heading = description_heading.find_next_sibling()
                        if description_heading.name == 'div':
                            product_description.append(description_heading.text)
                        else:
                            flag = True
                    except:
                        flag = True
            new_product['description'] = '\n'.join(product_description)

            # Get product nutritional information
            new_product['nutrition_100'] = {}
            col100 = -1
            colserving = -1
            try:
                nutrition_cols = page_soup.find('table', class_='nutritionTable').thead.tr.find_all('th')
                for col in range(1, len(nutrition_cols)):
                    if re.search("100 ?(g|ml)", str.lower(nutrition_cols[col].text)) and 'ri' not in str.lower(
                            nutrition_cols[col].text) and col100 == -1:
                        col100 = col - 1
                    if 'serving' in str.lower(nutrition_cols[col].text) and 'ri' not in str.lower(
                            nutrition_cols[col].text) and colserving == -1:
                        colserving = col - 1
                if col100 != -1:
                    rows = page_soup.find('table', class_='nutritionTable').tbody.find_all('tr')
                    try:
                        new_product['nutrition_100']['Energy'] = float(
                            re.findall("[0-9]+ ?kcal", rows[1].find_all('td')[col100].text)[0][:-4])
                        if colserving != -1:
                            serving_size = 0.1 * float(rows[1].find_all('td')[colserving].text.split('kcal')[0]) / \
                                           new_product['nutrition_100']['Energy']
                    except:
                        try:
                            new_product['nutrition_100']['Energy'] = float(
                                re.findall("[0-9]+ ?kcal", rows[0].find_all('td')[col100].text)[0][:-4])
                            if colserving != -1:
                                serving_size = 0.1 * float(
                                    re.findall("[0-9]+ ?kcal", rows[0].find_all('td')[colserving].text)[0][:-4]) / \
                                               new_product['nutrition_100']['Energy']
                        except:
                            try:
                                new_product['nutrition_100']['Energy'] = float(
                                    rows[0].find_all('td')[col100].text.replace(' ', '').replace('\n', '').split('/')[
                                        1])
                                if colserving != -1:
                                    serving_size = 0.1 * float(
                                        rows[0].find_all('td')[colserving].text.replace(' ', '').replace('\n',
                                                                                                         '').split('/')[
                                            1]) / new_product['nutrition_100']['Energy']
                            except:
                                pass
                    for row in rows[2:]:
                        try:
                            new_product['nutrition_100'][row.th.text] = float(
                                row.find_all('td')[col100].text.split('g')[0])
                        except:
                            pass
            except Exception as e:
                print(e)
            new_product['nutrition_100'] = str(new_product['nutrition_100'])

            # Get product servings
            new_product['pack_servings'] = 0
            servings = page_soup.find(text=re.compile("Contains .+ servings", re.IGNORECASE))
            if servings:
                servings = \
                str.lower(servings).split('contains ')[1].split('servings')[0].replace('approx. ', '').replace(
                    'approximately', '').split(' ')[0]
                try:
                    new_product['pack_servings'] = int(servings)
                except:
                    try:
                        if '-' in servings:
                            servings = servings.split('-')
                            new_product['pack_servings'] = 10 * tens.index(servings[0]) + units.index(servings[1])
                        else:
                            new_product['pack_servings'] = units.index(servings[1])
                    except:
                        pass
            if not new_product['pack_servings']:
                try:
                    new_product['pack_servings'] = int(
                        re.findall(" x[0-9]+", page_soup.find('h1', class_='pd__header').text)[0][2:])
                except:
                    try:
                        new_product['pack_servings'] = int(
                            re.findall(" [0-9]+ ", page_soup.find('h1', class_='pd__header').text)[0][1:-1])
                    except:
                        new_product['pack_servings'] = 0

            # Get product mass
            new_product['mass'] = 0
            try:
                new_product['mass'] = float(re.search("[0-9.]+", re.search(" [0-9.]+(g|ml)", page_soup.find('h1',
                                                                                                            class_='pd__header').text).group(
                    0)).group(0)) / 1000
                try:
                    new_product['mass'] *= float(
                        re.search(" x[0-9]+", page_soup.find('h1', class_='pd__header').text).group(0)[2:])
                except:
                    pass
            except:
                try:
                    new_product['mass'] = float(re.search("[0-9.]+",
                                                          re.search(" [0-9.]+(kg|l)",
                                                                    page_soup.find('h1', class_='pd__header').text
                                                                    ).group(0)).group(0))
                    try:
                        new_product['mass'] *= float(
                            re.search(" x[0-9]+", page_soup.find('h1', class_='pd__header').text).group(0)[2:])
                    except:
                        pass
                except:
                    try:
                        mass = re.search("[0-9]+x[0-9.]+", re.search(" [0-9]+x[0-9]*.?[0-9]+(g|ml)",
                                                                     page_soup.find('h1',
                                                                                    class_='pd__header').text).group(
                            0)).group(0).split('x')
                        new_product['mass'] = float(mass[0]) * float(mass[1]) / 1000
                        if not new_product['pack_servings']:
                            new_product['pack_servings'] = int(mass[0])
                    except:
                        try:
                            mass = re.search("[0-9]+x[0-9.]+",
                                             re.search(" [0-9]+x[0-9]*.?[0-9]+(kg|l)", page_soup.find('h1',
                                                                                                      class_='pd__header').text).group(
                                                 0)).group(0).split('x')
                            new_product['mass'] = float(mass[0]) * float(mass[1])
                            if not new_product['pack_servings']:
                                new_product['pack_servings'] = int(mass[0])
                        except:
                            if new_product['pack_servings'] != 0:
                                try:
                                    new_product['mass'] = round(new_product['pack_servings'] * serving_size, 3)
                                except:
                                    pass

            if new_product['pack_servings'] != 0 and not new_product['mass']:
                try:
                    new_product['mass'] = round(new_product['pack_servings'] * serving_size, 3)
                except:
                    pass
            if new_product['mass'] and not new_product['pack_servings']:
                try:
                    new_product['pack_servings'] = round(new_product['mass'] / serving_size, 2)
                except:
                    pass

            # Get product ingredients
            try:
                new_product['ingredients'] = [ingredient.text.replace(', ', '') for ingredient in
                                              page_soup.find('h3', text='Ingredients').parent.ul.find_all('li')]
            except:
                try:
                    new_product['ingredients'] = page_soup.find('strong',
                                                                text=re.compile('INGREDIENTS:')).parent.text.replace(
                        'INGREDIENTS:', '').replace('INGREDIENTS: ', '').replace('.', '').split(',')
                except:
                    new_product['ingredients'] = []
            new_product['ingredients'] = str(new_product['ingredients'])

            # Get product allergens
            try:
                new_product['allergens'] = [ingredient.text.replace(', ', '') for ingredient in page_soup.find('h3',
                                                                                                               text=re.compile(
                                                                                                                   'Ingredients',
                                                                                                                   re.IGNORECASE)).parent.ul.find_all(
                    'span', style='font-weight: bold;')]
            except:
                try:
                    new_product['allergens'] = [x.text for x in
                                                page_soup.find('strong',
                                                               text=re.compile('INGREDIENTS:')).parent.find_all(
                                                    'strong')[1:]]
                except:
                    new_product['allergens'] = []
            new_product['allergens'] = str(new_product['allergens'])

            # Get product health information
            product_info = []
            health_heading = page_soup.find('h3', text=re.compile('Health', re.IGNORECASE))
            if health_heading:
                flag = False
                while not flag:
                    try:
                        health_heading = health_heading.find_next_sibling()
                        if health_heading.name == 'div':
                            product_info.append(health_heading.text)
                        else:
                            flag = True
                    except:
                        flag = True
            new_product['info'] = '\n'.join(product_info)

            # Get product cooking information
            cooking_info = []
            prep_heading = page_soup.find('h3', text=re.compile('Preparation', re.IGNORECASE))
            if prep_heading:
                flag = False
                while not flag:
                    try:
                        prep_heading = prep_heading.find_next_sibling()
                        if prep_heading.name == 'div':
                            cooking_info.append(prep_heading.text)
                        else:
                            flag = True
                    except:
                        flag = True
            new_product['cook_info'] = '\n'.join(cooking_info)

            # Get product country of origin
            product_origin = []
            origin_heading = page_soup.find('h3', text=re.compile('Country of Origin', re.IGNORECASE))
            if origin_heading:
                flag = False
                while not flag:
                    try:
                        origin_heading = origin_heading.find_next_sibling()
                        if origin_heading.name == 'div':
                            product_origin.append(origin_heading.text)
                        else:
                            flag = True
                    except:
                        flag = True
            if not product_origin:
                new_product['origin_country'] = 'United Kingdom'
            else:
                new_product['origin_country'] = '\n'.join(product_origin)

            # Get product packaging information
            product_recycling = []
            packaging_heading = page_soup.find('h3', text=re.compile('Packaging', re.IGNORECASE))
            if packaging_heading:
                flag = False
                while not flag:
                    try:
                        packaging_heading = packaging_heading.find_next_sibling()
                        if packaging_heading.name == 'div':
                            product_recycling.append(packaging_heading.text)
                        else:
                            flag = True
                    except:
                        flag = True
            new_product['recycling'] = '\n'.join(product_recycling)

            """for key in new_product:
                print(key, type(new_product[key]))
                print(new_product[key])
                print()"""

            new_products = new_products.append(new_product, ignore_index=True)

        # Delete any old products from the current sector
        heroku_upload()
        query_text = '''    
        DELETE FROM sainsburys_products
        WHERE sector_id = '**sector_id**'
        AND date_updated <> '**date**'
        '''.replace('**date**', date.today().strftime('%Y-%m-%d')).replace('**sector_id**', sector['uuid'])
        _ = postgres_execute(query_text)

        # Update the sector just scraped in the sectors database
        query_text = '''
        UPDATE sainsburys_sectors
        SET products_scraped = 1, num_products = **num_products**, date_updated = '**date**'
        WHERE path = '**path**'
        '''.replace('**path**', sector['path']).replace(
            '**num_products**', str(len(new_products))).replace('**date**', date.today().strftime('%Y-%m-%d'))
        _ = postgres_execute(query_text)

        sql_text = '''UPDATE sainsburys_sectors
        SET real_date_updated = CAST(date_updated AS DATE)'''
        _ = postgres_execute(sql_text)

        sql_text = '''UPDATE sainsburys_products
        SET real_date_updated = CAST(date_updated AS DATE)'''
        _ = postgres_execute(sql_text)

    try:
        driver.close()
    except:
        pass

import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
from Heroku_functions import postgres_execute, postgres_update, postgres_connect
from datetime import date
import time
import re
import geopy.distance
import ast

countries = ['andorra', 'united arab emirates', 'afghanistan', 'antigua and barbuda', 'anguilla', 'albania', 'armenia', 'angola', 'antarctica', 'argentina', 'american samoa', 'austria', 'australia', 'aruba', 'aland islands', 'azerbaijan', 'bosnia and herzegovina', 'barbados', 'bangladesh', 'belgium', 'burkina faso', 'bulgaria', 'bahrain', 'burundi', 'benin', 'saint-barthélemy', 'bermuda', 'brunei darussalam', 'bolivia', 'caribbean netherlands', 'brazil', 'bahamas', 'bhutan', 'bouvet island', 'botswana', 'belarus', 'belize', 'canada', 'cocos (keeling) islands', 'democratic republic of the congo', 'centrafrican republic', 'republic of the congo', 'switzerland', "côte d'ivoire", 'cook islands', 'chile', 'cameroon', 'china', 'colombia', 'costa rica', 'cuba', 'cabo verde', 'curaçao', 'christmas island', 'cyprus', 'czech republic', 'germany', 'djibouti', 'denmark', 'dominica', 'dominican republic', 'algeria', 'ecuador', 'estonia', 'egypt', 'western sahara', 'eritrea', 'spain', 'ethiopia', 'finland', 'fiji', 'falkland islands', 'micronesia (federated states of)', 'faroe islands', 'france', 'gabon', 'united kingdom', 'grenada', 'georgia', 'french guiana', 'guernsey', 'ghana', 'gibraltar', 'greenland', 'the gambia', 'guinea', 'guadeloupe', 'equatorial guinea', 'greece', 'south georgia and the south sandwich islands', 'guatemala', 'guam', 'guinea bissau', 'guyana', 'hong kong (sar of china)', 'heard island and mcdonald islands', 'honduras', 'croatia', 'haiti', 'hungary', 'indonesia', 'ireland', 'israel', 'isle of man', 'india', 'british indian ocean territory', 'iraq', 'iran', 'iceland', 'italy', 'jersey', 'jamaica', 'jordan', 'japan', 'kenya', 'kyrgyzstan', 'cambodia', 'kiribati', 'comores', 'saint kitts and nevis', 'north korea', 'south korea', 'kuwait', 'cayman islands', 'kazakhstan', 'laos', 'lebanon', 'saint lucia', 'liechtenstein', 'sri lanka', 'liberia', 'lesotho', 'lithuania', 'luxembourg', 'latvia', 'libya', 'morocco', 'monaco', 'moldova', 'montenegro', 'saint martin (french part)', 'madagascar', 'marshall islands', 'north macedonia', 'mali', 'myanmar', 'mongolia', 'macao (sar of china)', 'northern mariana islands', 'martinique', 'mauritania', 'montserrat', 'malta', 'mauritius', 'maldives', 'malawi', 'mexico', 'malaysia', 'mozambique', 'namibia', 'new caledonia', 'niger', 'norfolk island', 'nigeria', 'nicaragua', 'the netherlands', 'norway', 'nepal', 'nauru', 'niue', 'new zealand', 'oman', 'panama', 'peru', 'french polynesia', 'papua new guinea', 'philippines', 'pakistan', 'poland', 'saint pierre and miquelon', 'pitcairn', 'puerto rico', 'palestinian territory', 'portugal', 'palau', 'paraguay', 'qatar', 'reunion', 'romania', 'serbia', 'russia', 'rwanda', 'saudi arabia', 'solomon islands', 'seychelles', 'sudan', 'sweden', 'singapore', 'saint helena', 'slovenia', 'svalbard and jan mayen', 'slovakia', 'sierra leone', 'san marino', 'sénégal', 'somalia', 'suriname', 'são tomé and príncipe', 'south sudan', 'el salvador', 'saint martin (dutch part)', 'syria', 'eswatini', 'turks and caicos islands', 'chad', 'french southern and antarctic lands', 'togo', 'thailand', 'tajikistan', 'tokelau', 'timor-leste', 'turkmenistan', 'tunisia', 'tonga', 'turkey', 'trinidad and tobago', 'tuvalu', 'taiwan', 'tanzania', 'ukraine', 'uganda', 'united states minor outlying islands', 'united states of america', 'uruguay', 'uzbekistan', 'city of the vatican', 'saint vincent and the grenadines', 'venezuela', 'british virgin islands', 'united states virgin islands', 'vietnam', 'vanuatu', 'wallis and futuna', 'samoa', 'yemen', 'mayotte', 'south africa', 'zambia', 'zimbabwe']
emissions={'road':[0.2,0.5], 'rail':[0.05,0.06], 'sea':[0.01,0.02], 'air':[1.13,1.13]}
air_food = ['green bean', 'sweetcorn', 'asparagus', 'pea', 'lime', 'avocado', 'spring onion', 'pineapple', 'sweet potato', 'grape']

def heroku_upload():
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

def get_country_coords(country):
    # create url
    url = '{0}{1}{2}'.format('http://nominatim.openstreetmap.org/search?country=',
                             country,
                             '&format=json&polygon=0')
    response = requests.get(url).json()[0]
    # parse response to list
    lst = [response.get(key) for key in ['lat','lon']]
    return [float(i) for i in lst]

def get_countries_distance(a,b):
    return float(str(geopy.distance.distance(get_country_coords(a), get_country_coords(b)))[:-3])

def get_travel_emissions(dist,mass,transport_type,temp_controlled):
    return dist*mass*emissions[transport_type][bool(temp_controlled)]/1000

location = 'united kingdom'

num_sectors = 1

product_query = '''
SELECT sainsburys_products.*, sainsburys_sectors.food_emissions, sainsburys_sectors.food_emissions_default, sainsburys_sectors.temp_controlled FROM sainsburys_products
LEFT JOIN sainsburys_sectors
ON sainsburys_products.sector_id = sainsburys_sectors.uuid
'''
result = postgres_execute(product_query)


for index, row in result.iterrows():
    #Convert e.g. Grown in Argentina, Brazil, South Africa or France -> ['Argentina', 'Brazil', 'South Africa', 'France']
    product_countries = []
    a = str.lower(row['origin_country']).replace(',','').split(' ')
    for i in range(len(a)):
        for e in range(i+1,min(len(a),i+5)):
            x = a[i:e+1].join(' ')
            if x in countries:
                if x not in product_countries:
                    product_countries.append(x)
    #Get distance to UK for each country the product could have been produced in and average the data
    average_dist = sum([get_countries_distance(x,'United Kingdom') for x in product_countries])/float(len(product_countries))
    #Check if product is transported by sea or air, and whether it needs to be temperature controlled
    transport_type, temp_controlled = 'sea', False
    for item in air_food:
        if item in row['name']:
            transport_type = 'air'
    try:
        transport_emissions = get_travel_emissions(average_dist, row['mass'], transport_type, row['temp_controlled'])
    except:
        pass
    food_emissions = 0
    if row['emissions_condition']:
        emissions_conditions = ast.literal_eval(row['emissions_condition'])
        for condition in emissions_conditions.keys():
            meets_condition = True
            for word in condition.split(','):
                if not re.search(word, row['name']):
                    meets_condition = False
            if meets_condition:
                food_emissions = row['mass'] * emissions_conditions[condition]
                break
    if not food_emissions:
        if row['emissions_default']:
            food_emissions = row['mass'] * row['emissions_default']
    if food_emissions and transport_emissions:
        result.iloc[index]['emissions'] = food_emissions + transport_emissions



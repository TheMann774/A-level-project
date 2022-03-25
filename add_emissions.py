# import relevant modules
import requests
from Heroku_functions import postgres_execute
import geopy.distance

# List of countries in format supported by geopy:
countries = ['andorra', 'united arab emirates', 'afghanistan', 'antigua and barbuda', 'anguilla', 'albania', 'armenia',
             'angola', 'antarctica', 'argentina', 'american samoa', 'austria', 'australia', 'aruba', 'aland islands',
             'azerbaijan', 'bosnia and herzegovina', 'barbados', 'bangladesh', 'belgium', 'burkina faso', 'bulgaria',
             'bahrain', 'burundi', 'benin', 'saint-barthélemy', 'bermuda', 'brunei darussalam', 'bolivia',
             'caribbean netherlands', 'brazil', 'bahamas', 'bhutan', 'bouvet island', 'botswana', 'belarus', 'belize',
             'canada', 'cocos (keeling) islands', 'democratic republic of the congo', 'centrafrican republic',
             'republic of the congo', 'switzerland', "côte d'ivoire", 'cook islands', 'chile', 'cameroon', 'china',
             'colombia', 'costa rica', 'cuba', 'cabo verde', 'curaçao', 'christmas island', 'cyprus', 'czech republic',
             'germany', 'djibouti', 'denmark', 'dominica', 'dominican republic', 'algeria', 'ecuador', 'estonia',
             'egypt', 'western sahara', 'eritrea', 'spain', 'ethiopia', 'finland', 'fiji', 'falkland islands',
             'micronesia (federated states of)', 'faroe islands', 'france', 'gabon', 'united kingdom', 'grenada',
             'georgia', 'french guiana', 'guernsey', 'ghana', 'gibraltar', 'greenland', 'the gambia', 'guinea',
             'guadeloupe', 'equatorial guinea', 'greece', 'south georgia and the south sandwich islands', 'guatemala',
             'guam', 'guinea bissau', 'guyana', 'hong kong (sar of china)', 'heard island and mcdonald islands',
             'honduras', 'croatia', 'haiti', 'hungary', 'indonesia', 'ireland', 'israel', 'isle of man', 'india',
             'british indian ocean territory', 'iraq', 'iran', 'iceland', 'italy', 'jersey', 'jamaica', 'jordan',
             'japan', 'kenya', 'kyrgyzstan', 'cambodia', 'kiribati', 'comores', 'saint kitts and nevis', 'north korea',
             'south korea', 'kuwait', 'cayman islands', 'kazakhstan', 'laos', 'lebanon', 'saint lucia', 'liechtenstein',
             'sri lanka', 'liberia', 'lesotho', 'lithuania', 'luxembourg', 'latvia', 'libya', 'morocco', 'monaco',
             'moldova', 'montenegro', 'saint martin (french part)', 'madagascar', 'marshall islands', 'north macedonia',
             'mali', 'myanmar', 'mongolia', 'macao (sar of china)', 'northern mariana islands', 'martinique',
             'mauritania', 'montserrat', 'malta', 'mauritius', 'maldives', 'malawi', 'mexico', 'malaysia', 'mozambique',
             'namibia', 'new caledonia', 'niger', 'norfolk island', 'nigeria', 'nicaragua', 'the netherlands', 'norway',
             'nepal', 'nauru', 'niue', 'new zealand', 'oman', 'panama', 'peru', 'french polynesia', 'papua new guinea',
             'philippines', 'pakistan', 'poland', 'saint pierre and miquelon', 'pitcairn', 'puerto rico',
             'palestinian territory', 'portugal', 'palau', 'paraguay', 'qatar', 'reunion', 'romania', 'serbia',
             'russia', 'rwanda', 'saudi arabia', 'solomon islands', 'seychelles', 'sudan', 'sweden', 'singapore',
             'saint helena', 'slovenia', 'svalbard and jan mayen', 'slovakia', 'sierra leone', 'san marino', 'sénégal',
             'somalia', 'suriname', 'são tomé and príncipe', 'south sudan', 'el salvador', 'saint martin (dutch part)',
             'syria', 'eswatini', 'turks and caicos islands', 'chad', 'french southern and antarctic lands', 'togo',
             'thailand', 'tajikistan', 'tokelau', 'timor-leste', 'turkmenistan', 'tunisia', 'tonga', 'turkey',
             'trinidad and tobago', 'tuvalu', 'taiwan', 'tanzania', 'ukraine', 'uganda',
             'united states minor outlying islands', 'united states of america', 'uruguay', 'uzbekistan',
             'city of the vatican', 'saint vincent and the grenadines', 'venezuela', 'british virgin islands',
             'united states virgin islands', 'vietnam', 'vanuatu', 'wallis and futuna', 'samoa', 'yemen', 'mayotte',
             'south africa', 'zambia', 'zimbabwe']
# Some common alternative formats of countries:
country_swaps = {'uk': 'united kingdom', 'england': 'united kingdom', 'scotland': 'united kingdom',
                 'usa': 'united states of america', 'ireland': 'republic of ireland'}
# Emissions coefficients for various transportation types in format [ambient, chilled] measured in kg CO2 per kg per km:
emissions = {'road': [0.2, 0.5], 'rail': [0.05, 0.06], 'sea': [0.01, 0.02], 'air': [1.13, 1.13]}
# List of foods transported by air:
air_food = ['green bean', 'sweetcorn', 'asparagus', 'pea', 'lime', 'avocado', 'spring onion', 'pineapple',
            'sweet potato', 'grape', 'beef', 'chicken', 'lamb', 'pork', 'turkey']
# List of foods which are temperature controlled:
controlled_food = ['milk', 'egg', 'cream', 'yoghurt', 'beef', 'chicken', 'lamb', 'pork', 'turkey', 'frozen']


def get_country_coords(country):
    """Get the coordinates of the centre of a given country using OpenStreetMap, returns [lat, lon] or None if not found"""
    try:
        url = 'http://nominatim.openstreetmap.org/search?country=' + country + '&format=json&polygon=0'
        response = requests.get(url).json()[0]
    except:
        return None
    return [float(response.get(key)) for key in ['lat', 'lon']]


def get_countries_distance(a, b):
    """Get the distance between two sets of coordinates in km, return 0 if error"""
    try:
        return float(str(geopy.distance.distance(get_country_coords(a), get_country_coords(b)))[:-3])
    except:
        return 0


def get_travel_emissions(dist, mass, transport_type, temp_controlled):
    """Get the emissions of a transportation journey in kg CO2"""
    emission_coefficient = emissions[transport_type][int(temp_controlled)]
    return dist * mass * emission_coefficient / 1000


location = 'united kingdom'

# Get all products and their sector where emissions haven't been calculated
product_query = '''
SELECT sainsburys_products.*, sainsburys_sectors.name AS sector_name FROM sainsburys_products
LEFT JOIN sainsburys_sectors
ON sainsburys_products.sector_id = sainsburys_sectors.uuid
WHERE emissions IS NULL
'''
result = postgres_execute(product_query)

# Get the data from emissions_stats
links_query = '''
SELECT product_contains, product_not_contains, sector_contains, emissions
FROM emissions_stats
'''
links = postgres_execute(links_query)

# Loop through products
for index, row in result.iterrows():
    print(index)
    transport_emissions = -1
    # Convert e.g. 'Grown in Argentina, Brazil, South Africa or France' -> ['Argentina', 'Brazil', 'South Africa', 'France']
    product_countries = []
    a = str.lower(row['origin_country']).replace(',', '').replace('\n', ' ').split(' ')
    a = [x.strip().replace('.', '') for x in a]
    for i in range(len(a)):
        for e in range(i, min(len(a), i + 5)):
            term = str.lower(' '.join(a[i:e + 1]))
            if term in countries:
                if term not in product_countries:
                    product_countries.append(term)
            elif term in country_swaps.keys():
                if country_swaps[term] not in product_countries:
                    product_countries.append(country_swaps[term])
    if product_countries:
        # Get distance to UK for each country the product could have been produced in and average the data
        average_dist = sum([get_countries_distance(x, 'united kingdom') for x in product_countries]) / float(
            len(product_countries))
        # Check if product is transported by sea or air, and whether it needs to be temperature controlled
        transport_type, temp_controlled = 'sea', False
        for item in air_food:
            if item in str.lower(row['name']):
                transport_type = 'air'
        for item in controlled_food:
            if item in str.lower(row['name']):
                temp_controlled = True
        try:
            transport_emissions = get_travel_emissions(average_dist, row['mass'], transport_type, temp_controlled)
        except:
            pass
    else:
        transport_emissions = 0

    food_emissions = 0
    match = None
    valid = True
    # Find food type which matches the product:
    for index2, row2 in links.iterrows():
        if list(row2).count('NaN') < 3:
            match_row = True

            if row2['product_contains'] != 'NaN':
                match_product_contains = False
                for condition in row2['product_contains'].split(' or '):
                    if False not in [str.lower(x) in str.lower(row['name']) for x in condition.split(',')]:
                        match_product_contains = True
                if not match_product_contains:
                    match_row = False

            if row2['sector_contains'] != 'NaN':
                match_sector_contains = False
                for condition in row2['sector_contains'].split(' or '):
                    if False not in [str.lower(x) in str.lower(row['sector_name']) for x in condition.split(',')]:
                        match_sector_contains = True
                if not match_sector_contains:
                    match_row = False

            if row2['product_not_contains'] != 'NaN':
                match_product_not_contains = True not in [str.lower(x) in str.lower(row['name']) for x in
                                                          row2['product_not_contains'].split(',')]
                if not match_product_not_contains:
                    match_row = False

            if match_row:
                if match:
                    valid = False
                else:
                    match = index2

    if valid and match:
        if row['mass']:
            food_emissions = row['mass'] * links.iloc[match]['emissions']  # Calculate food emissions
    if food_emissions and transport_emissions != -1:
        result.iloc[index, -2] = round(food_emissions + transport_emissions, 3)  # Update DataFrame
    else:
        if not food_emissions:
            print(row['name'])
        if transport_emissions == -1:
            print(row['origin_country'])
        result.iloc[index, -2] = 0

    # Update database:
    sql_text = '''
    UPDATE sainsburys_products
    SET emissions = **emissions**
    WHERE uuid = '**uuid**'
    '''.replace('**emissions**', str(result.iloc[index, -2])).replace('**uuid**', result.iloc[index]['uuid'])
    _ = postgres_execute(sql_text)


# Calculate metrics:
sql_text = '''
UPDATE sainsburys_products
SET emissions_per_kg = emissions/mass
WHERE mass > 0
'''
_ = postgres_execute(sql_text)

sql_text = '''
UPDATE sainsburys_products
SET emissions_per_portion = emissions/pack_servings
WHERE pack_servings > 0
'''
_ = postgres_execute(sql_text)

sql_text = '''
UPDATE sainsburys_products
SET emissions_per_calorie = 1000*emissions/CAST(SUBSTRING(nutrition_100, 
    POSITION('Energy' IN nutrition_100)+9, 
    POSITION('.' IN nutrition_100)-POSITION('Energy' IN nutrition_100)-7) AS float)/10/mass
WHERE POSITION('Energy' IN nutrition_100) > 0 AND mass > 0
'''
_ = postgres_execute(sql_text)

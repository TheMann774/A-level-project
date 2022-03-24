import pandas as pd
from Heroku_functions import postgres_connect, postgres_execute


def heroku_upload():
    """upload database of new-found products to heroku"""
    print("uploading", len(data), "rows to heroku")
    records = data.itertuples(index=False)
    result = list(records)
    records_list_template = ','.join(['%s'] * len(result))

    insert_query = '''INSERT INTO "emissions_stats" (
        food_commodity,
        product_contains,
        sector_contains,
        product_not_contains,
        emissions)
                    VALUES {}'''.format(records_list_template)

    conn = postgres_connect()
    cur = conn.cursor()
    cur.execute(insert_query, result)
    conn.commit()
    print("rows uploaded")


data = pd.read_csv('SuEatableLife_Food_Fooprint_database.csv').iloc[:324, :5]
del_query = '''
DELETE FROM emissions_stats
'''
postgres_execute(del_query)
heroku_upload()


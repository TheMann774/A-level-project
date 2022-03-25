import psycopg2
import pandas as pd


def postgres_connect():
    """Connect to the database"""
    PG_DBNAME = 'dflk6gukmji6li'
    PG_USER = 'xvfgvajqxphekv'
    PG_HOST = 'ec2-63-33-239-176.eu-west-1.compute.amazonaws.com'
    PG_PASSWORD = '8383cbb76aaef34af07f86a02178d9614e78e139af51a27c627e75706cd3a35f'

    connect_text = "dbname=" + PG_DBNAME + " user=" + PG_USER + " host=" + PG_HOST + " password=" + PG_PASSWORD

    try:
        conn = psycopg2.connect(connect_text)
        conn.set_session(readonly=False)  # *******WRITE-ENABLED CONNECTION*******
        return conn
    except psycopg2.Error as e:
        error_info = str(e)
        error_message = 'Failed to connect to database. Error: {' + error_info + '}'
        print(error_message)
        raise ConnectionError


def postgres_execute(sql_text):
    """Execute an SQL query"""
    conn = postgres_connect()
    cur = conn.cursor()
    # rollback any errors
    # cur.execute("ROLLBACK")
    cur.execute(sql_text)
    try:
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        result = pd.DataFrame(rows, columns=colnames)

    except:
        result = pd.DataFrame()
    conn.commit()
    cur.close()
    conn.close()
    return result


def postgres_update(conn, sql_text, value, value2, value3, idval):
    """Update a database"""
    if (conn is None) or (conn.closed == 1):
        conn = postgres_connect()
    cur = conn.cursor()

    updated_rows = 0
    try:
        cur.execute(sql_text, (value, value2, value3, idval))
        updated_rows = cur.rowcount
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    return conn, updated_rows

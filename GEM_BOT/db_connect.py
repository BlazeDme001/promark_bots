from contextlib import contextmanager
from configparser import ConfigParser
# from datetime import datetime
import os
import psycopg2
from psycopg2 import connect
import pandas as pd


PARSER = ConfigParser()
FILENAME = os.path.join(os.getcwd(), 'config.ini')
SECTION = 'prod'
PARSER.read(FILENAME)

if PARSER.has_section(SECTION):
    PARAMS = dict(PARSER.items(SECTION))
else:
    print(f'Section {SECTION} not found in the {FILENAME} file')
    raise Exception(f"Section {SECTION} not found in the {FILENAME} file")

class invalid_function_call(Exception):
    print("Calling database...")


@contextmanager
def postgres_connection():
    conn = psycopg2.connect(**PARAMS)
    try:
        yield conn
    finally:
        conn.close()

# @contextmanager
# def get_curser():
#     conn = connect(**PARAMS)
#     try:
#         yield conn.cursor()
#         conn.commit()
#     except Exception as error:
#         conn.rollback()
#         raise error
#     finally:
#         conn.close()


def execute(query, values=None):
    try:
        conn = connect(**PARAMS)
        cur = conn.cursor()
        if values:
            cur.execute(query, values)
        else:
            cur.execute(query)
        conn.commit()
        conn.close()
        return True
    except:
        return False


def get_data_in_list_of_tuple(query):
    with postgres_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()


def get_row_as_dframe(query, args=None):
    try:
        if not isinstance(args, list) and args is not None:
            raise invalid_function_call("please pass a list of values as arguments to the function call")

        conn = connect(**PARAMS)
        cur = conn.cursor()
        cur.execute(query, args)
        results_set = cur.fetchall()
        conn.commit()
        conn.close()
        # with get_curser() as cur:
        #     cur.execute(query, args)
        #     results_set = cur.fetchall()

        headers = [desc[0] for desc in cur.description]
        data = pd.DataFrame(results_set, columns=headers)
        # data = data.to_dict('records')
        return data
    except Exception as error:
        print("exception at db fetch error: ",error)
    finally:
        cur.close()


def insert_dict_into_table(table_name, data_dict):
    value_list = [tuple(data_dict.values())]
    headers = list(data_dict.keys())
    conn = connect(**PARAMS)
    cur = conn.cursor()
    # conn.close()
    cur.execute(
        f"""INSERT INTO {table_name} ("{'","'.join(headers)}") VALUES %s on conflict do nothing;""",
        value_list
    )
    conn.commit()
    conn.close()
    return cur.rowcount


# def insert_df_into_table(table_name, dframe):
#     date_tuple = [tuple(x) for x in dframe.values]
#     headers = dframe.columns
#     conn = connect(**PARAMS)
#     cur = conn.cursor()
#     cur.execute(
#     f"""INSERT INTO {table_name} ({', '.join(headers)}) VALUES %s on conflict do nothing;""", date_tuple)
#     conn.commit()
#     conn.close()
#     row_count = cur.rowcount
#     return row_count


def insert_df_into_table(table_name, dframe):
    date_tuple = [tuple(x) for x in dframe.values]
    headers = dframe.columns
    conn = connect(**PARAMS)
    cur = conn.cursor()

    placeholders = ', '.join(['%s'] * len(headers))
    query = f"INSERT INTO {table_name} ({', '.join(headers)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"

    cur.executemany(query, date_tuple)
    conn.commit()
    row_count = cur.rowcount

    conn.close()
    return row_count


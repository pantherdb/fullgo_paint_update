import psycopg2
import yaml
import argparse
from os import path
from sys import exit

parser = argparse.ArgumentParser()
parser.add_argument("query_filename")

with open("config/config.yaml") as f:
    cfg = yaml.load(f)

host = cfg["host"]
dbname = cfg["dbname"]
username = cfg["username"]
pword = cfg["pword"]

def get_connection():
    con = psycopg2.connect("dbname = {} user={} host={} password={}".format(dbname,
                                                                            username,
                                                                            host,
                                                                            pword))
    return con

def exec_query(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    print(cursor.query.decode("utf-8"))
    try:
        res = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        res.insert(0, colnames)
    except psycopg2.ProgrammingError:
        # Could be due to insert
        print(cursor.statusmessage)
        res = []
    connection.commit()
    return res

def format_results(results, delimiter=";"):
    formatted_results = []
    for r in results:
        vals = []
        for val in r:
            if val is None:
                val = ''
            else:
                val = str(val)
            vals.append(val)
        formatted_results.append(";".join(vals))
    return formatted_results

if __name__ == "__main__":
    args = parser.parse_args()
    qfile = args.query_filename
    if not path.isfile(qfile):
        print("ERROR: No such query file '{}'.".format(qfile))
        exit()
    with open(qfile) as qf:
        # print(qf.read())
        # results = []
        con = get_connection()
        results = exec_query(con, qf.read())
        con.close()
    for r in format_results(results):
        print(r)
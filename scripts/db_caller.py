import psycopg2
import yaml
import argparse
import datetime
from os import path
from sys import exit

parser = argparse.ArgumentParser()
parser.add_argument("query_filename")
# Only use query variables for single query SQL files, otherwise managing these gets tricky due to the per-statement cleaning step.
parser.add_argument("-v", "--query_variables", type=str, required=False, help="comma-delimited, ordered list of values to replace variables in SQL script.\
                                                Only use query variables for single query SQL files, otherwise managing these gets tricky due to the per-statement cleaning step.")

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
    try:
        cursor.execute(query)
    except psycopg2.Error as e:
        print(query)
        print(e.__class__.__name__, ":", e.diag.message_primary)
        raise e
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

def clean_query(raw_query, query_variables=None):
    noncommented_lines = []
    for line in raw_query.split("\n"):
        if not line.startswith("--") and line != "":
            noncommented_lines.append(line)
    cleaned_query = "\n".join(noncommented_lines)
    statement_var_count = cleaned_query.count("{}")
    if query_variables:
        provided_var_count = len(query_variables)
        if statement_var_count == provided_var_count:
            cleaned_query = cleaned_query.format(*query_variables)
        else:
            print(cleaned_query)
            print("ERROR: Non-matching number of variables in statement ({}) to number of variables provided ({})".format(statement_var_count, provided_var_count))
            exit()
    elif statement_var_count > 0:
        print(cleaned_query)
        print("ERROR: {} variables detected in statement but no variables provided".format(statement_var_count))
        exit()
    return cleaned_query

if __name__ == "__main__":
    args = parser.parse_args()
    qfile = args.query_filename
    query_variables = None
    if args.query_variables:
        query_variables = args.query_variables.split(",")
    if not path.isfile(qfile):
        print("ERROR: No such query file '{}'.".format(qfile))
        exit()
    with open(qfile) as qf:
        con = get_connection()
        query_text = qf.read()
        results = []
        query_statements = query_text.split(";")
        query_statements = list(filter(None, query_statements)) # Filter out empty strings
        if query_variables and len(query_statements) > 1:
            print("ERROR: Shouldn't (yet) use query variables for multi-statement SQL files")
            exit()
        for statement in query_statements:
            # Add block if variables and multi-statement
            cleaned_query = clean_query(statement, query_variables=query_variables)
            if cleaned_query:
                start_time = datetime.datetime.now()
                results = exec_query(con, cleaned_query + ";")
                for r in format_results(results):
                    print(r)
                print("Execution time:", datetime.datetime.now() - start_time, "- Host:", host, "- DB:", dbname)
        con.close()
import psycopg2
import yaml
import json
import argparse
import datetime
from os import path
from sys import exit

parser = argparse.ArgumentParser()
parser.add_argument("query_filename")
# Only use query variables for single query SQL files, otherwise managing these gets tricky due to the per-statement cleaning step.
parser.add_argument("-v", "--query_variables", type=str, required=False, help="comma-delimited, ordered list of values to replace variables in SQL script.\
                                                Only use query variables for single query SQL files, otherwise managing these gets tricky due to the per-statement cleaning step.")
parser.add_argument("-o", "--rows_outfile", help="Write result rows to specified filename.")
parser.add_argument("-d", "--delimiter", help="column delimiter to display in query output.")
parser.add_argument("-n", "--no_header_footer", action='store_const', const=True, help="No header or footer will be included in query result output")

class DBCallerConfig:
    def __init__(self, config_path="config/config.yaml"):

        with open(config_path) as f:
            cfg = yaml.load(f)

        for df in cfg["DB_DEFINITIONS"]["value"]:
            if df["id"] == cfg["DB_DEFINITION"]["value"]:
                chosen_df = df

        self.host = chosen_df["host"]
        self.dbname = chosen_df["dbname"]
        self.username = chosen_df["username"]
        self.pword = chosen_df["pword"]
        self.db_version = chosen_df.get("db_version")
        self.load_dir = chosen_df.get("load_dir")
        self.classification_version_sid = chosen_df.get("classification_version_sid")

def get_connection(config):
    con = psycopg2.connect("dbname = {} user={} host={} password={}".format(config.dbname,
                                                                            config.username,
                                                                            config.host,
                                                                            config.pword))
    return con

def exec_query(connection, query, omit_header=None):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
    except psycopg2.Error as e:
        print(query)
        print(e.__class__.__name__, ":", e.diag.message_primary)
        raise e
    if omit_header is None:
        print(cursor.query.decode("utf-8"))
    try:
        res = cursor.fetchall()
        colnames = [desc[0] for desc in cursor.description]
        res.insert(0, colnames)
    except psycopg2.ProgrammingError:
        # Could be due to insert
        print(cursor.statusmessage)
        res = []
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
        formatted_results.append(delimiter.join(vals))
    return formatted_results

def handle_config_variables(raw_query, config):
    cleaned_query = raw_query
    if "{load_dir}" in cleaned_query:
        # load_dir = chosen_df.get("load_dir")
        cleaned_query = cleaned_query.replace("{load_dir}", config.load_dir)
    if "{classification_version_sid}" in cleaned_query:
        # classification_version_sid = chosen_df.get("classification_version_sid")
        cleaned_query = cleaned_query.replace("{classification_version_sid}", str(config.classification_version_sid))
    return cleaned_query

def clean_query(raw_query, config, query_variables=None):
    cleaned_query = raw_query
    if cleaned_query.lstrip().startswith("--"):
        return None
    cleaned_query = handle_config_variables(cleaned_query, config)
    statement_var_count = cleaned_query.count("{}")
    if query_variables:
        if query_variables.__class__ == dict:
            cleaned_query = cleaned_query.format(**query_variables)
        elif statement_var_count > 0:
            # query_variables is likely a list
            provided_var_count = len(query_variables)
            if statement_var_count == provided_var_count:
                cleaned_query = cleaned_query.format(*query_variables)
            else:
                print("ERROR: Non-matching number of variables in statement ({}) to number of variables provided ({})".format(statement_var_count, provided_var_count))
                exit() #TODO: Get this to crash the whole make recipe
    elif statement_var_count > 0:
        print(cleaned_query)
        print("ERROR: {} variables detected in statement but no variables provided".format(statement_var_count))
        exit()
    return cleaned_query

def clean_file(raw_file_text):
    noncommented_lines = []
    for line in raw_file_text.split("\n"):
        if not line.lstrip().startswith("--") and line != "":
            noncommented_lines.append(line)
    cleaned_file = "\n".join(noncommented_lines)
    return cleaned_file

if __name__ == "__main__":
    args = parser.parse_args()
    qfile = args.query_filename
    config = DBCallerConfig()
    query_variables = None
    if args.query_variables:
        try:
            query_variables = json.loads(args.query_variables)
        except json.decoder.JSONDecodeError:
            query_variables = args.query_variables.split(",")
    if not path.isfile(qfile):
        print("ERROR: No such query file '{}'.".format(qfile))
        exit()
    rows_outfile = None
    if args.rows_outfile:
        rows_outfile = open(args.rows_outfile, "w+")
    with open(qfile) as qf:
        con = get_connection(config)
        query_text = qf.read()
        results = []
        query_text = clean_file(query_text)
        query_statements = query_text.split(";")
        query_statements = list(filter(None, query_statements)) # Filter out empty strings
        if query_variables and len(query_statements) > 1:
            print("WARNING: Should be careful using query variables for multi-statement SQL files")
            # exit()
        for statement in query_statements:
            # Add block if variables and multi-statement
            cleaned_query = clean_query(statement, config, query_variables=query_variables)
            if cleaned_query:
                start_time = datetime.datetime.now()
                results = exec_query(con, cleaned_query + ";", omit_header=args.no_header_footer)
                if args.delimiter:
                    formatted_results = format_results(results, delimiter=args.delimiter)
                else:
                    formatted_results = format_results(results)
                for r in formatted_results:
                    if rows_outfile:
                        rows_outfile.write("{}\n".format(r))
                    else:
                        print(r)
                if args.no_header_footer is None:
                    if len(results) > 0:    # Display row count unless insert, update, set, etc.
                        print("Rows returned:", len(results) - 1)
                    print("Execution time:", datetime.datetime.now() - start_time, "- Host:", config.host, "- DB:", config.dbname)
        con.commit()
        con.close()
    if rows_outfile:
        rows_outfile.close()
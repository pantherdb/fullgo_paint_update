import psycopg2
import yaml

with open("config/config.yaml") as f:
    cfg = yaml.load(f)

host = cfg["host"]
dbname = cfg["dbname"]
username = cfg["username"]
pword = cfg["pword"]

con = psycopg2.connect("dbname = {} user={} host={} password={}".format(dbname,
                                                                        username,
                                                                        host,
                                                                        pword))

def exec_query(connection, query):
    cursor = connection.cursor()
    cursor.execute(query)
    res = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    res.insert(0, colnames)
    return res

if __name__ == "__main__":
    results = exec_query(con, "select * from panther_upl.go_aggregate limit 5;")
    for r in results:
        vals = []
        for val in r:
            if val is None:
                val = ''
            else:
                val = str(val)
            vals.append(val)
        print(",".join(vals))
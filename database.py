import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
database = os.getenv("database")
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")

conn = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
cur = conn.cursor()
'''cur.execute("""
    CREATE TABLE pcr_tw_news(
        time TEXT,
        type TEXT,
        title TEXT,
        url TEXT
    );
    CREATE TABLE webhooklist(
        url TEXT
    );
""")'''
#cur.execute("DELETE FROM pcr_tw_news;")
cur.execute("DELETE FROM webhooklist;")
cur.execute("INSERT INTO webhooklist VALUES ('https://discord.com/api/webhooks/942361244843769877/8ug7YA50Map9ScJUeYu5CGDR929X14LF3hprMDf0XMsFykgHDo3HZOuNAMZbqxuwKSZS');")
#cur.execute("SELECT * FROM pcr_tw_news;")
#cur.execute("SELECT * FROM webhooklist;")
conn.commit()
conn.close()
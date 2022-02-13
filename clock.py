from apscheduler.schedulers.blocking import BlockingScheduler
import discord
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import psycopg2
import requests
from datetime import datetime
from time import sleep

load_dotenv()
database = os.getenv("database")
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
client = discord.Client()

sched = BlockingScheduler()

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
}

@sched.scheduled_job("interval", minutes=5)
def pcr_tw_news():
    r = requests.get("http://www.princessconnect.so-net.tw/news", headers=header)
    soup = BeautifulSoup(r.text, "html.parser")
    news_con = soup.select_one(".news_con dl")
    news_time = news_con.find_all("dt")
    news_title = news_con.find_all("dd")
    news = []
    for i in range(0, len(news_time)):
        news.append({
            "time": news_time[i].find(text=True).strip(),
            "type": news_time[i].span.text,
            "title": news_title[i].text,
            "url": news_title[i].a["href"],
        })
    news.reverse()
    conn = psycopg2.connect(database=database, user=user, password=password, host=host, port=port)
    cur = conn.cursor()
    for i in news:
        time = i["time"]
        type = i["type"]
        title = i["title"]
        url = i["url"]
        if "外掛停權" not in title:
            cur.execute("SELECT COUNT(*) FROM pcr_tw_news WHERE time='" + time + "' and type='" + type + "' and title='" + title + "' and url='" + url + "';")
            rows = cur.fetchall()
            if rows[0][0] == 0:
                cur.execute("INSERT INTO pcr_tw_news VALUES ('" + time + "', '" + type + "', '" + title + "', '" + url + "');")
                r = requests.get("http://www.princessconnect.so-net.tw" + url, headers=header)
                soup = BeautifulSoup(r.text, "html.parser")
                content = soup.select_one(".news_con section p")
                content = BeautifulSoup(str(content).replace("<br/>", "\n"), "html.parser").getText().strip()
                data = {
                    "username": "pcr台版公告轉發機器人",
                    "embeds": [
                        {
                            "author": {"name": "超異域公主連結☆Re:Dive - " + time},
                            "title": title,
                            "url": "http://www.princessconnect.so-net.tw" + url,
                            "description": content,
                            "timestamp": datetime.utcnow().isoformat(),
                            "color": 1814232,
                            "thumbnail": {"url": "https://i.imgur.com/e4KrYHe.png"},
                        }
                    ]
                }
                cur.execute("SELECT * FROM webhooklist;")
                rows = cur.fetchall()
                for row in rows:
                    webhookurl = row[0]
                    result = requests.post(webhookurl, json=data)
                    print(webhookurl)
                    try:
                        result.raise_for_status()
                    except requests.exceptions.HTTPError as error:
                        print(error)
                    else:
                        print("Payload delivered successfully, code {}.".format(result.status_code))
                sleep(1)

    conn.commit()
    conn.close()

sched.start()
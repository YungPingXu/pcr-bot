import discord
import re
from dotenv import load_dotenv
import os
from discord.ext import tasks
import psycopg2
import requests
from datetime import datetime
from time import sleep
from bs4 import BeautifulSoup

load_dotenv()
bot_token = os.getenv("bot_token")
database = os.getenv("database")
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
client = discord.Client()

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
}

def checktime(number): # 檢查是不是合法的時間
    return (number >= 0 and number <= 130) and \
           ((number // 100 == 0 and number % 100 <= 59 and number % 100 >= 0) or \
           (number // 100 == 1 and number % 100 <= 30 and number % 100 >= 0))

def transform_time(original_time): # 轉換秒數
    result = ""
    if original_time < 60:
        if original_time < 10:
            result += "00" + str(original_time)
        else:
            result += "0" + str(original_time)
    else:
        if 60 <= original_time < 70:
            result += str(original_time // 60) + "0" + str(original_time % 60)
        else:
            result += str(original_time // 60) + str(original_time % 60)
    return result

@client.event
async def on_message(message): # 當有訊息時
    if message.author == client.user: # 排除自己的訊息，避免陷入無限循環
        return
    try:
        message1 = message.content.lower() # 轉為小寫
        message2 = "" 
        for c in message1:
            if c in ("，", "、", "。"):
                message2 += c
            elif 65281 <= ord(c) <= 65374:
                message2 += chr(ord(c) - 65248)
            elif ord(c) == 12288: # 空格字元
                message2 += chr(32)
            else:
                message2 += c
        # message2 將 message1 轉為半形
        if re.match(r"\s*\.tr\s*[\s\S]+", message2):
            tr = re.match(r"\s*\.tr\s*(\d+)\s*\n([\s\S]+)", message2)
            if tr:
                time = int(tr.group(1))
                if 1 <= time <= 90:
                    lines = tr.group(2).split("\n")
                    resultline = ""
                    for line in lines:
                        filter = line.replace(":", "").replace("\t", "") # 過濾特殊字元
                        match = re.match(r'(\D*)(\d{2,3})((\s*[~-]\s*)(\d{2,3}))?(.*)?', filter) # 擷取時間
                        if match:
                            content1 = match.group(1) # 時間前面的文字
                            timerange = match.group(3) # 056~057 這種有範圍的時間
                            time1 = int(match.group(2)) # 有範圍的時間 其中的第一個時間
                            time2 = 0
                            if timerange is not None and match.group(5) is not None:
                                time2 = int(match.group(5)) # 有範圍的時間 其中的第二個時間
                            rangecontent = match.group(4) # 第一個時間和第二個時間中間的字串
                            content2 = match.group(6) # 時間後面的文字
                            if checktime(time1) and ((timerange is None and match.group(5) is None) or (timerange is not None and match.group(5) is not None and checktime(time2))):
                                totaltime1 = time1 % 100 + (time1 // 100) * 60 # time1的秒數
                                newtime1 = totaltime1 - (90 - time)
                                result = ""
                                if newtime1 < 0: # 如果時間到了 後續的就不要轉換
                                    continue # 迴圈跳到下一個
                                if match.group(5) is None:
                                    result = content1 + transform_time(newtime1) + content2
                                else:
                                    totaltime2 = time2 % 100 + time2 // 100 * 60 # time2的秒數
                                    newtime2 = totaltime2 - (90 - time)
                                    result = content1 + transform_time(newtime1) + rangecontent + transform_time(newtime2) + content2
                                resultline += result
                            else:
                                resultline += line
                        else:
                            resultline += line
                        resultline += "\n"
                    await message.channel.send(resultline)
                else:
                    await message.channel.send("您輸入的補償秒數錯誤，秒數必須要在 1～90 之間！")
            else:
                await message.channel.send("您輸入的秒數格式錯誤！正確的格式為\n.tr 補償秒數\n文字軸\n\n(補償秒數後面請直接換行，不要有其他字元)")
    except Exception as e:
        print(e)

@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))

@tasks.loop(minutes=5)
async def sonet_news_forward():
    print("Running sonet_news_forward...")
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
    print("Finished running sonet_news_forward.")

sonet_news_forward.start()
client.run(bot_token) # the token of your bot
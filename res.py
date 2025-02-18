import requests
n = 1

json = {
    "token": "",
    "user_id": "1073383604576591974",
    "channel_id": "1100148368996573265",
    "guild_id": "1077968892535775262",
    "query": "lovers rock"}

if n == 1:
    url = requests.post("http://localhost:8000/play-music", json=json)

print(url.text)
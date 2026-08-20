import requests
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime, timezone


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.environ["FOOTBALL_DATA_TOKEN"]
if not TOKEN:
    raise SystemExit("Brak podanego FOOTBALL_DATA_TOKEN w .env")

TEAM_ID=66
TEAM_NAME="Manchester United"


resp = requests.get(f"https://api.football-data.org/v4/teams/{TEAM_ID}/matches", 
                     headers={"X-Auth-Token": TOKEN},
                     params={"status": "FINISHED","season": 2025}, 
                     timeout=10
                     )
resp.raise_for_status


matches = resp.json()["matches"][-10:]

for m in reversed(matches):
    date = m["utcDate"][:10]
    home = m["homeTeam"]["shortName"]
    away = m["awayTeam"]["shortName"]
    ft = m["score"]["fullTime"]
    ref = m["referees"][0]["name"]
    print(f'{date} {home} {ft["home"]}:{ft["away"]} {away}\tREF: {ref}')
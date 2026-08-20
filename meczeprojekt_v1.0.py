import requests
import os
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.environ["FOOTBALL_DATA_TOKEN"]
if not TOKEN:
    raise SystemExit("Brak podanego FOOTBALL_DATA_TOKEN w .env")

TEAM_ID=66
TEAM_NAME="Manchester United"

def fetch_matches(limit=10):
    resp = requests.get(f"https://api.football-data.org/v4/teams/{TEAM_ID}/matches", 
                     headers={"X-Auth-Token": TOKEN},
                     params={"status": "FINISHED","season": 2025}, 
                     timeout=10
                     )
    resp.raise_for_status
    return resp.json()["matches"][-limit:]

def build_rows(matches):
    rows = []
    for m in reversed(matches):
        ft = m["score"]["fullTime"]
        is_home = m["homeTeam"]["id"] == TEAM_ID
        scored, conceded = (ft["home"], ft["away"]) if is_home else (ft["away"], ft["home"])

        if scored > conceded:
            result = "W"
        elif scored < conceded:
            result = "L"
        else:
            result = "D"

        ref = next(
            (r["name"] for r in m.get("referees", []) if r.get("type") == "REFEREE"),
            "-",
        )

        rows.append({
            "date": m["utcDate"][:10],
            "home": m["homeTeam"]["shortName"],
            "away": m["awayTeam"]["shortName"],
            "home_crest": m["homeTeam"].get("crest", ""),
            "away_crest": m["awayTeam"].get("crest", ""),
            "score": f'{ft["home"]}:{ft["away"]}',
            "competition": m["competition"]["name"],
            "referee": ref,
            "result": result
        })
    return rows

def render(rows):
    env = Environment(
        loader=FileSystemLoader(BASE_DIR / "templates"),
        autoescape=True,
    )
    html = env.get_template("index.html").render(
        team=TEAM_NAME,
        rows=rows,
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )
    out = BASE_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Zapisano: {out}")

render(build_rows(fetch_matches()))
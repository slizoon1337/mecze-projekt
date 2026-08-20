from fastapi.responses import FileResponse
import requests
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Query


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")
if not TOKEN:
    raise SystemExit("Brak podanego FOOTBALL_DATA_TOKEN w .env")

API = "https://api.football-data.org/v4"
HEADERS = {"X-Auth-Token": TOKEN}
CACHE_TTL = 3600
FRONTEND = BASE_DIR / "templates" / "app.html"
WINDOW_DAYS = 740

app = FastAPI(title="Ostatnie mecze v2")
_cache = {}

def api_get(path, **params):
    """Zapytanie do football-data.org z cache, zeby nie przekraczac 10/min."""
    key = (path, tuple(sorted(params.items())))
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]

    resp = requests.get(f"{API}{path}", headers=HEADERS, params=params, timeout=15)

    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(502, f"API nie zwrocilo JSSON-a (HTTP {resp.status_code})")

    if resp.status_code != 200 or "errorCode" in data:
        raise HTTPException(502, data.get("message") or f"Blad API (HTTP {resp.status_code})")

    _cache[key] = (time.monotonic(), data)
    return data

def label(t):
    return t.get("shortName") or t.get("name") or t.get("tla") or "?"

def build_row(m, team_id):
    ft = m["score"]["fullTime"]
    is_home = m["homeTeam"]["id"] == team_id
    winner = m["score"].get("winner")

    if winner == "DRAW":
        result = "D"
    elif winner in ("HOME_TEAM", "AWAY_TEAM"):
        result = "W" if (winner == "HOME_TEAM") == is_home else "L"
    else:
                scored, conceded = (ft["home"], ft["away"]) if is_home else (ft["away"], ft["home"])
                result = "W" if scored > conceded else "L" if scored < conceded else "D"

    return {
         "date": m["utcDate"][:10],
         "home": label(m["homeTeam"]),
         "away": label(m["awayTeam"]),
         "home_crest": m["homeTeam"].get("crest") or "",
         "away_crest": m["awayTeam"].get("crest") or "",
         "score": f'{ft["home"]}:{ft["away"]}',
         "competition": m["competition"]["name"],
         "referee": next(
              (r["name"] for r in m.get("referees", []) if r.get("type") == "REFEREE"),
              "-",
         ),
         "result": result
    }


@app.get("/")
def index():
     if not FRONTEND.exists():
          raise HTTPException(500, f"Brak pliku frontendu: {FRONTEND}")
     return FileResponse(FRONTEND)

@app.get("/api/areas")
def areas():
     comps = api_get("/competitions")["competitions"]
     return sorted({c["area"]["name"] for c in comps})

@app.get("/api/competitions")
def competitions(area: str):
     comps = api_get("/competitions")["competitions"]
     out = [
          {"code": c["code"], "name": c["name"]}
          for c in comps
          if c["area"]["name"] == area and c.get("code")
     ]
     return sorted(out, key=lambda c: c["name"])

@app.get("/api/teams")
def teams(competition: str):
     data = api_get(f"/competitions/{competition}/teams")
     out = [
          {"id": t["id"], "name": label(t), "crest": t.get("crest") or ""}
          for t in data["teams"]
     ]
     return sorted(out, key=lambda t: t["name"])

@app.get("/api/matches")
def matches(team: int, limit: int=Query(10, ge=1, le=100)):
     today=datetime.now(timezone.utc).date()
     data = api_get(
          f"/teams/{team}/matches",
          status="FINISHED",
          dateFrom=str(today - timedelta(WINDOW_DAYS)),
          dateTo=str(today),
     )

     rows = []
     for m in reversed(data.get("matches", [])):
          ft = m["score"]["fullTime"]
          if ft.get("home") is None or ft.get("away") is None:
               continue
          rows.append(build_row(m, team))
          if len(rows) == limit:
               break
     return rows
import json
import os
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlencode
 
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
 
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
 
KEY = os.environ.get("API_FOOTBALL_KEY")
if not KEY:
    raise SystemExit("Brak API_FOOTBALL_KEY w .env")
 
API = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": KEY}
FRONTEND = BASE_DIR / "templates" / "app_v3.html"
DB = BASE_DIR / "cache.db"
 
# rozne dane starzeja sie w roznym tempie
TTL_STATIC = 30 * 24 * 3600      # kraje, ligi
TTL_TEAMS = 7 * 24 * 3600        # sklady lig
TTL_MATCHES = 3600               # wyniki
TTL_EVENTS = 30 * 24 * 3600      # zdarzenia zakonczonego meczu sie nie zmieniaja
 
app = FastAPI(title="Ostatnie mecze v3 - API-Football")
_quota = {"limit": None, "remaining": None}
 
# ---------------- cache na dysku ----------------
 
def _db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS cache (k TEXT PRIMARY KEY, v TEXT, ts REAL)")
    return conn
 
def cache_get(key, ttl):
    with _db() as conn:
        row = conn.execute("SELECT v, ts FROM cache WHERE k = ?", (key,)).fetchone()
    if row and time.time() - row[1] < ttl:
        return json.loads(row[0])
    return None
 
def cache_put(key, value):
    with _db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache (k, v, ts) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time()),
        )
 
# ---------------- API-Football ----------------
 
def api_get(path, ttl, **params):
    key = path + "?" + urlencode(sorted(params.items()))
 
    hit = cache_get(key, ttl)
    if hit is not None:
        return hit
 
    resp = requests.get(f"{API}{path}", headers=HEADERS, params=params, timeout=20)
 
    _quota["limit"] = resp.headers.get("x-ratelimit-requests-limit")
    _quota["remaining"] = resp.headers.get("x-ratelimit-requests-remaining")
    print(f"[api] {key}   pozostalo dzisiaj: {_quota['remaining']}/{_quota['limit']}")
 
    try:
        data = resp.json()
    except ValueError:
        raise HTTPException(502, f"API nie zwrocilo JSON-a (HTTP {resp.status_code})")
 
    # API-Football odpowiada 200 nawet przy bledzie — komunikat siedzi w polu "errors"
    errors = data.get("errors")
    if errors:
        if isinstance(errors, dict):
            msg = "; ".join(f"{k}: {v}" for k, v in errors.items())
        else:
            msg = str(errors)
        raise HTTPException(502, f"API-Football: {msg}")
 
    if data.get("message") and not data.get("response"):
        raise HTTPException(502, f"API-Football: {data['message']}")
 
    if resp.status_code != 200:
        raise HTTPException(502, f"Blad API (HTTP {resp.status_code})")
 
    out = data.get("response") or []
    cache_put(key, out)
    return out
 
# ---------------- przetwarzanie ----------------
def round_label(r):
    if not r:
        return ""
    if r.startswith("Regular Season - "):
        return "Kolejka " + r.split(" - ")[-1]
    elif r.startswith("League Stage - "):
        return "Faza ligowa #" + r.split(" - ")[-1]

    tr = {
        "Group Stage": "Faza grupowa",
        "Round of 16": "1/8 finalu",
        "Quarter-finals": "1/4 finalu",
        "Semi-finals": "1/2 finalu",
        "3rd Place Final": "Mecz o 3. miejsce",
        "Final": "Final",
    }
    for en, pl in tr.items():
        if r.startswith(en):
            return pl
    return r


def build_row(f, team_id):
    home, away = f["teams"]["home"], f["teams"]["away"]
    gh, ga = f["goals"].get("home"), f["goals"].get("away")
    is_home = home["id"] == team_id
 
    hw, aw = home.get("winner"), away.get("winner")
    if hw is None and aw is None:
        if gh is not None and ga is not None and gh != ga:
            result = "W" if ((gh > ga) == is_home) else "L"
        else:
            result = "D"
    else:
        result = "W" if (hw if is_home else aw) else "L"
 
    # karne dopisujemy do wyniku, bo "goals" pokazuje stan po 90 minutach
    pen = (f.get("score") or {}).get("penalty") or {}
    pen_txt = ""
    if pen.get("home") is not None and pen.get("away") is not None:
        pen_txt = f' (k. {pen["home"]}:{pen["away"]})'
 
    return {
        "fixture_id": f["fixture"]["id"],
        "date": f["fixture"]["date"][:10],
        "home": home["name"],
        "away": away["name"],
        "home_logo": home.get("logo") or "",
        "away_logo": away.get("logo") or "",
        "score": (f"{gh}:{ga}" if gh is not None else "-") + pen_txt,
        "competition": f["league"]["name"],
        "competition_logo": f["league"].get("logo") or "",
        "round": round_label(f["league"].get("round")),
        "result": result,
    }
 
# ---------------- endpointy ----------------
 
@app.get("/")
def index():
    if not FRONTEND.exists():
        raise HTTPException(500, f"Brak pliku frontendu: {FRONTEND}")
    return FileResponse(FRONTEND)
 
@app.get("/api/quota")
def quota():
    return _quota
 
@app.get("/api/countries")
def countries():
    data = api_get("/countries", TTL_STATIC) or []
    return [
        {"name": c["name"], "flag": c.get("flag") or ""}
        for c in data
        if isinstance(c, dict) and c.get("name")
    ]
 
@app.get("/api/leagues")
def leagues(country: str):
    data = api_get("/leagues", TTL_STATIC, country=country) or []
 
    out = []
    for item in data:
        lg = item["league"]
        seasons = item.get("seasons") or []
        years = sorted((s["year"] for s in seasons), reverse=True)
        if not years:
            continue
        current = next((s["year"] for s in seasons if s.get("current")), years[0])
 
        out.append({
            "id": lg["id"],
            "name": lg["name"],
            "type": lg.get("type") or "",
            "logo": lg.get("logo") or "",
            "season": current,
            "seasons": years,
        })
    return sorted(out, key=lambda x: (x["type"] != "League", x["id"]))
 
@app.get("/api/teams")
def teams(league: int, season: int):
    data = api_get("/teams", TTL_TEAMS, league=league, season=season) or []
    out = [
        {
            "id": t["team"]["id"],
            "name": t["team"]["name"],
            "logo": t["team"].get("logo") or "",
        }
        for t in data
    ]
    return sorted(out, key=lambda t: t["name"])
 
@app.get("/api/matches")
def matches(
    team: int,
    season: int,
    league: int | None = None,
    limit: int = Query(10, ge=1, le=50),
):
    params = {"team": team, "season": season}
    if league:
        params["league"] = league
 
    data = api_get("/fixtures", TTL_MATCHES, **params) or []
 
    rows = []
    for f in sorted(data, key=lambda f: f["fixture"]["date"], reverse=True):
        if f["goals"].get("home") is None or f["goals"].get("away") is None:
            continue
        rows.append(build_row(f, team))
        if len(rows) == limit:
            break
 
    return rows
 
@app.get("/api/events")
def events(fixture: int):
    data = api_get("/fixtures/events", TTL_EVENTS, fixture=fixture) or []
 
    out = []
    for e in data:
        typ = (e.get("type") or "").lower()
        if typ not in ("goal", "card", "subst"):
            continue
 
        t = e.get("time") or {}
        minute, extra = t.get("elapsed"), t.get("extra")
        if minute is None:
            label = "?"
        elif extra:
            label = f"{minute}+{extra}"
        else:
            label = str(minute)
 
        out.append({
            "minute": label,
            "sort": (minute or 0) + (extra or 0) / 100,
            "type": typ,
            "detail": e.get("detail") or "",
            "team": (e.get("team") or {}).get("name") or "",
            "player": (e.get("player") or {}).get("name") or "?",
            "assist": (e.get("assist") or {}).get("name") or "",
        })
 
    return sorted(out, key=lambda x: x["sort"])

@app.get("/api/standings")
def standings(league: int, season: int):
    data = api_get("/standings", TTL_MATCHES, league=league, season=season) or []
    if not data:
        return []
 
    groups = (data[0].get("league") or {}).get("standings") or []
 
    # grupujemy po polu "group" z wiersza, nie po zagniezdzeniu z API
    buckets = {}
    for g in groups:
        for t in g:
            st = t.get("all") or {}
            goals = st.get("goals") or {}
            team = t.get("team") or {}
 
            row = {
                "rank": t.get("rank"),
                "team_id": team.get("id"),
                "team": team.get("name") or "?",
                "logo": team.get("logo") or "",
                "played": st.get("played"),
                "win": st.get("win"),
                "draw": st.get("draw"),
                "lose": st.get("lose"),
                "gf": goals.get("for"),
                "ga": goals.get("against"),
                "diff": t.get("goalsDiff"),
                "points": t.get("points"),
                "form": t.get("form") or "",
            }
            buckets.setdefault(t.get("group") or "", []).append(row)
 
    return [
        {"name": name, "rows": sorted(rows, key=lambda r: r["rank"] or 999)}
        for name, rows in buckets.items()
    ]
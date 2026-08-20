import requests
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader
import argparse


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN")
if not TOKEN:
    raise SystemExit("Brak podanego FOOTBALL_DATA_TOKEN w .env")

parser = argparse.ArgumentParser(description="Generuje strone z ostatnimi meczami.")
parser.add_argument("--team-id", type=int, default=66, help="ID druzyny (domyslnie 66 = Man Utd)")
parser.add_argument("--limit", type=int, default=10, help="ile meczow pokazac")
parser.add_argument("--output", default="index.html", help="nazwa pliku wynikowego")
parser.add_argument("--list-teams", metavar="KOD", help="wypisz druzyny z danej ligi (np. PL) i zakoncz.")
parser.add_argument("--list-competitions", action="store_true", help="wypisz dostepne rozgrywki wraz z kodami i zakoncz")
parser.add_argument("--season-from", default="2025-08-01", help="poczatek zakresu dat (YYYY-MM-DD)")
parser.add_argument("--season-to", default="2026-06-30", help="koniec zakresu dat (YYYY-MM-DD)")
args = parser.parse_args()

TEAM_ID=args.team_id
MATCH_LIMIT = args.limit

def fetch_matches(limit=10):
    resp = requests.get(f"https://api.football-data.org/v4/teams/{TEAM_ID}/matches", 
                     headers={"X-Auth-Token": TOKEN},
                     params={"status": "FINISHED","dateFrom": args.season_from, "dateTo": args.season_to}, 
                     timeout=10
                     )
    data = resp.json()
    if resp.status_code != 200 or "errorCode" in data:
        msg=data.get("message") or resp.text[:200]
        raise SystemExit(f"API odrzucilo zapytanie (HTTP {resp.status_code}): {msg}")

    matches = data.get("matches")
    if matches is None:
        raise SystemExit("Odpowiedz nie zawiera 'matches'. Klucze: " + ", ".join(data))
    if not matches:
        print(f"Uwaga: brak meczow w zakresie {args.season_from} ... {args.season_to}")

    return matches[-limit:]

def list_competitions():
    resp = requests.get(
        "https://api.football-data.org/v4/competitions",
        headers={"X-Auth-Token": TOKEN},
        timeout=10,
    )
    resp.raise_for_status()
    comps = resp.json()["competitions"]
    print(f'{"KOD":<6} {"NAZWA":<34} {"KRAJ":<18} PLAN')
    for c in sorted(comps, key=lambda c: c["area"]["name"]):
        code = c.get("code") or "-"
        print(f'{code:<6} {c["name"]:<34} {c["area"]["name"]:<18} {c.get("plan", "")}')


def list_teams(code):
    resp = requests.get(
        f"https://api.football-data.org/v4/competitions/{code}/teams",
        headers={"X-Auth-Token": TOKEN},
        timeout=10,
    )
    resp.raise_for_status()
    for t in sorted(resp.json()["teams"], key=label):
        print(f'{t["id"]:>5} {label(t):<26} {t.get("tla") or ""}')

def label(team):
    return team.get("shortName") or team.get("name") or team.get("tla") or "?"

def team_name_from(matches, team_id):
    resp = requests.get(
        f"https://api.football-data.org/v4/teams/{team_id}",
        headers={"X-Auth-Token": TOKEN},
        timeout = 10
    )
    if resp.status_code != 200:
        print(f"Nie udalo sie pbrac nazwy (HTTP {resp.status_code}): {resp.text[:200]}")
        return f"Druzyna {team_id}"
    data = resp.json()
    return data.get("name") or label(data)

def build_rows(matches, team_id):
    rows = []
    for m in reversed(matches):
        ft = m["score"]["fullTime"]

        if ft.get("home") is None or ft.get("away") is None:
            continue

        is_home = m["homeTeam"]["id"] == TEAM_ID
        winner = m["score"].get("winner")

        if winner == "DRAW":
            result = "D"
        elif winner in ("HOME_TEAM", "AWAY_TEAM"):
            result = "W" if (winner == "HOME_TEAM") == is_home else "L"
        else:
            scored, conceded = (ft["home"], ft["away"]) if is_home else (ft["away"], ft["home"])
            result = "W" if scored > conceded else "L" if scored < conceded else "D"

        ref = next(
            (r["name"] for r in m.get("referees", []) if r.get("type") == "REFEREE"),
            "-",
        )

        rows.append({
            "date": m["utcDate"][:10],
            "home": m["homeTeam"]["shortName"],
            "away": m["awayTeam"]["shortName"],
            "home_crest": m["homeTeam"].get("crest") or "",
            "away_crest": m["awayTeam"].get("crest") or "",
            "score": f'{ft["home"]}:{ft["away"]}',
            "competition": m["competition"]["name"],
            "referee": ref,
            "result": result
        })
    return rows

def render(rows, team):
    env = Environment(
        loader=FileSystemLoader(BASE_DIR / "templates"),
        autoescape=True,
    )
    html = env.get_template("index.html").render(
        team=team,
        rows=rows,
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )
    out = BASE_DIR / args.output
    out.write_text(html, encoding="utf-8")
    print(f"Zapisano: {out} {len(rows)} meczow.")

if args.list_teams:
    list_teams(args.list_teams)
    raise SystemExit(0)

if args.list_competitions:
    list_competitions()
    raise SystemExit(0)

if args.list_teams:
    for code in args.list_teams.split(","):
        list_teams(code.strip())
        raise SystemExit(0)

matches = fetch_matches()
render(build_rows(matches, TEAM_ID), team_name_from(matches, TEAM_ID))
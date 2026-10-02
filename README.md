# Wyniki piłkarskie - trzy podejścia
 
Projekt do nauki: pobieranie wyników z publicznych API i pokazywanie ich w przeglądarce.
Trzy wersje, trzy różne architektury.
 
| | Uruchomienie | Wybór | Dane | Hosting |
|---|---|---|---|---|
| **v1** `meczeprojekt_v1.1.py` | terminal, flagi | `--team-id` | football-data.org | GitHub Pages ✓ |
| **v2** `meczeprojekt_v2.py` | `uvicorn` | kraj → liga → drużyna | football-data.org | lokalnie |
| **v3** `meczeprojekt_v3.py` | `uvicorn` | kraj → liga → sezon → drużyna | API-Football | lokalnie |
 
**v3 dodatkowo:** tabela ligowa ze strefami pucharowymi, gole, kartki i statystyki
po kliknięciu w mecz, skróty do popularnych lig, cache na dysku, pamiętanie ostatniego wyboru.
 
## Start
 
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
 
W `.env` wklej klucze:
 
```
FOOTBALL_DATA_TOKEN=...      # v1, v2 - football-data.org/client/register
API_FOOTBALL_KEY=...         # v3 - dashboard.api-football.com/register
```
 
Oba plany są darmowe. Każda wersja używa tylko swojego klucza.
 
---
 
## v1 - generator statycznej strony
 
```bash
python meczeprojekt_v1.1.py
```
 
Tworzy `index.html` - samodzielny plik, otwierasz dwuklikiem albo publikujesz.
 
```bash
python meczeprojekt_v1.1.py --list-competitions    # kody lig
python meczeprojekt_v1.1.py --list-teams PL        # id drużyn
python meczeprojekt_v1.1.py --team-id 64 --limit 5
```
 
Pełna lista opcji: `--help`
 
---
 
## v2 - serwer, dane bieżące
 
```bash
uvicorn meczeprojekt_v2:app --reload
```
 
→ http://127.0.0.1:8000
 
Kaskadowe listy, dane pobierane na żądanie. Cache w pamięci, limit 10 zapytań/min.
 
---
 
## v3 - serwer, szczegółowe dane
 
```bash
uvicorn meczeprojekt_v3:app --reload
```
 
→ http://127.0.0.1:8000 · dokumentacja API: `/docs`
 
### Co potrafi
 
- **Wybór** kraj → rozgrywki (osobno ligi i puchary) → sezon → drużyna oraz liczba meczów (5–50)
- **Skróty** do popularnych lig: Premier League, La Liga, Bundesliga, Serie A, Ligue 1,
  Ekstraklasa, Liga Mistrzów. Ostatni wybór zapamiętuje przeglądarka, przycisk „Wyczyść” go kasuje
- **Lista meczów** z logami drużyn i rozgrywek, kolejką lub fazą turnieju, wynikiem
  (razem z karnymi) i plakietką W/D/L
- **Szczegóły meczu** po kliknięciu:
  - gole i kartki z minutami, asystami, karnymi i samobójami
  - statystyki z paskami porównania: posiadanie piłki, strzały, xG, rzuty rożne,
    faule, spalone, obrony bramkarza, podania
- **Tabela ligowa** pod meczami, wczytywana zaraz po wyborze sezonu:
  - kolorowe strefy (Liga Mistrzów, Liga Europy, Liga Konferencji, awans, spadek) z legendą
  - forma z 5 ostatnich meczów
  - podświetlona wybrana drużyna
  - w pucharach z fazą grupową osobna tabela dla każdej grupy
- **Licznik** pozostałych zapytań na dziś
 
### Endpointy
 
| Endpoint | Zwraca |
|---|---|
| `/api/countries` | kraje |
| `/api/leagues?country=` | ligi i puchary kraju z listą sezonów |
| `/api/teams?league=&season=` | drużyny w lidze i sezonie |
| `/api/matches?team=&season=&league=&limit=` | ostatnie zakończone mecze (limit 1–50) |
| `/api/events?fixture=` | gole, kartki i zmiany w meczu |
| `/api/stats?fixture=` | statystyki meczu |
| `/api/standings?league=&season=` | tabela ligowa |
| `/api/quota` | pozostałe zapytania na dziś |
 
### Cache
 
Odpowiedzi API-Football trafiają do `cache.db` (SQLite) i przeżywają restart serwera.
Przy dobowym limicie zapytań to konieczność. Czas ważności zależy od rodzaju danych:
 
| Dane | Ważność |
|---|---|
| kraje, ligi | 30 dni |
| drużyny | 7 dni |
| mecze, tabela | 1 godzina |
| zdarzenia i statystyki meczu | 30 dni |
 
Kasowanie: `rm cache.db`.
 
### Ograniczenia darmowego planu API-Football
 
- 100 zapytań na dobę (licznik widoczny na stronie)
- sezony 2022–2024, bez bieżącego
- brak parametru `last`, dlatego pobierany jest cały sezon i filtrowany lokalnie
- statystyki i strefy w tabeli są tylko tam, gdzie API je zbiera. W mniejszych ligach
  może ich brakować, a xG jest głównie w topowych ligach
 
---
 
## Struktura
 
```
├── meczeprojekt_v0.1.py    # szkice
├── meczeprojekt_v1.0.py
├── meczeprojekt_v1.1.py    # v1
├── meczeprojekt_v2.py      # v2
├── meczeprojekt_v3.py      # v3
├── templates/
│   ├── index.html          # szablon Jinja2 (v1)
│   ├── app.html            # frontend v2
│   └── app_v3.html         # frontend v3
├── index.html              # wynik v1
├── requirements.txt
├── .env.example            # wzór pliku z kluczami
└── .env                    # klucze, ignorowany przez Gita
```
 
## Źródła danych
 
[football-data.org](https://www.football-data.org/) · [API-Football](https://www.api-football.com/)
 

# Wyniki piłkarskie - trzy podejścia
 
Projekt do nauki: pobieranie wyników z publicznych API i pokazywanie ich w przeglądarce.
Trzy wersje, trzy różne architektury.
 
| | Uruchomienie | Wybór | Dane | Hosting |
|---|---|---|---|---|
| **v1** `meczeprojekt_v1.1.py` | terminal, flagi | `--team-id` | football-data.org | GitHub Pages ✓ |
| **v2** `meczeprojekt_v2.py` | `uvicorn` | kraj → liga → drużyna | football-data.org | lokalnie |
| **v3** `meczeprojekt_v3.py` | `uvicorn` | kraj → liga → sezon → drużyna | API-Football | lokalnie |
 
**v3 dodatkowo:** gole i kartki po kliknięciu w mecz, skróty do popularnych lig,
cache na dysku, pamiętanie ostatniego wyboru.
 
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
 
Kliknięcie w mecz rozwija listę goli i kartek z minutami i asystami.
 
**Ograniczenia darmowego planu API-Football:**
- 100 zapytań na dobę (licznik widoczny na stronie)
- sezony 2022–2024, bez bieżącego
- brak parametru `last` - dlatego pobierany jest cały sezon i filtrowany lokalnie
 
Cache siedzi w `cache.db` i przeżywa restart serwera - przy dobowym limicie to konieczność.
Kasowanie: `rm cache.db`.
 
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
└── .env                    # klucze, ignorowany przez Gita
```

## Źródła danych
 
[football-data.org](https://www.football-data.org/) · [API-Football](https://www.api-football.com/)

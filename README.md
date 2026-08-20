# Ostatnie mecze — wyniki z football-data.org
 
Dwa sposoby na to samo: przeglądanie ostatnich wyników drużyny.
Wspólny token, wspólne środowisko, osobne punkty wejścia.
 
| | `meczeprojekt_v1.1.py` | `meczeprojekt_v2.py` |
|---|---|---|
| Sposób użycia | terminal, flagi CLI | przeglądarka, listy do wyboru |
| Wynik | statyczny plik `index.html` | dane pobierane na żądanie |
| Wybór drużyny | argument `--team-id` | kraj → liga → drużyna |
| Wymaga serwera | nie | tak (`uvicorn`) |
| GitHub Pages | tak | nie |
 
## Wymagania
 
- Python 3.9+
- darmowy klucz API z [football-data.org](https://www.football-data.org/client/register)
 
## Instalacja
 
```bash
git clone git@github.com:slizoon1337/meczeprojekt.git
cd meczeprojekt
 
python3 -m venv .venv
source .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
 
pip install -r requirements.txt
```
 
## Konfiguracja
 
```bash
cp .env.example .env
```
 
W `.env` wklej token:
 
```
FOOTBALL_DATA_TOKEN=twoj_token
```
 
Plik jest ignorowany przez Gita — token nie trafia do repozytorium.
Obie wersje czytają go z tego samego miejsca.
 
---
 
# Wersja 1 — generator statycznej strony
 
Pobiera mecze jednej drużyny i zapisuje gotowy `index.html`: data, drużyny z herbami,
wynik, rozgrywki, sędzia główny, oznaczenie W/D/L.
 
```bash
python meczeprojekt_v1.1.py
```
 
Plik powstaje w katalogu projektu — otwierasz go dwuklikiem albo publikujesz na Pages.
 
## Wybór drużyny
 
```bash
python meczeprojekt_v1.1.py --team-id 64                     # Liverpool
python meczeprojekt_v1.1.py --team-id 57 --limit 5           # Arsenal, 5 meczów
python meczeprojekt_v1.1.py --team-id 65 --output city.html  # do osobnego pliku
```
 
## Podpowiedzi identyfikatorów
 
Nie trzeba pamiętać kodów ani ID — program je wypisze:
 
```bash
python meczeprojekt_v1.1.py --list-competitions       # kody rozgrywek
python meczeprojekt_v1.1.py --list-teams PL           # drużyny wybranej ligi
python meczeprojekt_v1.1.py --list-teams PL,PD,BL1    # kilka lig naraz
```
 
```
   57  Arsenal                ARS
   58  Aston Villa            AVL
   61  Chelsea                CHE
   64  Liverpool              LIV
   66  Man United             MUN
```
 
## Opcje
 
| Flaga | Domyślnie | Opis |
|---|---|---|
| `--team-id` | `66` | identyfikator drużyny |
| `--limit` | `10` | ile ostatnich meczów |
| `--output` | `index.html` | nazwa pliku wynikowego |
| `--season-from` | `2025-08-01` | początek zakresu dat |
| `--season-to` | `2026-06-30` | koniec zakresu dat |
| `--list-teams KODY` | — | wypisz drużyny lig (po przecinku) i zakończ |
| `--list-competitions` | — | wypisz dostępne rozgrywki i zakończ |
 
Pełna ściąga: `python meczeprojekt_v1.1.py --help`
 
Przy turniejach reprezentacji domyślny zakres dat trzeba poszerzyć — obejmuje sezon klubowy:
 
```bash
python meczeprojekt_v1.1.py --list-teams WC
python meczeprojekt_v1.1.py --team-id 759 --season-from 2026-06-01 --season-to 2026-07-31
```
---
 
# Wersja 2 — serwer z wyborem w przeglądarce
 
Kaskadowe listy: kraj → rozgrywki → drużyna. Do tego wybór liczby meczów (5/10/20/50).
Tabela odświeża się po każdej zmianie.
 
```bash
uvicorn meczeprojekt_v2:app --reload
```
 
Otwórz http://127.0.0.1:8000 · zatrzymanie: Ctrl+C
 
## Endpointy
 
Frontend korzysta z własnego API, które pośredniczy w rozmowie z football-data.org:
 
| Adres | Zwraca |
|---|---|
| `/` | stronę z listami |
| `/api/areas` | kraje mające dostępne rozgrywki |
| `/api/competitions?area=England` | ligi w danym kraju |
| `/api/teams?competition=PL` | drużyny w danej lidze |
| `/api/matches?team=66&limit=10` | ostatnie mecze drużyny (`limit` 1–100) |
| `/docs` | dokumentację, generowaną automatycznie |
 
## Jak to działa
 
- **Token zostaje na serwerze.** Przeglądarka woła tylko `/api/*`, nagłówek
  `X-Auth-Token` dokłada Python. Bezpośrednie odpytywanie football-data.org
  z przeglądarki wymagałoby ujawnienia klucza i jest blokowane przez CORS.
- **Cache w pamięci na godzinę.** Bez niego przeklikiwanie list wyczerpałoby
  limit 10 zapytań na minutę w kilka sekund. Lista rozgrywek obsługuje dwa
  pierwsze pola wyboru, więc kosztuje jedno zapytanie.
- **Okno 740 dni.** Mecze pobierane są z ostatnich 740 dni licząc od dziś
  (API dopuszcza maksymalnie 750). Jeśli w tym okresie jest mniej meczów,
  niż wybrałeś, strona pokaże wszystkie dostępne wraz z wyjaśnieniem.
 
Dlaczego to nie działa na GitHub Pages: hosting statyczny nie uruchamia procesów.
 
---
 
## Struktura projektu
 
```
meczeprojekt/
├── .env                    # token (ignorowany przez Gita)
├── .env.example            # szablon konfiguracji
├── .gitignore
├── README.md
├── requirements.txt
├── meczeprojektv_1.1.py         # v1 — generator statyczny
├── meczeprojekt_v2.py      # v2 — serwer FastAPI
├── templates/
│   ├── index.html          # szablon Jinja2 dla v1
│   └── app.html            # frontend v2
└── index.html              # wynik v1 — publikowany na Pages
```
 
## Ograniczenia darmowego planu
 
- **10 zapytań na minutę** — v2 buforuje odpowiedzi, v1 robi przerwy między zapytaniami
- **Zakres rozgrywek** — tylko oznaczone jako `TIER_ONE` (sprawdzisz przez `--list-competitions`)
- **Sędziowie** — pole bywa puste, wyświetla się wtedy `-`
- **Strzelcy bramek** — zdarzenia meczowe nie są dostępne w tym planie
 
## Źródło danych
 
[football-data.org](https://www.football-data.org/)
 


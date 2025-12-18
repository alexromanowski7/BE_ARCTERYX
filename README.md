# Sklep Arc'teryx

Projekt na podstawie sklepu: https://arcteryx.com
Dane produktów i kategorii są scrapowane ze sklepu źródłowego.

## Technologie

- PrestaShop 1.7.8.x
- Docker + docker-compose
- Python (scraper, testy Selenium)

## Struktura repozytorium

- `shop/` – kod źródłowy sklepu (PrestaShop)
- `tests/` – testy automatyczne UI (Selenium)
- `scraper/` – narzędzie do scrapowania sklepu źródłowego
- `scraper_output/` – rezultaty scrapowania (CSV/JSON, obrazy)
- `deploy/` – pliki konfiguracyjne i skrypty instalacyjne/wdrożeniowe

## Uruchomienie (Docker)

Instrukcja krok po kroku
Pobranie repozytorium:

git clone <adres-twojego-repozytorium>
cd <nazwa-katalogu-projektu>
Uruchomienie kontenerów: W głównym katalogu projektu uruchom komendę:

docker-compose up -d

Dostęp do sklepu: Po poprawnym uruchomieniu kontenerów, sklep będzie dostępny pod adresem:

Sklep: https://localhost

Panel Administratora: https://localhost/admin697jmd6ap

Dane logowania:

E-mail: admin@sklep.pl

Hasło: password123

Zatrzymanie środowiska: Aby zatrzymać i usunąć kontenery:

docker-compose down

## Zespół

- Alexandre Romanowski-Baouche 197787
- Paweł Łaszkiewicz 198220
- Wiktor Banach 197801

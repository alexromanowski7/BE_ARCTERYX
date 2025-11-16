# Sklep Arc'teryx

Projekt na podstawie sklepu: https://arcteryx.com
Dane produktów i kategorii są scrapowane ze sklepu źródłowego.

## Technologie

- PrestaShop 1.7.8.x
- PHP, MySQL/MariaDB
- Docker + docker-compose / Ubuntu VM
- Python (scraper, testy Selenium)
- Selenium WebDriver

## Struktura repozytorium

- `shop/` – kod źródłowy sklepu (PrestaShop)
- `tests/` – testy automatyczne UI (Selenium)
- `scraper/` – narzędzie do scrapowania sklepu źródłowego
- `scraper_output/` – rezultaty scrapowania (CSV/JSON, obrazy)
- `deploy/` – pliki konfiguracyjne i skrypty instalacyjne/wdrożeniowe

## Uruchomienie (Docker)

#TODO

## Zespół

- Alexandre Romanowski-Baouche 197787
- Paweł Łaszkiewicz 198220
- Wiktor Banach 197801

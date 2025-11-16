# scraper/Scraper.py
import os
import json
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import HEADERS, SITEMAP_INDEX_URL, VALID_ROOT

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def fetch_html(url: str) -> str:
    resp = SESSION.get(url, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def discover_sitemaps():
    """
    Z głównego sitemap.xml wyciągnij listę pod-sitemap.
    Obsługuje zarówno sitemapindex, jak i pojedynczy urlset.
    """
    xml = fetch_html(SITEMAP_INDEX_URL)
    soup = BeautifulSoup(xml, "xml")

    sitemaps = set()

    # Jeżeli to indeks (<sitemapindex>), bierzemy <sitemap><loc>...</loc></sitemap>
    for sm in soup.find_all("sitemap"):
        loc = sm.find("loc")
        if not loc:
            continue
        url = loc.get_text(strip=True)
        sitemaps.add(url)

    # Jeżeli nie było <sitemap>, traktujemy ten plik jako zwykły urlset
    if not sitemaps:
        sitemaps.add(SITEMAP_INDEX_URL)

    print(f"[DEBUG] znaleziono {len(sitemaps)} sitemap w indeksie")
    return sorted(sitemaps)


def collect_product_urls():
    """
    Zbierz URL-e produktów z wszystkich sitemap.
    Filtrujemy po fragmentach '/us/en/shop/'.
    """
    product_urls = set()

    sitemap_urls = discover_sitemaps()
    for sm_url in sitemap_urls:
        try:
            print(f"[DEBUG] pobieram sitemap: {sm_url}")
            xml = fetch_html(sm_url)
        except Exception as e:
            print(f"[!] Błąd pobierania sitemap {sm_url}: {e}")
            continue

        soup = BeautifulSoup(xml, "xml")

        # klasyczny format: <urlset><url><loc>...</loc></url></urlset>
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if VALID_ROOT in url:
                product_urls.add(url)

    urls = sorted(product_urls)
    print(f"Zebrano {len(urls)} URL-i produktów z sitemap")
    return urls


def extract_image_urls(soup: BeautifulSoup, base_url: str):
    """Weź max 2 duże zdjęcia; odfiltruj miniatury po nazwie."""
    urls = []
    for img in soup.select("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        lower = src.lower()
        if "thumb" in lower or "icon" in lower or "logo" in lower:
            continue
        full = urljoin(base_url, src)
        urls.append(full)
    return urls[:2]


def guess_text(soup: BeautifulSoup, selectors):
    for css in selectors:
        el = soup.select_one(css)
        if el and el.get_text(strip=True):
            return el.get_text(" ", strip=True)
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(" ", strip=True)
    p = soup.find("p")
    if p and p.get_text(strip=True):
        return p.get_text(" ", strip=True)
    return ""


def guess_price(soup: BeautifulSoup):
    for css in ["[class*='Price']", "span[aria-label*='Price']"]:
        el = soup.select_one(css)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    for el in soup.find_all(string=True):
        text = el.strip()
        if "$" in text:
            return text
    return ""


def guess_attributes(soup: BeautifulSoup):
    attrs = {"color": "", "material": ""}

    text = soup.get_text(" ", strip=True).lower()

    for color in ["black", "blue", "red", "green", "grey", "gray", "yellow", "orange", "white"]:
        if color in text and not attrs["color"]:
            attrs["color"] = color.capitalize()

    for material in ["gore-tex", "nylon", "polyester", "down", "cotton", "merino"]:
        if material in text and not attrs["material"]:
            attrs["material"] = material.upper() if "gore-tex" in material else material.capitalize()

    return attrs


def classify_product(url: str):
    """
    Kategoria główna: Clothing / Footwear / Accessories
    Podkategoria: Men / Women (albo Other).
    """
    path = urlparse(url).path.lower()

    # podkategoria = płeć
    if "/mens/" in path:
        subcategory = "Men"
    elif "/womens/" in path:
        subcategory = "Women"
    else:
        subcategory = "Other"

    # kategoria = typ produktu
    if "shoe" in path or "boot" in path or "footwear" in path:
        category = "Footwear"
    elif "hat" in path or "belt" in path or "glove" in path or "accessor" in path:
        category = "Accessories"
    else:
        category = "Clothing"

    return category, subcategory


def slugify(text: str) -> str:
    return (
        text.lower()
        .strip()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("'", "")
        .replace('"', "")
    )


def parse_product_page(url: str, category: str, subcategory: str):
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    name = guess_text(soup, ["h1[class*='Product']", "h1[data-testid*='product']"])
    description = guess_text(
        soup,
        [
            "div[class*='Description']",
            "section[class*='Description']",
            "div[data-testid*='description']",
        ],
    )
    price_text = guess_price(soup)
    attributes = guess_attributes(soup)
    image_urls = extract_image_urls(soup, url)

    product_id = slugify(name) or slugify(urlparse(url).path) or str(int(time.time() * 1000))
    image_paths = download_images(image_urls, product_id)

    return {
        "category": category,
        "subcategory": subcategory,
        "name": name,
        "description": description,
        "price": price_text,
        "attributes": attributes,
        "images": image_paths,
        "source_url": url,
    }


def download_images(image_urls, product_id: str):
    images_dir = os.path.join("scraper_output", "images")
    os.makedirs(images_dir, exist_ok=True)

    saved = []

    for i, img_url in enumerate(image_urls):
        try:
            resp = SESSION.get(img_url, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"[!] Błąd pobierania obrazka {img_url}: {e}")
            continue

        ext = ".jpg"
        lower = img_url.lower()
        if ".png" in lower:
            ext = ".png"
        elif ".jpeg" in lower:
            ext = ".jpeg"

        filename = f"{product_id}-{i+1}{ext}"
        rel_path = os.path.join("images", filename)
        abs_path = os.path.join("scraper_output", rel_path)

        with open(abs_path, "wb") as f:
            f.write(resp.content)

        saved.append(rel_path)
        time.sleep(0.05)

    return saved


def main():
    os.makedirs("scraper_output", exist_ok=True)

    product_urls = collect_product_urls()
    all_products = []

    for url in product_urls:
        category, subcategory = classify_product(url)
        if subcategory not in ("Men", "Women"):
            continue

        print(f"Scrapuję: {category} / {subcategory} -> {url}")
        try:
            product = parse_product_page(url, category, subcategory)
            if len(product["images"]) < 2:
                print(f"  [!] Pomijam {product['name']} – mniej niż 2 duże zdjęcia")
                continue
            all_products.append(product)
        except Exception as e:
            print(f"  [!] Błąd przy {url}: {e}")

    out_path = os.path.join("scraper_output", "data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    print(f"Zapisano {len(all_products)} produktów do {out_path}")


if __name__ == "__main__":
    main()

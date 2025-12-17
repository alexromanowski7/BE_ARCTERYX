import os
import json
import csv
import re
import random
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

try:
    from config import HEADERS, SITEMAP_INDEX_URL, VALID_ROOT
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from config import HEADERS, SITEMAP_INDEX_URL, VALID_ROOT

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

def fetch_html(url: str) -> str:
    try:
        resp = SESSION.get(url, timeout=20)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except Exception as e:
        print(f"[!] Błąd pobierania {url}: {e}")
        return ""

def discover_sitemaps():
    xml = fetch_html(SITEMAP_INDEX_URL)
    if not xml: return [SITEMAP_INDEX_URL]
    soup = BeautifulSoup(xml, "html.parser")
    sitemaps = set()
    for sm in soup.find_all("sitemap"):
        loc = sm.find("loc")
        if loc: sitemaps.add(loc.get_text(strip=True))
    if not sitemaps: sitemaps.add(SITEMAP_INDEX_URL)
    return sorted(sitemaps)

def collect_product_urls():
    product_urls = set()
    sitemap_urls = discover_sitemaps()
    for sm_url in sitemap_urls:
        print(f"[DEBUG] pobieram sitemap: {sm_url}")
        xml = fetch_html(sm_url)
        if not xml: continue
        soup = BeautifulSoup(xml, "html.parser")
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if VALID_ROOT in url: product_urls.add(url)
    return sorted(product_urls)

def extract_image_urls(soup: BeautifulSoup, base_url: str):
    urls = []
    
    meta_img = soup.find("meta", property="og:image")
    if meta_img and meta_img.get("content"):
        urls.append(urljoin(base_url, meta_img["content"]))

    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            if not script.string: continue
            data = json.loads(script.string)
            if isinstance(data, dict): data = [data]
            for item in data:
                if item.get('@type') == 'Product' and 'image' in item:
                    img_data = item['image']
                    if isinstance(img_data, list): 
                        urls.extend(img_data)
                    elif isinstance(img_data, str): 
                        urls.append(img_data)
        except: continue
        
    # 3. Skanuj tagi <img> szukając srcset (dla wysokiej rozdzielczości)
    for img in soup.select("img"):
        src = None
        
        srcset = img.get("srcset") or img.get("data-srcset")
        if srcset:
            try:
                candidates = srcset.split(",")
                best_candidate = candidates[-1].strip().split(" ")[0]
                if best_candidate:
                    src = best_candidate
            except:
                pass
        
        if not src:
            src = img.get("src") or img.get("data-src")
            
        if not src: continue
        
        src_lower = src.lower()
        if "base64" in src_lower: continue
        if any(x in src_lower for x in ["icon", "logo", "svg", "avatar", "thumb", "swatch"]): continue
        
        full_url = urljoin(base_url, src)
        urls.append(full_url)

    seen = set()
    clean_urls = []
    
    for x in urls:
        if x not in seen:
            clean_urls.append(x)
            seen.add(x)
    
    return clean_urls[:2]

def guess_text(soup: BeautifulSoup, selectors):
    for css in selectors:
        el = soup.select_one(css)
        if el and el.get_text(strip=True): return el.get_text(" ", strip=True)
    h1 = soup.find("h1")
    return h1.get_text(" ", strip=True) if h1 else ""

def guess_price(soup: BeautifulSoup):
    raw_price = ""
    for css in ["[class*='Price']", "span[aria-label*='Price']"]:
        el = soup.select_one(css)
        if el and el.get_text(strip=True):
            raw_price = el.get_text(strip=True)
            break
    if not raw_price:
        for el in soup.find_all(string=True):
            if "$" in el and len(el) < 20:
                raw_price = el
                break
    if raw_price:
        clean = re.sub(r'[^\d.]', '', raw_price)
        try:
            # Mnożenie ceny razy 4
            price_val = float(clean) * 4
            return str(int(price_val))
        except: return ""
    return ""

def guess_attributes(soup: BeautifulSoup):
    attrs = {"color": "", "material": ""}
    text = soup.get_text(" ", strip=True).lower()
    for c in ["black", "blue", "red", "green", "grey", "gray", "yellow", "orange", "white"]:
        if c in text and not attrs["color"]: attrs["color"] = c.capitalize()
    for m in ["gore-tex", "nylon", "polyester", "down", "cotton", "merino"]:
        if m in text and not attrs["material"]: attrs["material"] = m.upper() if "gore-tex" in m else m.capitalize()
    return attrs

def classify_product(url: str):
    path = urlparse(url).path.lower()
    
    if "/womens/" in path or "-womens" in path or "/women/" in path:
        subcategory = "Women"
    elif "/mens/" in path or "-mens" in path or "/men/" in path:
        subcategory = "Men"
    else:
        subcategory = "Unisex"

    clothing_keywords = [
        "jacket", "coat", "parka", "vest", "anorak", "shell", "blazer",
        "pant", "short", "legging", "tights", "bottom", "knickers", "bib",
        "hoody", "shirt", "tee", "top", "polo", "pullover", "sweater", 
        "cardigan", "fleece", "dress", "skirt", "bra"
    ]
    accessories_keywords = [
        "backpack", "pack", "bag", "duffle", "tote", "waist",
        "hat", "cap", "beanie", "toque", "balaclava", "neck-gaiter", "headband",
        "glove", "mitten", "belt", "suspender", "sock", "harness", "chalk", "bucket"
    ]
    footwear_keywords = ["shoe", "boot", "footwear", "aerios", "konseal", "vertex", "kragg", "sylan", "norvan"]

    if any(x in path for x in clothing_keywords):
        category = "Clothing"
    elif any(x in path for x in accessories_keywords):
        category = "Accessories"
    elif any(x in path for x in footwear_keywords):
        category = "Footwear"
    else:
        category = "Clothing"

    return category, subcategory

def extract_description(soup: BeautifulSoup):
    description = ""

    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            if not script.string: continue
            data = json.loads(script.string)
            if isinstance(data, dict): data = [data]
            for item in data:
                if item.get('@type') == 'Product' and 'description' in item:
                    description = item['description']
                    if description:
                        return BeautifulSoup(description, "html.parser").get_text(" ", strip=True)
        except: continue

    meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        return meta_desc["content"].strip()


    possible_selectors = [
        "div[itemprop='description']",
        ".product-description",
        "#product-description",
        "div[class*='description'] p",
        "section[class*='Description']"
    ]
    
    for selector in possible_selectors:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 20: # Ignoruj bardzo krótkie teksty
            return el.get_text(" ", strip=True)

    return "Brak opisu"


def parse_product_page(url: str, category: str, subcategory: str):
    html = fetch_html(url)
    if not html: raise Exception("Pusta odpowiedź HTML")
    soup = BeautifulSoup(html, "html.parser")
    
    clean_description = extract_description(soup)

    return {
        "category": category,
        "subcategory": subcategory,
        "name": guess_text(soup, ["h1[class*='Product']", "h1[data-testid*='product']", "h1"]), # Dodano fallback do samego h1
        "description": clean_description,
        "price": guess_price(soup),
        "attributes": guess_attributes(soup),
        "images": extract_image_urls(soup, url),
        "source_url": url,
    }

def parse_product_page(url: str, category: str, subcategory: str):
    html = fetch_html(url)
    if not html: raise Exception("Pusta odpowiedź HTML")
    soup = BeautifulSoup(html, "html.parser")
    
    return {
        "category": category,
        "subcategory": subcategory,
        "name": guess_text(soup, ["h1[class*='Product']", "h1[data-testid*='product']"]),
        "description": guess_text(soup, ["div[class*='Description']", "section[class*='Description']"]),
        "price": guess_price(soup),
        "attributes": guess_attributes(soup),
        "images": extract_image_urls(soup, url),
        "source_url": url,
    }

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    project_root = os.path.dirname(script_dir)
    
    output_dir = os.path.join(project_root, "scraper_output")
    
    os.makedirs(output_dir, exist_ok=True)
    print(f"[INFO] Wyniki zostaną zapisane w: {output_dir}")

    product_urls = collect_product_urls()
    all_products = []

    for url in product_urls:
        category, subcategory = classify_product(url)
        
        if subcategory == "Unisex" and category != "Accessories":
            continue

        print(f"Scrapuję: {category} / {subcategory} -> {url}")
        try:
            product = parse_product_page(url, category, subcategory)
            if len(product["images"]) < 1:
                print(f"  [!] Pomijam {product['name']} – brak zdjęć")
                continue
            all_products.append(product)
            print(f"  OK: {product['name']} - cena: {product['price']} - zdjęcia: {len(product['images'])}")
        except Exception as e:
            print(f"  [!] Błąd przy {url}: {e}")

    csv_path = os.path.join(output_dir, "data_links.csv")
    fieldnames = ["name", "description", "price", "categories", "quantity", "images", "source_url", "color", "material"]

    with open(csv_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()

        for p in all_products:
            cat = p['category']
            sub = p['subcategory']
            
            if cat == "Accessories" and sub == "Unisex":
                categories_str = "Accessories/Men,Accessories/Women"
            else:
                categories_str = f"{cat}/{sub}"

            images_str = ",".join(p.get("images", []))

            row = {
                "name": p["name"],
                "description": p["description"],
                "price": p["price"],
                "categories": categories_str,
                "quantity": random.randint(0, 10),
                "images": images_str,
                "source_url": p["source_url"],
                "color": p["attributes"].get("color", ""),
                "material": p["attributes"].get("material", ""),
            }
            writer.writerow(row)

    print(f"Zakończono! Zapisano {len(all_products)} produktów do {csv_path}")

if __name__ == "__main__":
    main()
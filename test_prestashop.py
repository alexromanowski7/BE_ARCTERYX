import os
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select

# --- KONFIGURACJA ---
BASE_URL = os.getenv("SHOP_URL", "https://localhost:8443/")
CART_URL = BASE_URL.rstrip("/") + "/koszyk?action=show"
LOGIN_URL = BASE_URL.rstrip("/") + "/logowanie?create_account=1"
HISTORY_URL = BASE_URL.rstrip("/") + "/historia-zamowien"

# TWOJE KATEGORIE
CATEGORIES = ["16-men", "19-women", "21-men", "22-women", "31-men", "32-women"]
TARGET_PRODUCTS = 10  # Cel: 10 produktów w koszyku

def wait_visible(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))

def click_js(driver, element):
    """Bezpieczne kliknięcie JavaScriptem"""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)

def open_category_and_get_products(driver, category_slug):
    full_url = BASE_URL.rstrip("/") + "/" + category_slug
    # print(f"📂 Kategoria: {full_url}") # Ograniczam spam w konsoli
    driver.get(full_url)
    
    links = []
    try:
        wait_visible(driver, (By.CSS_SELECTOR, "#products, .products"), timeout=5)
        elements = driver.find_elements(By.TAG_NAME, "a")
        for a in elements:
            href = a.get_attribute("href")
            if href and ".html" in href and "product" not in href:
                if href not in links: links.append(href)
    except: pass
    
    random.shuffle(links) # Mieszamy, żeby nie brać zawsze tych samych
    return links

def add_product_to_cart_safe(driver, product_url):
    """
    Zwraca True jeśli dodano, False jeśli się nie udało.
    Bazuje na Twoim pierwotnym kodzie (try/except + zmiana qty na 1).
    """
    print(f"   -> Próba produktu: {product_url}")
    driver.get(product_url)
    time.sleep(1)

    # 1. Wybór wariantu (często odblokowuje przycisk)
    try:
        variant_selects = driver.find_elements(By.CSS_SELECTOR, ".product-variants select")
        for select_elem in variant_selects:
            select = Select(select_elem)
            try: select.select_by_index(0)
            except: pass
            time.sleep(1)
    except: pass

    # 2. Próba wpisania losowej ilości (1-4)
    qty = random.randint(1, 4)
    
    try:
        qty_input = driver.find_element(By.ID, "quantity_wanted")
        click_js(driver, qty_input)
        qty_input.clear()
        qty_input.send_keys(Keys.BACK_SPACE * 3)
        qty_input.send_keys(str(qty))
        qty_input.send_keys(Keys.TAB) # Trigger walidacji
        time.sleep(1)

        # 3. Sprawdzenie czy sklep nie blokuje (brak towaru)
        add_btn = driver.find_element(By.CSS_SELECTOR, "button[data-button-action='add-to-cart']")
        availability_msg = ""
        try:
            availability_msg = driver.find_element(By.ID, "product-availability").text.lower()
        except: pass

        # Jeśli zablokowane lub komunikat o braku -> Zmieniamy na 1 sztukę
        if not add_btn.is_enabled() or "nie ma wystarczającej" in availability_msg or "not enough" in availability_msg:
            print("      ⚠️ Za dużo sztuk. Zmieniam na 1.")
            qty_input.click()
            qty_input.clear()
            qty_input.send_keys("1")
            qty_input.send_keys(Keys.TAB)
            time.sleep(1)

        # Ponowne sprawdzenie przycisku
        if add_btn.is_enabled():
            click_js(driver, add_btn)
            
            # Czekamy na modal
            wait_visible(driver, (By.ID, "blockcart-modal"), timeout=5)
            print("      ✅ DODANO.")
            
            # Zamykamy modal (przycisk 'Kontynuuj zakupy' - btn-secondary)
            try:
                close_btns = driver.find_elements(By.CSS_SELECTOR, "#blockcart-modal .btn-secondary")
                if close_btns:
                    click_js(driver, close_btns[0])
                else:
                    # Fallback: kliknij w tło lub X
                    driver.find_element(By.CSS_SELECTOR, ".close").click()
            except: pass
            
            return True
        else:
            print("      ❌ Produkt niedostępny (przycisk nieaktywny).")
            return False

    except Exception as e:
        print(f"      ❌ Błąd w procesie dodawania: {e}")
        return False

def remove_from_cart(driver, n=3):
    print(f"🗑️ Usuwanie {n} szt.")
    driver.get(CART_URL)
    time.sleep(2)
    for i in range(n):
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, "a.remove-from-cart")
            if not btns: break
            click_js(driver, btns[0])
            time.sleep(2)
            print(f"   - Usunięto {i+1}")
        except: break

def register_account(driver):
    print(f"👤 Rejestracja...")
    driver.get(LOGIN_URL)
    email = f"klient{random.randint(10000,99999)}@test.pl"
    try:
        driver.find_element(By.NAME, "firstname").send_keys("Jan")
        driver.find_element(By.NAME, "lastname").send_keys("Testowy")
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys("Test1234!")
        
        cbs = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in cbs: click_js(driver, cb)
        
        save = driver.find_element(By.CSS_SELECTOR, "button[data-link-action='save-customer']")
        click_js(driver, save)
        time.sleep(2)
        print(f"   ✅ Zarejestrowano: {email}")
    except Exception as e:
        print(f"   ❌ Błąd rejestracji: {e}")

def checkout_process(driver):
    print("🚀 CHECKOUT START")
    driver.get(CART_URL)
    time.sleep(2)
    try:
        checkout_btn = driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-primary, .cart-detailed-actions a")
        if checkout_btn:
            click_js(driver, checkout_btn[0])
        else:
            return "PUSTY KOSZYK"
    except: pass
    time.sleep(2)

    # ADRES
    try:
        if driver.find_elements(By.NAME, "address1") and driver.find_element(By.NAME, "address1").is_displayed():
            driver.find_element(By.NAME, "address1").send_keys("Ulica Testowa 1")
            driver.find_element(By.NAME, "postcode").send_keys("00-001")
            driver.find_element(By.NAME, "city").send_keys("Warszawa")
            click_js(driver, driver.find_element(By.NAME, "confirm-addresses"))
        else:
            confirm_btns = driver.find_elements(By.NAME, "confirm-addresses")
            if confirm_btns: click_js(driver, confirm_btns[0])
    except: pass
    time.sleep(1)

    # DOSTAWA
    try:
        opts = driver.find_elements(By.CSS_SELECTOR, ".delivery-option input")
        if opts: click_js(driver, opts[0])
        click_js(driver, driver.find_element(By.NAME, "confirmDeliveryOption"))
    except: pass
    time.sleep(1)

    # PŁATNOŚĆ
    try:
        cod_input = driver.find_elements(By.CSS_SELECTOR, "input[data-module-name*='cashondelivery'], input[data-module-name*='cod']")
        if cod_input:
            click_js(driver, cod_input[0])
        else:
            inputs = driver.find_elements(By.CSS_SELECTOR, ".payment-options input[type='radio']")
            if inputs: click_js(driver, inputs[-1])

        terms = driver.find_elements(By.ID, "conditions_to_approve[terms-and-conditions]")
        if terms: click_js(driver, terms[0])

        click_js(driver, driver.find_element(By.CSS_SELECTOR, "#payment-confirmation button"))
        time.sleep(5)
        
        if "confirmation" in driver.current_url or "potwierdzenie" in driver.current_url:
            return "SUKCES"
        return "BŁĄD"
    except Exception as e:
        print(f"   ❌ Błąd checkoutu: {e}")
        return "BŁĄD"

def main():
    chrome_opts = ChromeOptions()
    chrome_opts.add_argument("--start-maximized")
    chrome_opts.add_argument("--ignore-certificate-errors")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    driver.implicitly_wait(3)

    try:
        # --- 1. DODAWANIE PRODUKTÓW (Pętla aż 10) ---
        products_added_count = 0
        
        print(f"--- ROZPOCZYNAM DODAWANIE (CEL: {TARGET_PRODUCTS}) ---")

        # Pętla główna: kręci się tak długo, aż uzbiera 10 produktów
        # Zabezpieczenie 'loop_limit' przed nieskończonością
        loop_limit = 0 
        
        while products_added_count < TARGET_PRODUCTS and loop_limit < 50:
            loop_limit += 1
            print(f"\n🔄 Przebieg pętli kategorii nr {loop_limit}...")
            
            for cat in CATEGORIES:
                if products_added_count >= TARGET_PRODUCTS: break
                
                links = open_category_and_get_products(driver, cat)
                
                for link in links:
                    if products_added_count >= TARGET_PRODUCTS: break
                    
                    # Tu wywołujemy starą, dobrą logikę dodawania
                    success = add_product_to_cart_safe(driver, link)
                    
                    if success:
                        products_added_count += 1
                        print(f"   🔢 Stan licznika: {products_added_count}/{TARGET_PRODUCTS}")

        if products_added_count < TARGET_PRODUCTS:
            print(f"⚠️ UWAGA: Nie udało się uzbierać {TARGET_PRODUCTS} produktów mimo {loop_limit} prób.")

        # --- 2. USUWANIE ---
        remove_from_cart(driver, 3)

        # --- 3. REJESTRACJA ---
        register_account(driver)

        # --- 4. CHECKOUT ---
        status = checkout_process(driver)
        print(f"=== WYNIK TESTU: {status} ===")

        # --- 5. FAKTURA ---
        driver.get(HISTORY_URL)
        try:
             wait_visible(driver, (By.ID, "content"), timeout=5)
             if driver.find_elements(By.CSS_SELECTOR, "a[href*='.pdf']"):
                 print("✅ FAKTURA JEST DOSTĘPNA.")
             else:
                 print("ℹ️  Brak faktury (zależy od ustawień statusu w adminie).")
        except: pass

    except Exception as e:
        print(f"BŁĄD KRYTYCZNY: {e}")
    finally:
        print("Koniec pracy. Zamykam za 5s.")
        time.sleep(5)
        driver.quit()

if __name__ == "__main__":
    main()
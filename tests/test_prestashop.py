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

BASE_URL = os.getenv("SHOP_URL", "https://localhost/")
CART_URL = BASE_URL.rstrip("/") + "/koszyk?action=show"
LOGIN_URL = BASE_URL.rstrip("/") + "/logowanie" 
HISTORY_URL = BASE_URL.rstrip("/") + "/historia-zamowien"

ADMIN_URL = "https://localhost/admin697jmd6ap" 
ADMIN_EMAIL = "admin@sklep.pl" 
ADMIN_PASS = "password123"

CATEGORIES = ["14-men", "17-women", "16-men", "18-women", "11-men", "12-women"]
SEARCH_QUERY = "Hummingbird"
TARGET_PRODUCTS = 10 

def wait_visible(driver, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))

def click_js(driver, element):
    """Bezpieczne kliknięcie JavaScriptem (ignoruje elementy zasłaniające)"""
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    time.sleep(0.5)
    driver.execute_script("arguments[0].click();", element)

def search_and_add_product(driver, query):
    print(f"🔍 Wyszukiwanie: '{query}'")
    try:
        search_box = driver.find_element(By.NAME, "s")
        search_box.clear()
        search_box.send_keys(query)
        search_box.send_keys(Keys.ENTER)
        wait_visible(driver, (By.CSS_SELECTOR, "#products"), timeout=5)
        
        links = [a.get_attribute("href") for a in driver.find_elements(By.CSS_SELECTOR, ".products .product-title a")]
        if links:
            return add_product_to_cart_safe(driver, random.choice(links))
    except: pass
    return False

def open_category_and_get_products(driver, category_slug):
    driver.get(BASE_URL.rstrip("/") + "/" + category_slug)
    links = []
    try:
        wait_visible(driver, (By.CSS_SELECTOR, "#products, .products"), timeout=5)
        for a in driver.find_elements(By.TAG_NAME, "a"):
            href = a.get_attribute("href")
            if href and ".html" in href and "product" not in href and href not in links:
                links.append(href)
    except: pass
    random.shuffle(links)
    return links

def add_product_to_cart_safe(driver, product_url):
    print(f"   -> Produkt: {product_url}")
    driver.get(product_url)
    time.sleep(1)
    try:
        try: Select(driver.find_element(By.CSS_SELECTOR, ".product-variants select")).select_by_index(0)
        except: pass
        
        qty = random.randint(1, 3)
        q_input = driver.find_element(By.ID, "quantity_wanted")
        click_js(driver, q_input)
        q_input.clear()
        q_input.send_keys(Keys.BACK_SPACE*3 + str(qty) + Keys.TAB)
        time.sleep(1)

        btn = driver.find_element(By.CSS_SELECTOR, "button[data-button-action='add-to-cart']")
        if btn.is_enabled():
            click_js(driver, btn)
            wait_visible(driver, (By.ID, "blockcart-modal"), timeout=5)
            print("      ✅ DODANO.")
            try: click_js(driver, driver.find_element(By.CSS_SELECTOR, "#blockcart-modal .btn-secondary"))
            except: pass
            return True
        return False
    except: return False

def remove_from_cart(driver, n=3):
    print(f"🗑️ Usuwanie {n} szt.")
    driver.get(CART_URL)
    time.sleep(2)
    for _ in range(n):
        try:
            click_js(driver, driver.find_element(By.CSS_SELECTOR, "a.remove-from-cart"))
            time.sleep(2)
        except: break

def register_account(driver):
    print(f"👤 Rejestracja klienta...")
    driver.get(BASE_URL.rstrip("/") + "/logowanie?create_account=1")
    email = f"klient{random.randint(100000,999999)}@test.pl"
    password = "Test1234!"
    
    try:
        driver.find_element(By.NAME, "firstname").send_keys("Jan")
        driver.find_element(By.NAME, "lastname").send_keys("Automatyczny")
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        for cb in driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"): click_js(driver, cb)
        
        save_btn = driver.find_element(By.CSS_SELECTOR, "button[data-link-action='save-customer']")
        click_js(driver, save_btn)
        time.sleep(2)
        print(f"   ✅ Konto utworzone: {email}")
        return email, password
    except Exception as e:
        print(f"   ❌ Błąd rejestracji: {e}")
        return None, None

def login_customer_again(driver, email, password):
    """Loguje klienta ponownie, bo Admin mógł zabić sesję"""
    print(f"👤 Ponowne logowanie klienta ({email})...")
    driver.get(LOGIN_URL)
    time.sleep(1)
    try:
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        click_js(driver, driver.find_element(By.ID, "submit-login"))
        time.sleep(2)
    except: pass

def checkout_process(driver):
    print("🚀 Checkout...")
    driver.get(CART_URL)
    time.sleep(2)
    try:
        btns = driver.find_elements(By.CSS_SELECTOR, "a.btn.btn-primary")
        if btns: click_js(driver, btns[0])
        else: return "PUSTY"
    except: pass
    time.sleep(2)

    try:
        if len(driver.find_elements(By.NAME, "address1")) > 0:
            driver.find_element(By.NAME, "address1").send_keys("Ulica 1")
            driver.find_element(By.NAME, "postcode").send_keys("00-001")
            driver.find_element(By.NAME, "city").send_keys("Miasto")
            click_js(driver, driver.find_element(By.NAME, "confirm-addresses"))
        else:
            conf = driver.find_elements(By.NAME, "confirm-addresses")
            if conf: click_js(driver, conf[0])
    except: pass
    time.sleep(1)

    try:
        opts = driver.find_elements(By.CSS_SELECTOR, ".delivery-option input")
        if opts: click_js(driver, opts[0])
        click_js(driver, driver.find_element(By.NAME, "confirmDeliveryOption"))
    except: pass
    time.sleep(1)

    try:
        cod = driver.find_elements(By.CSS_SELECTOR, "input[data-module-name*='cashondelivery'], input[data-module-name*='cod']")
        if cod: click_js(driver, cod[0])
        else: click_js(driver, driver.find_elements(By.CSS_SELECTOR, ".payment-options input")[-1])
        
        terms = driver.find_elements(By.ID, "conditions_to_approve[terms-and-conditions]")
        if terms: click_js(driver, terms[0])
        
        click_js(driver, driver.find_element(By.CSS_SELECTOR, "#payment-confirmation button"))
        time.sleep(5)
        return "SUKCES" if "confirmation" in driver.current_url or "potwierdzenie" in driver.current_url else "BŁĄD"
    except: return "BŁĄD"

def change_order_status_in_admin(driver):
    print(f"\n🔧 PANEL ADMINA: Zmiana statusu...")
    driver.get(ADMIN_URL)
    time.sleep(2)

    if len(driver.find_elements(By.ID, "email")) > 0:
        driver.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)
        driver.find_element(By.ID, "passwd").send_keys(ADMIN_PASS)
        click_js(driver, driver.find_element(By.NAME, "submitLogin"))
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "main")))

    try:
        if "token=" in driver.current_url:
            import re
            token = re.search(r'token=([a-zA-Z0-9]+)', driver.current_url).group(1)
            driver.get(driver.current_url.split("?")[0] + f"?controller=AdminOrders&token={token}")
    except: pass
    time.sleep(2)

    try:
        wait_visible(driver, (By.TAG_NAME, "table"), 10)
        print("   -> Klikam w status na liście...")
        
        btn = driver.find_element(By.XPATH, "//tbody//tr[1]//button[contains(@class, 'dropdown-toggle')]")
        click_js(driver, btn)
        time.sleep(1)
        
        print("   -> Wybieram 'Dostarczone'...")
        opt = driver.find_element(By.XPATH, "//div[contains(@class, 'dropdown-menu')]//*[contains(text(), 'Dostarczone')]")
        click_js(driver, opt)
        
        print("   ✅ Status zmieniony.")
        time.sleep(3)
        
    except Exception as e:
        print(f"   ⚠️ Błąd zmiany statusu na liście: {e}")
        try:
            click_js(driver, driver.find_element(By.CSS_SELECTOR, "table.order tbody tr:first-child td a.btn"))
            time.sleep(3)
            click_js(driver, driver.find_element(By.ID, "update_order_status_action_btn"))
            click_js(driver, driver.find_element(By.XPATH, "//*[contains(text(), 'Dostarczone')]"))
            try: click_js(driver, driver.find_element(By.CSS_SELECTOR, "button.add-order-state-btn"))
            except: pass
        except: pass

def main():
    chrome_opts = ChromeOptions()
    chrome_opts.add_argument("--start-maximized")
    chrome_opts.add_argument("--ignore-certificate-errors")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_opts)
    driver.implicitly_wait(5)

    try:
        products_added_count = 0
        print(f"--- START TESTU ---")

        if search_and_add_product(driver, SEARCH_QUERY): products_added_count += 1
        
        loop = 0
        while products_added_count < TARGET_PRODUCTS and loop < 50:
            loop += 1
            for cat in CATEGORIES:
                if products_added_count >= TARGET_PRODUCTS: break
                for link in open_category_and_get_products(driver, cat):
                    if products_added_count >= TARGET_PRODUCTS: break
                    if add_product_to_cart_safe(driver, link): products_added_count += 1

        remove_from_cart(driver, 3)
        
        client_email, client_pass = register_account(driver)
        
        status = checkout_process(driver)
        print(f"=== ZAMÓWIENIE: {status} ===")

        if status == "SUKCES":
            change_order_status_in_admin(driver)

            if client_email and client_pass:
                login_customer_again(driver, client_email, client_pass)
            
            print("\n📄 Pobieranie faktury...")
            driver.get(HISTORY_URL)
            time.sleep(2)
            try:
                 wait_visible(driver, (By.ID, "content"), timeout=5)
                 
                 print("   -> Szukam ikonki PDF...")
                 
                 invoice_link = driver.find_element(By.XPATH, "//table//a[contains(@href, 'pdf') or contains(@href, 'PDF')]")
                 
                 if invoice_link:
                     print(f"   ✅ ZNALEZIONO! Klikam w ikonkę...")
                     click_js(driver, invoice_link)
                     time.sleep(5)
                     print("   ⬇️  Pobrano fakturę.")
                 else:
                     print("   ℹ️  Nie widzę ikonki PDF. Sprawdź status 'Dostarczone'.")
                     
            except Exception as e:
                print(f"   ❌ Nie udało się kliknąć w PDF: {e}")
                driver.save_screenshot("error_invoice_click.png")

    except Exception as e:
        print(f"BŁĄD KRYTYCZNY: {e}")
    finally:
        print("Koniec pracy.")
        driver.quit()

if __name__ == "__main__":
    main()
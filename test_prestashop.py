import os
import random
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = os.getenv("SHOP_URL", "https://shop.local/")  # ustaw swój host
EMAIL_DOMAIN = "example.test"
WAIT = 10

def wait_click(driver, locator, timeout=WAIT):
    return WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))

def wait_visible(driver, locator, timeout=WAIT):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located(locator))

def add_product_from_card(driver, product_url, qty=1):
    driver.get(product_url)
    qty_input = wait_visible(driver, (By.CSS_SELECTOR, "input#quantity_wanted"))
    qty_input.clear()
    qty_input.send_keys(str(qty))
    add_btn = wait_click(driver, (By.CSS_SELECTOR, "button[data-button-action='add-to-cart']"))
    add_btn.click()
    wait_visible(driver, (By.CSS_SELECTOR, ".cart-content-btn .btn-primary, .modal-content"))  # modal potwierdzenia
    # zamknij modal, jeśli się pojawia
    try:
        close_modal = driver.find_element(By.CSS_SELECTOR, "button.close, .modal .close")
        close_modal.click()
        WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, ".modal.show")))
    except Exception:
        pass

def open_category(driver, cat_slug):
    driver.get(BASE_URL.strip("/") + f"/{cat_slug}")
    wait_visible(driver, (By.CSS_SELECTOR, "#products, .product_list, .products"))

def collect_product_links_on_page(driver, max_items=20):
    links = []
    cards = driver.find_elements(By.CSS_SELECTOR, ".product-miniature a.product-thumbnail, article.product-miniature a")
    for a in cards[:max_items]:
        href = a.get_attribute("href")
        if href and "/product" in href:
            links.append(href)
    return list(dict.fromkeys(links))  # dedupe

def ensure_cart_page(driver):
    driver.get(BASE_URL.strip("/") + "/cart")
    wait_visible(driver, (By.CSS_SELECTOR, "#cart, .cart-grid"))

def remove_n_items_from_cart(driver, n=3):
    ensure_cart_page(driver)
    removed = 0
    while removed < n:
        remove_btns = driver.find_elements(By.CSS_SELECTOR, "a.cart-remove, a.remove-from-cart, .remove-from-cart")
        if not remove_btns:
            # alternatywny selektor 1.7
            remove_btns = driver.find_elements(By.CSS_SELECTOR, "i.material-icons.clear")
        if not remove_btns:
            break
        wait_click(driver, (By.XPATH, f"(//a[contains(@class,'remove-from-cart') or contains(@class,'cart-remove') or i[contains(@class,'clear')]])[{1}]")).click()
        time.sleep(1)
        removed += 1
        WebDriverWait(driver, 10).until(lambda d: True)  # krótki oddech na przeliczenie

def register_account(driver):
    driver.get(BASE_URL.strip("/") + "/login?create_account=1")
    wait_visible(driver, (By.CSS_SELECTOR, "form#customer-form"))
    now_tag = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    email = f"test+{now_tag}@{EMAIL_DOMAIN}"
    # Pola formularza mogą zależeć od motywu; typowy Classic:
    driver.find_element(By.NAME, "firstname").send_keys("Jan")
    driver.find_element(By.NAME, "lastname").send_keys("Kowalski")
    driver.find_element(By.NAME, "email").send_keys(email)
    driver.find_element(By.NAME, "password").send_keys("Test12345!")
    # Zgody mogą być wymagane
    try:
        driver.find_element(By.NAME, "psgdpr").click()
    except Exception:
        pass
    driver.find_element(By.CSS_SELECTOR, "form#customer-form button[type='submit']").click()
    wait_visible(driver, (By.CSS_SELECTOR, ".account, a.account, .logout"))
    return email

def checkout_and_place_order_cod_with_carrier(driver, carrier_index=1):
    # Przejdź do koszyka i rozpocznij checkout
    ensure_cart_page(driver)
    # przycisk "Złóż zamówienie" / "Proceed to checkout"
    try:
        wait_click(driver, (By.CSS_SELECTOR, "a.btn.btn-primary, a.checkout, .cart-detailed-actions a")).click()
    except Exception:
        # alternatywa
        driver.get(BASE_URL.strip("/") + "/order")
    # Adres
    try:
        wait_click(driver, (By.NAME, "address1")).send_keys("Testowa 1")
        driver.find_element(By.NAME, "postcode").send_keys("00-001")
        driver.find_element(By.NAME, "city").send_keys("Warszawa")
        # kraj może być predefiniowany na PL
        driver.find_element(By.CSS_SELECTOR, "button[name='confirm-addresses'], button[name='confirm-address']").click()
    except Exception:
        # jeśli adres już istnieje
        try:
            wait_click(driver, (By.CSS_SELECTOR, "button[name='confirm-addresses'], button[name='confirm-address']")).click()
        except Exception:
            pass
    # Przewoźnik
    wait_visible(driver, (By.CSS_SELECTOR, "#js-delivery, .delivery-options-list"))
    carriers = driver.find_elements(By.CSS_SELECTOR, "input[name='delivery_option'], input[name='delivery_option[0]']")
    if len(carriers) >= carrier_index:
        carriers[carrier_index - 1].click()
    # akceptacja regulaminu dostawy bywa wymagana
    try:
        driver.find_element(By.NAME, "delivery_message").send_keys("Proszę dostarczyć po 18:00")
    except Exception:
        pass
    # potwierdź sekcję dostawy
    try:
        wait_click(driver, (By.CSS_SELECTOR, "button[name='confirmDeliveryOption'], button[name='confirmDeliveryOption[0]']")).click()
    except Exception:
        pass
    # Płatność – wybierz „przy odbiorze”
    wait_visible(driver, (By.CSS_SELECTOR, "#payment-option, .payment-options"))
    # typowe selektory COD:
    cod_inputs = driver.find_elements(By.CSS_SELECTOR, "input[id*='cashondelivery'], input[id*='cod'], input[name='payment-option'][id*='delivery']")
    if not cod_inputs:
        cod_inputs = driver.find_elements(By.CSS_SELECTOR, "input[name='payment-option']")
    if cod_inputs:
        cod_inputs[0].click()
    # akceptacja regulaminu zakupów
    try:
        driver.find_element(By.ID, "conditions_to_approve[terms-and-conditions]").click()
    except Exception:
        try:
            driver.find_element(By.NAME, "conditions_to_approve[terms-and-conditions]").click()
        except Exception:
            pass
    # Zatwierdź zamówienie
    pay_btn = None
    for sel in [
        "button.btn.btn-primary.center-block",
        "button#payment-confirmation button",
        "#payment-confirmation button",
        "button[name='confirmOrder']",
    ]:
        try:
            pay_btn = wait_click(driver, (By.CSS_SELECTOR, sel), timeout=15)
            break
        except Exception:
            continue
    if pay_btn:
        pay_btn.click()
    # Oczekuj strony potwierdzenia
    wait_visible(driver, (By.CSS_SELECTOR, ".order-confirmation, .order-confirmation-card, .page-order-confirmation"))
    # Status zamówienia (tekstowo)
    try:
        status_el = driver.find_element(By.CSS_SELECTOR, ".order-confirmation .status, .order-confirmation-card .status")
        status = status_el.text.strip()
    except Exception:
        status = "Zamówienie złożone"
    return status

def download_invoice_from_account(driver):
    # Przejdź do konta → Historia zamówień
    driver.get(BASE_URL.strip("/") + "/history")
    wait_visible(driver, (By.CSS_SELECTOR, ".order-history, table.table"))
    # Kliknij „Pobierz fakturę”/„Invoice” (zwykle link PDF)
    links = driver.find_elements(By.LINK_TEXT, "Pobierz fakturę")
    if not links:
        links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Faktura")
    if not links:
        links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Invoice")
    if links:
        links[0].click()
        time.sleep(2)  # czas na pobranie

def main():
    chrome_opts = ChromeOptions()
    chrome_opts.add_argument("--start-maximized")
    chrome_opts.add_argument("--ignore-certificate-errors")
    chrome_opts.add_argument("--incognito")
    # Uwaga: dla realnego pobrania PDF można skonfigurować auto-download do katalogu.
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_opts)
    driver.set_page_load_timeout(60)
    driver.implicitly_wait(2)

    try:
        driver.get(BASE_URL)
        wait_visible(driver, (By.CSS_SELECTOR, "body"))

        # 1) Dodaj 10 produktów z dwóch kategorii (po 5 na kategorię) w różnych ilościach
        categories = ["2-men", "3-women"]  # podmień na swoje slugi kategorii
        total_added = 0
        for cat in categories:
            open_category(driver, cat)
            product_links = collect_product_links_on_page(driver, max_items=12)
            random.shuffle(product_links)
            for link in product_links[:5]:
                qty = random.randint(1, 3)
                add_product_from_card(driver, link, qty=qty)
                total_added += 1
        # 2) Wyszukiwanie produktu i dodanie losowego
        search_box = wait_visible(driver, (By.NAME, "s"))
        search_box.clear()
        search_box.send_keys("test")
        search_box.send_keys(Keys.ENTER)
        wait_visible(driver, (By.CSS_SELECTOR, "#products, .products"))
        found = collect_product_links_on_page(driver, max_items=10)
        if found:
            add_product_from_card(driver, random.choice(found), qty=1)

        # 3) Usuń 3 produkty z koszyka
        remove_n_items_from_cart(driver, n=3)

        # 4) Rejestracja konta
        email = register_account(driver)

        # 5-9) Checkout: wybór przewoźnika, płatność przy odbiorze, zatwierdzenie, status
        status = checkout_and_place_order_cod_with_carrier(driver, carrier_index=1)

        # 10) Pobranie faktury VAT (po złożeniu zamówienia)
        download_invoice_from_account(driver)

        print("Test E2E zakończony. Status:", status)
        print("Email konta:", email)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()

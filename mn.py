from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
import os

class EuropagesScraper:
    def __init__(self, niche: str, max_pages: int, headless: bool = True):
        self.niche = niche
        self.max_pages = max_pages
        self.base_url = "https://www.europages.co.uk/en/search"
        self.browser = self.init_browser(headless)
        self.profile_links = []
        self.company_websites = {}

    def init_browser(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        service = Service(ChromeDriverManager().install())
        browser = webdriver.Chrome(service=service, options=chrome_options)
        browser.implicitly_wait(10)
        return browser

    def accept_cookies(self):
        try:
            cookie_buttons = WebDriverWait(self.browser, 5).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'accept')]"))
            )
            for button in cookie_buttons:
                try:
                    button.click()
                    time.sleep(2)
                    break
                except:
                    continue
        except TimeoutException:
            pass

    def collect_profile_links(self):
        for page in range(1, self.max_pages + 1):
            if page == 1:
                url = f"{self.base_url}?cserpRedirect=1&q={self.niche}"
            else:
                url = f"{self.base_url}/page/{page}?cserpRedirect=1&q={self.niche}"

            self.browser.get(url)
            self.accept_cookies()
            time.sleep(3)

            links = [link.get_attribute("href") for link in self.browser.find_elements(By.CSS_SELECTOR, "a[data-test='company-name']")]
            self.profile_links.extend([l for l in links if l and l.startswith("http")])
        
        self.save_json(self.profile_links, f"{self.niche}_collected_links.json")
        print(f"[✅] Collected {len(self.profile_links)} Europages profile links.")

    def collect_company_websites(self):
        for link in self.profile_links:
            self.browser.get(link)
            self.accept_cookies()
            time.sleep(3)
            try:
                website_button = WebDriverWait(self.browser, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.website-button"))
                )
                website_url = website_button.get_attribute("href")
                if website_url and website_url.startswith("http"):
                    self.company_websites[link] = website_url
                    print(f"[INFO] Found website: {website_url}")
            except TimeoutException:
                print(f"[INFO] No website found for: {link}")
                continue

        self.save_json(self.company_websites, f"{self.niche}_company_websites.json")
        print(f"[✅] Collected {len(self.company_websites)} company websites.")

    def save_json(self, data, filename):
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def close(self):
        self.browser.quit()

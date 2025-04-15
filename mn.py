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
import tempfile
import uuid
import shutil

class EuropagesScraper:
    def __init__(self, niche: str, max_pages: int, headless: bool = True):
        self.niche = niche
        self.max_pages = max_pages
        self.base_url = "https://www.europages.co.uk/en/search"
        self.user_data_dir = None
        self.browser = self.init_browser(headless)
        self.profile_links = []
        self.company_websites = {}

    def init_browser(self, headless):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--disable-gpu")

            # ✅ Create a unique user data dir every time
            self.user_data_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
            if os.path.exists(self.user_data_dir):
                shutil.rmtree(self.user_data_dir)
            os.makedirs(self.user_data_dir)
            chrome_options.add_argument(f"--user-data-dir={self.user_data_dir}")

        # ✅ Ensure correct path to ChromeDriver
        service = Service("/usr/bin/chromedriver")  # Adjust if needed
        service_log_path="chromedriver.log"

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
        if self.browser:
            try:
                self.browser.quit()
            except Exception as e:
                print(f"[WARN] Failed to close browser: {e}")
        if self.user_data_dir and os.path.exists(self.user_data_dir):
            try:
                shutil.rmtree(self.user_data_dir)
            except Exception as e:
                print(f"[WARN] Failed to remove temp user data dir: {e}")
'''
    def close(self):
        self.browser.quit()
        # Clean up the user data dir
        try:
            if self.user_data_dir and os.path.exists(self.user_data_dir):
                shutil.rmtree(self.user_data_dir)
        except Exception as e:
            print(f"[WARN] Could not clean up user data dir: {e}")
'''

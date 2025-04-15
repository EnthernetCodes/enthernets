from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')  # Run without GUI
options.add_argument('--no-sandbox')  # Required for root
options.add_argument('--disable-dev-shm-usage')  # Avoid shared memory crashes
options.add_argument('--remote-debugging-port=9222')  # Optional: debug
options.add_argument('--disable-gpu')  # Optional: headless mode stability

service = Service("/usr/bin/chromedriver")
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://www.google.com")
print(driver.title)

driver.quit()

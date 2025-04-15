from flask import jsonify
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
import csv
import json
import os
import re
from filelock import FileLock

from mn import EuropagesScraper  # importing your class from mn.py

# ======= File Handling =======
def save_json(data, filename):
    lock_dir = "locks"
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, f"{filename}.lock")

    with FileLock(lock_path):
        with open(filename, "w") as file:
            json.dump(data, file, indent=4)

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as file:
            return json.load(file)
    return []

# ======= Extract Emails from the Official Website =======
def extract_emails_from_website(session, website_url):
    try:
        response = session.get(website_url, timeout=10)
        page_text = response.text
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_text)
        return list(set(emails))
    except Exception as e:
        print(f"[ERROR] Failed to extract emails from {website_url}: {e}")
        return []

# ======= Scrape Company Details from Official Websites =======
def scrape_company_details(session, company_websites, niche):
    scraped_data = load_json(f"{niche}_scraped_data.json")

    for europages_url, company_site in tqdm(company_websites.items(), desc="Scraping Company Details", unit="company"):
        if any(d["Website"] == company_site for d in scraped_data):
            continue

        print(f"[INFO] Visiting official site: {company_site}")
        emails = extract_emails_from_website(session, company_site)

        if emails:
            scraped_data.append({
                "Europages Profile": europages_url,
                "Website": company_site,
                "Emails": emails
            })
            save_json(scraped_data, f"{niche}_scraped_data.json")

    return scraped_data

# ======= Export to CSV =======
def export_to_csv(data, filename):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["Europages Profile", "Website", "Emails"])
        writer.writeheader()
        for entry in data:
            writer.writerow({
                "Europages Profile": entry["Europages Profile"],
                "Website": entry["Website"],
                "Emails": ", ".join(entry["Emails"])
            })
    print(f"[✅] Data exported to '{filename}'")

# ======= Extract Emails and Company Names from CSV =======
def extract_email_and_company_from_csv(input_csv, output_csv):
    with open(input_csv, newline='', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        rows = []
        for row in reader:
            company_name = row["Website"].split("//")[-1].split("/")[0] if "Website" in row else ""
            email = row["Emails"].split(",")[0] if "Emails" in row and row["Emails"] else ""
            rows.append({"Company Name": company_name, "Email": email})

    with open(output_csv, "w", newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=["Company Name", "Email"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✅] Extracted emails and company names saved to '{output_csv}'")

# ======= Main Run Function =======
def run_scraper(niche, max_pages, log=print):
    log("[RUN] Scraper started...")

    session = requests.Session()
    scraper = EuropagesScraper(niche=niche, max_pages=max_pages)

    scraper.collect_profile_links()
    log(f"[RUN] Collected {len(scraper.profile_links)} profile links.")

    scraper.collect_company_websites()
    log(f"[RUN] Collected {len(scraper.company_websites)} company websites.")

    scraper.close()

    if not scraper.company_websites:
        log("[RUN] No company websites found. Exiting early.")
        return []

#    results = scrape_company_details(scraper.company_websites, niche, session=session, log=log)
    results = scrape_company_details(session, scraper.company_websites, niche)
    return results

    '''
def run_scraper(niche, max_pages):
    session = requests.Session()

    # Use Selenium scraper to collect profile links & websites
    scraper = EuropagesScraper(niche=niche, max_pages=max_pages)
    scraper.collect_profile_links()
    scraper.collect_company_websites()
    scraper.close()

    company_websites = scraper.company_websites

    # Now continue with requests + BeautifulSoup to extract emails
    scraped_data = scrape_company_details(session, company_websites, niche)
    export_to_csv(scraped_data, f"{niche}_scraped_companies.csv")
    extract_email_and_company_from_csv(f"{niche}_scraped_companies.csv", f"{niche}_emails.csv")

    return scraped_data
'''

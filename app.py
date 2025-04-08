from flask import Flask, render_template
from flask import Flask, request, render_template, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
import csv
import requests
import os
from datetime import datetime
import json
from m import (
    collect_company_links,
    collect_company_websites,
    scrape_company_details,
    export_to_csv,
    extract_email_and_company_from_csv,
    save_json
)


app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scraped_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
from admin import setup_admin

# after creating app and db
setup_admin(app)

db = SQLAlchemy(app)

class ScrapedCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    niche = db.Column(db.String(100), nullable=False)
    europages_profile = db.Column(db.String, nullable=False)
    website = db.Column(db.String, nullable=False)
    emails = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ NEW

    def __repr__(self):
        return f"<ScrapedCompany {self.website}>"


from threading import Thread

def background_scrape(niche, max_pages):
    base_url = "https://www.europages.co.uk/en/search"
    page_urls = [f"{base_url}?cserpRedirect=1&q={niche}"] + [
        f"{base_url}/page/{page}?cserpRedirect=1&q={niche}" for page in range(2, max_pages + 1)
    ]
    session = requests.Session()

    try:
        progress = {"niche": niche, "current_stage": "Collecting profile links", "progress_detail": ""}
        save_json(progress, f"progress_{niche}.json")
        europages_links = collect_company_links(session, page_urls)

        progress["current_stage"] = "Finding official websites"
        save_json(progress, f"progress_{niche}.json")
        company_websites = collect_company_websites(session, europages_links)

        progress["current_stage"] = "Scraping company details"
        save_json(progress, f"progress_{niche}.json")
        scraped_data = scrape_company_details(session, company_websites, niche)

        os.makedirs("data", exist_ok=True)
        with app.app_context():
          for entry in scraped_data:
              new_record = ScrapedCompany(
                  niche=niche,
                  europages_profile=entry["Europages Profile"],
                  website=entry["Website"],
                  emails=", ".join(entry["Emails"])
              )
              db.session.add(new_record)
          db.session.commit()

        csv_file = f"data/{niche}_scraped_companies.csv"
        email_csv = f"data/{niche}_emails.csv"
        export_to_csv(scraped_data, csv_file)
        extract_email_and_company_from_csv(csv_file, email_csv)

        progress["current_stage"] = "Complete"
        save_json(progress, f"progress_{niche}.json")

    except Exception as e:
        progress = {"niche": niche, "current_stage": f"Error: {e}", "progress_detail": ""}
        save_json(progress, f"progress_{niche}.json")

@app.route("/progress/<niche>")
def progress(niche):
    progress_file = f"progress_{niche}.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            return f.read()
    return {"niche": niche, "current_stage": "Not started", "progress_detail": ""}

@app.route("/extractor", methods=["GET", "POST"])
def extract():
    if request.method == "POST":
        niche = request.form["niche"]
        max_pages = int(request.form["max_pages"])

        base_url = "https://www.europages.co.uk/en/search"
        page_urls = [f"{base_url}?cserpRedirect=1&q={niche}"] + [
            f"{base_url}/page/{page}?cserpRedirect=1&q={niche}" for page in range(2, max_pages + 1)
        ]

        # Set initial progress
        save_json({"niche": niche, "current_stage": "Starting...", "progress_detail": ""}, f"progress_{niche}.json")

        # Launch background scraping
        thread = Thread(target=background_scrape, args=(niche, max_pages))
        thread.start()

        return redirect(url_for("results", niche=niche))

        session = requests.Session()

        try:
            progress = {"niche": niche, "current_stage": "Collecting profile links", "progress_detail": ""}
            save_json(progress, f"progress_{niche}.json")
            europages_links = collect_company_links(session, page_urls)

            progress["current_stage"] = "Finding official websites"
            save_json(progress, f"progress_{niche}.json")
            company_websites = collect_company_websites(session, europages_links)

            progress["current_stage"] = "Scraping company details"
            save_json(progress, f"progress_{niche}.json")
            scraped_data = scrape_company_details(session, company_websites, niche)

            os.makedirs("data", exist_ok=True)
            for entry in scraped_data:
                new_record = ScrapedCompany(
                    niche=niche,
                    europages_profile=entry["Europages Profile"],
                    website=entry["Website"],
                    emails=", ".join(entry["Emails"])
                )
                db.session.add(new_record)
            db.session.commit()

            csv_file = f"data/{niche}_scraped_companies.csv"
            email_csv = f"data/{niche}_emails.csv"
            export_to_csv(scraped_data, csv_file)
            extract_email_and_company_from_csv(csv_file, email_csv)

            return redirect(url_for("results", niche=niche))

        except Exception as e:
            flash(f"Error during scraping: {e}", "error")
            return redirect(url_for("extract"))

    return render_template("extractor.html")

@app.route("/results/<niche>")
def results(niche):
    csv_file = f"data/{niche}_scraped_companies.csv"
    email_file = f"data/{niche}_emails.csv"
    progress_file = f"progress_{niche}.json"

    results_data = ScrapedCompany.query.filter_by(niche=niche).all()

    progress = {"niche": niche, "current_stage": "Complete", "progress_detail": ""}
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as file:
            content = file.read().strip()
            if content:
              progress.update(json.loads(content))
            else:
              print(f"⚠️ Progress file {progress_file} is empty.")

    return render_template("results.html", results_data=results_data, progress=progress)

@app.route("/download/<niche>")
def download(niche):
    email_file = f"data/{niche}_emails.csv"
    if os.path.exists(email_file):
        return send_file(email_file, as_attachment=True)
    else:
        flash("Download file not found.", "error")
        return redirect(url_for("results", niche=niche))

@app.route('/all-data')
def all_data():
    data = ScrapedCompany.query.all()
    return render_template("all_data.html", data=data)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

from flask import Flask, request, render_template, redirect, url_for, send_file, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import csv
import requests
import os
from datetime import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from m import (
    scrape_company_details,
    export_to_csv,
    extract_email_and_company_from_csv,
    save_json,
    run_scraper
)


app = Flask(__name__)
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
import logging

executor = ThreadPoolExecutor(max_workers=2)  # You can adjust this number

def background_scrape(niche, max_pages):
    # Setup log file
    log_path = f"{niche}_log.txt"
    logging.basicConfig(filename=log_path, level=logging.INFO, format='[%(asctime)s] %(message)s')
    log = lambda msg: (print(msg), logging.info(msg))  # Log to both terminal and file

    progress = {
        "niche": niche,
        "current_stage": "Scraping in progress",
        "progress_detail": ""
    }
    save_json(progress, f"progress_{niche}.json")

    try:
        log(f"[THREAD] Background scraper started for niche: {niche}, pages: {max_pages}")
        scraped_data = run_scraper(niche, max_pages, log=log)
        print(f"Querying database for niche: {niche}")
#        print(f"Found {len(results_data)} results.")
        log(f"[DB] Inserting {len(scraped_data)} records into database...")
        with app.app_context():
            for entry in scraped_data:
                new_record = ScrapedCompany(
                    niche=niche,
                    europages_profile=entry["Europages Profile"],
                    website=entry["Website"],
                    emails=", ".join(entry["Emails"])
                )
                print(f"Saving record: {new_record}")
                db.session.add(new_record)
            db.session.commit()
        log("[DB] Database insert complete.")

        progress["current_stage"] = "Complete"
        save_json(progress, f"progress_{niche}.json")

    except Exception as e:
        error_msg = f"[ERROR] Scraping failed: {e}"
        log(error_msg)
        progress["current_stage"] = error_msg
        save_json(progress, f"progress_{niche}.json")

'''@app.route("/progress/<niche>")
def progress(niche):
    progress_file = f"progress_{niche}.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            return f.read()
    return {"niche": niche, "current_stage": "Not started", "progress_detail": ""}
'''

@app.route("/progress/<niche>")
def progress(niche):
    progress_file = f"progress_{niche}.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            content = f.read()
            return jsonify(json.loads(content))  # Ensure it returns a valid JSON response
    return jsonify({"niche": niche, "current_stage": "Not started", "progress_detail": ""})

@app.route("/")
def home():
    return render_template("extractor.html")

@app.route("/extractor", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        niche = request.form["niche"]
        max_pages = int(request.form["max_pages"])

        # Set initial progress
        save_json({"niche": niche, "current_stage": "Starting...", "progress_detail": ""}, f"progress_{niche}.json")

        # Launch background scraper
        executor.submit(background_scrape, niche, max_pages)
#        thread = Thread(target=background_scrape, args=(niche, max_pages))
#        thread.start()

        # Redirect to progress page
        return redirect(url_for("results", niche=niche))

    return render_template("extractor.html")

@app.route("/logs/<niche>")
def view_logs(niche):
    log_file = f"{niche}_log.txt"
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            content = f.read()
    else:
        content = "Log file not found."
    return f"<pre style='white-space: pre-wrap; background: #111; color: #0f0; padding: 1rem;'>{content}</pre>"

@app.route("/results/<niche>")
def results(niche):
    csv_file = f"data/{niche}_scraped_companies.csv"
    email_file = f"data/{niche}_emails.csv"
    progress_file = f"progress_{niche}.json"

    results_data = ScrapedCompany.query.filter_by(niche=niche).all()
    print(f"Querying database for niche: {niche}")
    print(f"Found {len(results_data)} results.")

    progress = {"niche": niche, "current_stage": "Complete", "progress_detail": ""}
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as file:
            content = file.read().strip()
            if content:
                progress.update(json.loads(content))
            else:
                print(f"⚠️ Progress file {progress_file} is empty.")

    return render_template("results.html", results_data=results_data, progress=progress)
'''
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
'''
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
    app.run(host='0.0.0.0', port=5000, debug=True)

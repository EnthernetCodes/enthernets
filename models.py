# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ScrapedCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    niche = db.Column(db.String(100))
    email = db.Column(db.String(200))
    source_page = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ScrapedData {self.email}>"

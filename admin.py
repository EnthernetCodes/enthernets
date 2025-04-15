from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import db, ScrapedCompany

def setup_admin(app):
    admin = Admin(app, name="MailScraper Admin", template_mode="bootstrap4")
    admin.add_view(ModelView(ScrapedCompany, db.session))

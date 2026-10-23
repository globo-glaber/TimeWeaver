import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'timeweaver-dev-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///schedule.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
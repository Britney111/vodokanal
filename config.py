# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'vodokanal-rostov-secret-key-2024'

    # Railway даёт DATABASE_URL автоматически при добавлении PostgreSQL
    db_url = os.environ.get('DATABASE_URL') or \
        f"postgresql://postgres:220520@localhost:5432/vodokanal_db"

    # Railway иногда даёт postgres:// вместо postgresql:// — фиксим
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ITEMS_PER_PAGE = 15
    LOW_STOCK_THRESHOLD = 10


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

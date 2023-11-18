import os
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
class Config:
    SECRET_KEY = config('SECRET_KEY','secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL', default='postgresql+psycopg2://ydrdkqhr:m0bO1SspaNFE4KwyTFAadw9MmhSlPFlO@suleiman.db.elephantsql.com/ydrdkqhr')


class DevConfig(Config):
    DEBUG = config('DEBUG', cast=bool)
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL', default='postgresql+psycopg2://ydrdkqhr:m0bO1SspaNFE4KwyTFAadw9MmhSlPFlO@suleiman.db.elephantsql.com/ydrdkqhr')

class TestConfig(Config):
    pass

class ProdConfig(Config):
    pass

config_dict = {
    'development': DevConfig,
    'testing': TestConfig,
    'production': ProdConfig
}
import os
from decouple import config
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
class Config:
    SECRET_KEY = config('SECRET_KEY','secret')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_SECRET_KEY =config('JWT_SECRET_KEY')


class DevConfig(Config):
    DEBUG = config('DEBUG', cast=bool)
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL')

class TestConfig(Config):
    pass

class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = config('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = config('DEBUG', cast=bool)


config_dict = {
    'development': DevConfig,
    'testing': TestConfig,
    'production': ProdConfig
}
import os


class Config(object):
    DEBUG = False
    CSRF_ENABLED = True
    SECRET_KEY = 'this-really-needs-to-be-changed'
    API_URL = os.environ.get('API_URL', 'http://127.0.0.1:5001')
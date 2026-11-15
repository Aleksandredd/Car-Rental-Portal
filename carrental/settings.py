"""
Django settings for the Car Rental Portal.

All car/user data lives on an external REST API (see docs/API_NOTES.md).
Django only renders pages and keeps the login session, so the local
database holds nothing but the session table.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.getenv('SECRET_KEY', 'dev-only-insecure-key-change-me')
DEBUG = env_bool('DEBUG', False)
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# External API and third-party keys
API_BASE_URL = os.getenv('API_BASE_URL', 'https://rentcar.stepprojects.ge').rstrip('/')
API_TIMEOUT = 15  # seconds
MAPBOX_TOKEN = os.getenv('MAPBOX_TOKEN', '')

INSTALLED_APPS = [
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'carrental.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.current_user',
            ],
        },
    },
]

WSGI_APPLICATION = 'carrental.wsgi.application'

# Used only for the session table.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Sessions: the API token lasts one day, so the login session does too.
SESSION_COOKIE_AGE = 60 * 60 * 24
SESSION_COOKIE_HTTPONLY = True
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tbilisi'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Local copies of uploaded car photos (fallback when the API returns no image URL).
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Upload limits for the "Add car" form
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB per photo
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024

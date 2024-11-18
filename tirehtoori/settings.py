"""
Django settings for tirehtoori project.

Generated by 'django-admin startproject' using Django 4.2.16.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
if not (BASE_DIR / "manage.py").is_file():
    raise ImproperlyConfigured("BASE_DIR is not set correctly")

env = environ.Env(
    ADMIN_URL=(str, "admin"),
    ALLOWED_HOSTS=(list, []),
    DATABASE_URL=(str, "postgres:///tirehtoori-db"),
    DATABASE_PASSWORD=(str, ""),
    DJANGO_LOG_LEVEL=(str, "INFO"),
    DEBUG=(bool, False),
    ENABLE_REDIRECT_APP=(bool, False),
    ENABLE_ADMIN_APP=(bool, False),
    SECRET_KEY=(str, ""),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "development"),
    STATIC_URL=(str, "__static/"),
    STATIC_ROOT=(environ.Path(), BASE_DIR / "static"),
)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env("ALLOWED_HOSTS")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "%(asctime)s %(name)s %(levelname)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL"),
        },
    },
}

# Application definition

INSTALLED_APPS = [
    "redirect.apps.RedirectConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

if not env("ENABLE_ADMIN_APP"):
    INSTALLED_APPS.pop(INSTALLED_APPS.index("django.contrib.admin"))

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tirehtoori.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "tirehtoori.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {"default": env.db()}

if env("DATABASE_PASSWORD"):
    DATABASES["default"]["PASSWORD"] = env("DATABASE_PASSWORD")


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = env("STATIC_URL")
STATIC_ROOT = env("STATIC_ROOT")

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Enable Django Admin site
ENABLE_ADMIN_APP = env("ENABLE_ADMIN_APP")
ADMIN_URL = env("ADMIN_URL")

# Enable API
ENABLE_REDIRECT_APP = env("ENABLE_REDIRECT_APP")

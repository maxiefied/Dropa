"""Dropa settings.

Everything that differs between your laptop and the live site is read from
environment variables. On your laptop they come from a `.env` file (copy
`.env.example` to `.env`). On the live site, the host provides them.
"""
import os
from pathlib import Path

import dj_database_url
from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.environ.get(name)
    return int(value) if value and value.strip() else default


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ----- Core -----

DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "dev-only-insecure-key-do-not-use-online"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY is not set. On your laptop, copy .env.example to .env "
            "(it sets DEBUG=True). On the live site, set SECRET_KEY in the host's settings."
        )

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost" if DEBUG else "")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Render tells the app its own address.
RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")

if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS is empty. Set it to your site's address, for example "
        "ALLOWED_HOSTS=dropa.example.com"
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "marketplace",
    "orders",
    "payments",
    "riders",
    "aftersales",
    "payouts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.navigation",
            ],
        },
    },
]

# ----- Database: SQLite on your laptop, PostgreSQL on the live site -----

if os.environ.get("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(conn_max_age=600, conn_health_checks=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ----- Accounts -----

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----- Language and time -----

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# ----- Messages -----

MESSAGE_TAGS = {message_constants.ERROR: "danger"}

# ----- Static files -----

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ----- Uploaded files -----
# Public files (menu photos, rider photos shown on name-tag checks) and private
# files (ID documents, business documents, complaint photos) are kept apart.
# Private files are never served from a public address: each download goes
# through a view that checks who is asking (see config/private_files.py).

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR))
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
PRIVATE_MEDIA_ROOT = DATA_DIR / "private_media"

USE_S3_MEDIA = bool(os.environ.get("S3_PRIVATE_BUCKET"))

STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

if USE_S3_MEDIA:
    # Any S3-compatible service works (Cloudflare R2, Backblaze B2, AWS S3, ...).
    s3_common = {
        "access_key": os.environ.get("S3_ACCESS_KEY_ID"),
        "secret_key": os.environ.get("S3_SECRET_ACCESS_KEY"),
        "endpoint_url": os.environ.get("S3_ENDPOINT_URL") or None,
        "region_name": os.environ.get("S3_REGION") or None,
        "file_overwrite": False,
        "default_acl": None,
    }
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **s3_common,
            "bucket_name": os.environ.get("S3_PUBLIC_BUCKET"),
            "custom_domain": os.environ.get("S3_PUBLIC_CUSTOM_DOMAIN") or None,
            "querystring_auth": False,
        },
    }
    STORAGES["private"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **s3_common,
            "bucket_name": os.environ.get("S3_PRIVATE_BUCKET"),
            "querystring_auth": True,  # links are signed...
            "querystring_expire": 300,  # ...and stop working after 5 minutes
        },
    }
else:
    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(MEDIA_ROOT), "base_url": MEDIA_URL},
    }
    STORAGES["private"] = {
        "BACKEND": "config.storage.PrivateFileSystemStorage",
        "OPTIONS": {"location": str(PRIVATE_MEDIA_ROOT)},
    }

# ----- Security on the live site -----

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Leave at 0 until you've confirmed HTTPS works everywhere, then raise it
    # (31536000 is one year). Browsers remember this setting.
    SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0)

# ----- Logging: print to the console so the host's log page shows errors -----

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ----- Dropa business rules (all adjustable without code changes) -----

DROPA_SIMULATE_PAYMENTS = env_bool("DROPA_SIMULATE_PAYMENTS", True)
DROPA_SIMULATED_PAYOUT_RESULT = os.environ.get("DROPA_SIMULATED_PAYOUT_RESULT", "success")
DROPA_PAYMENT_WINDOW_MINUTES = env_int("DROPA_PAYMENT_WINDOW_MINUTES", 10)
DROPA_VENDOR_RESPONSE_MINUTES = env_int("DROPA_VENDOR_RESPONSE_MINUTES", 5)
DROPA_PAYMENT_COOLDOWN_SECONDS = env_int("DROPA_PAYMENT_COOLDOWN_SECONDS", 60)
DROPA_COMPLAINT_WINDOW_HOURS = env_int("DROPA_COMPLAINT_WINDOW_HOURS", 24)
DROPA_MAX_RIDER_ACTIVE_ORDERS = env_int("DROPA_MAX_RIDER_ACTIVE_ORDERS", 3)
DROPA_MAX_CODE_ATTEMPTS = env_int("DROPA_MAX_CODE_ATTEMPTS", 5)
DROPA_RIDER_PAYOUT_HOUR = env_int("DROPA_RIDER_PAYOUT_HOUR", 18)

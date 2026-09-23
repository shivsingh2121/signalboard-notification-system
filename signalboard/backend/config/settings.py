"""Django settings for the Signalboard notification backend."""
import os
import dj_database_url
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DEBUG", False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "accounts",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------- Database ----------------
# Pick ONE of these in .env (checked in this order):
#   1) DATABASE_URL=mysql://user:pass@host:3306/dbname   (or postgresql://...)
#   2) DB_ENGINE=mysql + DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
#      (easiest for MySQL: passwords with @ # : / need no escaping)
#   3) nothing -> local SQLite file (db.sqlite3)
# DB_SSL=True turns on TLS for hosted MySQL (TiDB Cloud, Aiven...).
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_ENGINE = os.getenv("DB_ENGINE", "").strip().lower()


def _mysql_options():
    opts = {
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    }
    if env_bool("DB_SSL", False):
        import certifi  # installed with requests

        opts["ssl"] = {"ca": os.getenv("DB_SSL_CA", "").strip() or certifi.where()}
    return opts


if DATABASE_URL:
    _db = dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)
    if _db["ENGINE"].endswith("mysql"):
        _db["OPTIONS"] = _mysql_options()  # drop URL query params PyMySQL doesn't understand
    DATABASES = {"default": _db}
elif DB_ENGINE in ("mysql", "mariadb"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "signalboard"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": _mysql_options(),
            "CONN_MAX_AGE": 600,
            "CONN_HEALTH_CHECKS": True,
            "TEST": {"CHARSET": "utf8mb4", "COLLATION": "utf8mb4_unicode_ci"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS: the Vercel frontend talks to this API with a bearer token ---
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
CORS_ALLOWED_ORIGINS = list({FRONTEND_URL, *env_list("CORS_EXTRA_ORIGINS")})
if DEBUG:  # local dev: Vite dev (5173) and preview (4173) on either hostname
    CORS_ALLOWED_ORIGINS += [f"http://{h}:{p}" for h in ("localhost", "127.0.0.1") for p in (5173, 4173)]
if env_bool("CORS_ALLOW_VERCEL_PREVIEWS", True):
    CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.vercel\.app$"]
CSRF_TRUSTED_ORIGINS = [o for o in CORS_ALLOWED_ORIGINS if o.startswith("http")]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.ActivityTokenAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": None,
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# --- Notification providers (all sandbox / free tier) ---
SITE_NAME = os.getenv("SITE_NAME", "Signalboard")

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")

# postmark | brevo | resend | console
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "postmark").lower()
POSTMARK_TOKEN = os.getenv("POSTMARKAPP_TOKEN", "")
POSTMARK_FROM_EMAIL = os.getenv("POSTMARK_FROM_EMAIL", "")
POSTMARK_MESSAGE_STREAM = os.getenv("POSTMARK_MESSAGE_STREAM", "outbound")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "")

ONESIGNAL_APP_ID = os.getenv("ONESIGNAL_APP_ID", "")
ONESIGNAL_REST_API_KEY = os.getenv("ONESIGNAL_REST_API_KEY", "")

# Send notifications in a background thread so login/logout responses stay fast.
NOTIFY_ASYNC = env_bool("NOTIFY_ASYNC", True)
# Shared secret for the cron endpoint (Render Cron Job / external pinger)
CRON_SECRET = os.getenv("CRON_SECRET", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
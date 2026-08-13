# exam_site/settings.py

from pathlib import Path
import os


# ==========================================================
# BASE DIRECTORY
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================================
# SECURITY
# ==========================================================

# Local fallback is only for development.
# On the VPS, set a strong SECRET_KEY environment variable.
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "dev-secret-change-this-in-production",
)


# ==========================================================
# ENVIRONMENT
# ==========================================================

# LOCAL:
#   DEBUG=True by default
#
# PRODUCTION VPS:
#   Set DEBUG=False

DEBUG = os.environ.get("DEBUG", "True").lower() == "true"


# ==========================================================
# ALLOWED HOSTS
# ==========================================================

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "idaare.com,www.idaare.com,127.0.0.1,localhost",
).split(",")

ALLOWED_HOSTS = [
    host.strip()
    for host in ALLOWED_HOSTS
    if host.strip()
]


# ==========================================================
# INSTALLED APPS
# ==========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Project apps
    "exams.apps.ExamsConfig",
    "blog.apps.BlogConfig",
    "videos",

    # Third-party apps
    "django_ckeditor_5",
]


# ==========================================================
# MIDDLEWARE
# ==========================================================

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


# ==========================================================
# URL CONFIGURATION
# ==========================================================

ROOT_URLCONF = "exam_site.urls"


# ==========================================================
# TEMPLATES
# ==========================================================

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


# ==========================================================
# WSGI
# ==========================================================

WSGI_APPLICATION = "exam_site.wsgi.application"


# ==========================================================
# DATABASE
# ==========================================================
#
# LOCAL COMPUTER:
#   Uses SQLite automatically.
#
# VPS / PRODUCTION:
#   Set USE_SQLITE=False
#
# Example production variables:
#
#   USE_SQLITE=False
#   DB_NAME=exam_db
#   DB_USER=exam_user
#   DB_PASSWORD=your_password
#   DB_HOST=127.0.0.1
#   DB_PORT=5432
#
# ==========================================================

USE_SQLITE = os.environ.get(
    "USE_SQLITE",
    "True",
).lower() == "true"


if USE_SQLITE:

    # ------------------------------------------------------
    # LOCAL DEVELOPMENT DATABASE
    # ------------------------------------------------------

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

else:

    # ------------------------------------------------------
    # PRODUCTION POSTGRESQL DATABASE
    # ------------------------------------------------------

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",

            "NAME": os.environ.get(
                "DB_NAME",
                "exam_db",
            ),

            "USER": os.environ.get(
                "DB_USER",
                "exam_user",
            ),

            "PASSWORD": os.environ.get(
                "DB_PASSWORD",
                "",
            ),

            "HOST": os.environ.get(
                "DB_HOST",
                "127.0.0.1",
            ),

            "PORT": os.environ.get(
                "DB_PORT",
                "5432",
            ),
        }
    }


# ==========================================================
# PASSWORD VALIDATION
# ==========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==========================================================
# CSRF
# ==========================================================

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "https://idaare.com,https://www.idaare.com",
).split(",")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in CSRF_TRUSTED_ORIGINS
    if origin.strip()
]


# ==========================================================
# PRODUCTION SECURITY
# ==========================================================
#
# These settings are enabled automatically when:
#
# DEBUG=False
#
# ==========================================================

if not DEBUG:

    CSRF_COOKIE_SECURE = True

    SESSION_COOKIE_SECURE = True

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


# ==========================================================
# INTERNATIONALIZATION
# ==========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Nairobi"

USE_I18N = True

USE_TZ = True


# ==========================================================
# STATIC FILES
# ==========================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = (
    "whitenoise.storage.CompressedManifestStaticFilesStorage"
)


# ==========================================================
# MEDIA FILES
# ==========================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ==========================================================
# CKEDITOR 5
# ==========================================================

CKEDITOR_5_CONFIGS = {
    "default": {

        "toolbar": [
            "heading",
            "|",

            "bold",
            "italic",
            "underline",

            "|",

            "bulletedList",
            "numberedList",

            "|",

            "insertTable",
            "imageUpload",

            "|",

            "undo",
            "redo",
        ],

        "table": {
            "contentToolbar": [
                "tableColumn",
                "tableRow",
                "mergeTableCells",
                "tableCellProperties",
                "tableProperties",
            ]
        },

        "image": {
            "toolbar": [
                "imageTextAlternative",
                "imageStyle:alignLeft",
                "imageStyle:alignCenter",
                "imageStyle:alignRight",
            ]
        },
    }
}


# ==========================================================
# DEFAULT PRIMARY KEY
# ==========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================================
# LOGIN / LOGOUT
# ==========================================================

LOGIN_REDIRECT_URL = "/after-login/"

LOGOUT_REDIRECT_URL = "/"


# ==========================================================
# EMAIL
# ==========================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"

EMAIL_PORT = 587

EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.environ.get(
    "EMAIL_USER",
    "sahassan39@gmail.com",
)

EMAIL_HOST_PASSWORD = os.environ.get(
    "EMAIL_PASSWORD",
    "",
)

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ==========================================================
# FILE UPLOAD PERMISSIONS
# ==========================================================

FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755
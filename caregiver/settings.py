from pathlib import Path
import environ

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent  # folder with manage.py

# ---- Environment (.env) ----
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])

# ---- Core Django ----
ROOT_URLCONF = "caregiver.urls"
WSGI_APPLICATION = "caregiver.wsgi.application"
ASGI_APPLICATION = "caregiver.asgi.application"

# ---- Database (PostgreSQL via django-tenants backend) ----
# IMPORTANT: Use the django-tenants engine so the connection has `schema_name`
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

# ---- django-tenants config ----
PUBLIC_SCHEMA_NAME = "public"
TENANT_MODEL = "tenants.Client"            # app_label.ModelName
TENANT_DOMAIN_MODEL = "tenants.Domain"     # app_label.ModelName
DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

# Apps that live in the public schema (shared across all tenants)
SHARED_APPS = [
    "django_tenants",          # must be first
    "tenants",                 # where Client + Domain models live
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.admin",
]

# Apps installed inside each tenant schema (per-tenant data)
TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # add your tenant apps later, e.g. "organizations"
]

# Build INSTALLED_APPS (dedupe while preserving order)
INSTALLED_APPS = list(dict.fromkeys(SHARED_APPS + TENANT_APPS))

# ---- Middleware (tenant middleware must be very early) ----
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---- Templates ----
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# ---- Password validation ----
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Internationalization / Time ----
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

# ---- Static / Media ----
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

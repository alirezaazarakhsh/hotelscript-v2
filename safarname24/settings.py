from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# ENVIRONMENT
# ======================
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ======================
# BASIC SETTINGS
# ======================
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = [
    host.strip()
    for host in env("DJANGO_ALLOWED_HOSTS", default="").split(",")
    if host.strip()
]

ALLOWED_HOSTS.extend([
    "localhost",
    "127.0.0.1",
    "91.107.148.119",
])

ALLOWED_HOSTS = list(set(ALLOWED_HOSTS))

# ======================
# INSTALLED APPS
# ======================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "corsheaders",
    "rest_framework",
    "drf_yasg",
    "django_jalali",

    # TinyMCE Self‑Hosted
    "tinymce",

    # Apps
    "site_config",
    "coming_soon",
    "packages",
    "home_config",
    "hostpage",
    "sevinapp",
    "HostPageManager",
    "contact_us",
    "about_us",
    "ruls",
    "footer",
    "settingwhmcs",
]

# ======================
# MIDDLEWARE
# ======================
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

# ======================
# URLS & WSGI
# ======================
ROOT_URLCONF = "sevinapp.urls"
WSGI_APPLICATION = "sevinapp.wsgi.application"

# ======================
# TEMPLATES
# ======================
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

# ======================
# DATABASE
# ======================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

# ======================
# PASSWORD VALIDATORS
# ======================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ======================
# INTERNATIONALIZATION
# ======================
LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"

USE_I18N = True
USE_TZ = True

# ======================
# STATIC FILES
# ======================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [
    BASE_DIR / "staticfiles",
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ======================
# MEDIA FILES
# ======================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================
# DEFAULT AUTO FIELD
# ======================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ======================
# CORS
# ======================
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in env("CORS_ALLOWED_ORIGINS", default="").split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ======================
# CSRF
# ======================
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env("CSRF_TRUSTED_ORIGINS", default="").split(",")
    if origin.strip()
]

# ======================
# SECURITY
# ======================
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"

# ======================
# TINYMCE SELF‑HOSTED CONFIG
# ======================

TINYMCE_DEFAULT_CONFIG = {
    "height": 600,
    "plugins": (
        "advlist anchor autolink charmap code fullscreen help image "
        "insertdatetime link lists media preview searchreplace table "
        "visualblocks wordcount textcolor"
    ),
    "toolbar": (
        "undo redo | styleselect | bold italic underline | forecolor backcolor | "
        "fontsize | alignleft aligncenter alignright alignjustify | "
        "bullist numlist outdent indent | link image media | table | "
        "charmap insertdatetime anchor | searchreplace code preview | fullscreen help"
    ),
    "menubar": "file edit view insert format tools table help",
    "extended_valid_elements": (
        "script[src|type], iframe[src|width|height|frameborder|allowfullscreen], "
        "video[controls|preload|width|height|src|poster|autoplay|muted|loop]"
    ),
    "content_style": "body { font-family: Arial, sans-serif; font-size: 14px }",
    "automatic_uploads": True,
    "file_picker_types": "image media",
}

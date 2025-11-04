import os
import environ
from pathlib import Path
from datetime import timedelta
import sys
import re

env = environ.Env(
    DB_ENGINE=(str, 'django.db.backends.postgresql'),
    DB_NAME=(str, 'safarname24'),
    DB_USER=(str, 'postgres'),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, 'localhost'),
    DB_PORT=(str, '5432'),
)

environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', "django-insecure-t&tg@de!xd4nbb1ci4(hl9#msk=3=^_^w0h((@m1&k=k8axhnu")
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "safarnameh24.com",
    "www.safarnameh24.com",
    "cps.safarnameh24.com",
    "www.cps.safarnameh24.com",
    "91.107.134.107",
]

# لیست اصلی origins
CSRF_TRUSTED_ORIGINS = [
    "http://safarnameh24.com",
    "https://safarnameh24.com",
    "http://www.safarnameh24.com",
    "https://www.safarnameh24.com",
    "http://cps.safarnameh24.com",
    "https://cps.safarnameh24.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('STATIC_ROOT', os.path.join(BASE_DIR, 'staticfiles'))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jalali',
    'colorfield',
    'ckeditor',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'authentication',
    'config',
    'contact',
    'blog',
    'reservation',
    'finance',
    'bashgah_moshtarian',
    'drf_yasg',
    'corsheaders',
    'safarname24',
    'icons',
    'setting_sms',
    'notification',
    'setting_payment',
    'favorite',
    'tinymce',
    'channels',
    'nested_admin',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # باید اول باشد
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG and 'test' not in sys.argv:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

ROOT_URLCONF = 'safarname24.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'safarname24.wsgi.application'
ASGI_APPLICATION = 'safarname24.asgi.application'

# تنظیمات Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.environ.get('REDIS_HOST', 'redis'), int(os.environ.get('REDIS_PORT', 6379)))],
        },
    },
}

# تنظیمات Celery
CELERY_BROKER_URL = f"redis://{os.environ.get('REDIS_HOST', 'redis')}:{os.environ.get('REDIS_PORT', 6379)}/0"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tehran'

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', env('DB_ENGINE')),
        'NAME': os.environ.get('DB_NAME', env('DB_NAME')),
        'USER': os.environ.get('DB_USER', env('DB_USER')),
        'PASSWORD': os.environ.get('DB_PASSWORD', env('DB_PASSWORD')),
        'HOST': os.environ.get('DB_HOST', env('DB_HOST')),
        'PORT': os.environ.get('DB_PORT', env('DB_PORT')),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'safarname24.swagger_schemas.CustomSwaggerAutoSchema',
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

AUTHENTICATION_BACKENDS = (
    'authentication.backends.UserAuthBackend',
    'authentication.backends.AdminAuthBackend',
)

AUTH_USER_MODEL = "authentication.BaseUser"
OTP_VALID_TIME = 1

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'safarname24.pagination.Paginator',
    'PAGE_SIZE': 18,
}

if not DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'safarname24.renderers.ResponseRenderer',
    )

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'SIGNING_KEY': SECRET_KEY,
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    "TOKEN_OBTAIN_SERIALIZER": "authentication.serializers.UserTokenObtainPairSerializer",
}

INTERNAL_IPS = ['127.0.0.1']

# ====================== CORS SETTINGS ======================
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = False  # فقط در توسعه = True کنید

# لیست اصلی origins
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://safarnameh24.com",
    "https://safarnameh24.com",
    "http://www.safarnameh24.com",
    "https://www.safarnameh24.com",
    "http://cps.safarnameh24.com",
    "https://cps.safarnameh24.com",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# افزودن دامنه Google User Content (برای توسعه با Google SCF)
# این برای محیط توسعه با Google App Engine یا Firebase Hosting ضروری است
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.scf\.usercontent\.goog$",
    r"^https://.*\.googleusercontent\.com$",
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# فقط در محیط توسعه (اختیاری)
if DEBUG:
    CORS_ORIGIN_ALLOW_ALL = True  # فقط برای تست لوکال
# =========================================================

JALALI_DATE_DEFAULTS = {
    'Strftime': {
        'date': '%Y/%m/%d',
    },
    'Static': {
        'js': [
            'admin/js/django_jalali.min.js',
        ],
        'css': {
            'all': ['admin/css/django_jalali.min.css']
        },
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

ZARINPAL_CONFIG = {
    'SANDBOX': False,
    'CALLBACK_URL': 'https://safarnameh24.com/gateways/verify/',
}

TINYMCE_DEFAULT_CONFIG = {
    "height": 600,
    "plugins": "advlist anchor autolink charmap code fullscreen help image insertdatetime link lists media preview searchreplace table visualblocks wordcount",
    "toolbar": "undo redo | styleselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image media | table | charmap insertdatetime anchor | searchreplace code preview | fullscreen help",
    "menubar": "file edit view insert format tools table help",
    "extended_valid_elements": "script[src|type], iframe[src|width|height|frameborder|allowfullscreen], video[controls|preload|width|height|src|poster|autoplay|muted|loop]",
    "content_style": "body { font-family: Arial, sans-serif; font-size: 14px }",
}

# تنظیمات محیط
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')

if ENVIRONMENT == 'local':
    CALLBACK_REDIRECT_BASE_URL = 'http://localhost:3000'
else:
    CALLBACK_REDIRECT_BASE_URL = 'https://safarnameh24.com'

ZARINPAL_REQUEST_URL = 'https://payment.zarinpal.com/pg/v4/payment/request.json'
ZARINPAL_PAYMENT_URL = 'https://payment.zarinpal.com/pg/StartPay'
ZARINPAL_VERIFY_URL = 'https://payment.zarinpal.com/pg/v4/payment/verify.json'

IRANIANGATEWAY_REFERER = 'https://safarnameh24.com'
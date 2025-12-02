import os
import environ
from pathlib import Path
from datetime import timedelta
import sys

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

SECRET_KEY = "django-insecure-t&tg@de!xd4nbb1ci4(hl9#msk=3=^_^w0h((@m1&k=k8axhnu"
DEBUG = True

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "safarnameh24.com",
    "www.safarnameh24.com",
    "cps.safarnameh24.com",
    "www.cps.safarnameh24.com",
    "chatbot.safarnameh24.com",
    "www.chatbot.safarnameh24.com",
    "91.107.134.107",
]

CSRF_TRUSTED_ORIGINS = [
    "http://safarnameh24.com",
    "https://safarnameh24.com",
    "http://www.safarnameh24.com",
    "https://www.safarnameh24.com",
    "http://cps.safarnameh24.com",
    "https://cps.safarnameh24.com",
    "http://chatbot.safarnameh24.com",
    "https://chatbot.safarnameh24.com",
    "http://www.chatbot.safarnameh24.com",
    "https://www.chatbot.safarnameh24.com",
    ]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_jalali',
    'colorfield',
    'tinymce',
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
    'settingchatbot',
    'chat_api',
    
    'channels',
    'nested_admin',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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
            "hosts": [("redis" if os.environ.get('REDIS_HOST') else "127.0.0.1", 6379)],
        },
    },
}

# Cache backend: prefer Redis so cache keys (used by websocket timer) survive page refresh
# If REDIS_HOST is set in env (e.g. in Docker), use that host; otherwise default to localhost
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ.get('REDIS_HOST', '127.0.0.1')}:6379/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# تنظیمات Celery
CELERY_BROKER_URL = 'redis://redis:6379/0' if os.environ.get('REDIS_HOST') else 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0' if os.environ.get('REDIS_HOST') else 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tehran'

# تنظیمات Celery Beat برای اجرای تسک‌های زمان‌بندی شده
CELERY_BEAT_SCHEDULE = {
    'check-expired-reservations': {
        'task': 'reservation.tasks.check_and_reject_expired_reservations',
        'schedule': 60.0,  # هر 60 ثانیه (1 دقیقه)
    },
}

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST') if not os.environ.get('DB_HOST') else os.environ.get('DB_HOST'),
        'PORT': env('DB_PORT'),
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
        'authentication.authentication.CookieJWTAuthentication',
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
    "http://chatbot.safarnameh24.com",
    "https://chatbot.safarnameh24.com",
    "http://www.chatbot.safarnameh24.com",
    "https://www.chatbot.safarnameh24.com",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = False
CORS_ALLOW_HEADERS = [
    'content-type',
    'authorization',
    'x-requested-with',
]

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
            'filename': 'debug.log',
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




# safarnameh24/settings.py

# مشخص کردن محیط (local یا production)
ENVIRONMENT = 'production'  # برای محیط لوکال (برای تست لوکال این را فعال کنید)
# ENVIRONMENT = 'production'  # برای محیط پروداکشن

# تنظیم URL پایه برای ریدایرکت callback
if ENVIRONMENT == 'local':
    CALLBACK_REDIRECT_BASE_URL = 'http://localhost:3000'
else:
    CALLBACK_REDIRECT_BASE_URL = 'https://safarnameh24.com'

#  تنظیمات درگاه زرین‌پال (برای پروداکشن - کامنت شده)
ZARINPAL_REQUEST_URL = 'https://payment.zarinpal.com/pg/v4/payment/request.json'
ZARINPAL_PAYMENT_URL = 'https://payment.zarinpal.com/pg/StartPay'
ZARINPAL_VERIFY_URL = 'https://payment.zarinpal.com/pg/v4/payment/verify.json'

# تنظیمات درگاه ایران‌درگاه
IRANIANGATEWAY_REFERER = 'https://safarnameh24.com'

# تنظیمات درگاه زرین‌پال (فقط سندباکس)
# ZARINPAL_SANDBOX_REQUEST_URL = 'https://sandbox.zarinpal.com/pg/v4/payment/request.json'
# ZARINPAL_SANDBOX_PAYMENT_URL = 'https://sandbox.zarinpal.com/pg/StartPay'
# ZARINPAL_SANDBOX_VERIFY_URL = 'https://sandbox.zarinpal.com/pg/v4/payment/verify.json'
import os
import environ
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab
import sys

env = environ.Env(
    DB_ENGINE=(str, 'django.db.backends.postgresql'),
    DB_NAME=(str, 'zarvantrip'),
    DB_USER=(str, 'postgres'),
    DB_PASSWORD=(str, ''),
    DB_HOST=(str, 'localhost'),
    DB_PORT=(str, '5432'),
)

environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

# خواندن SECRET_KEY از متغیر محیطی با مقدار پیش‌فرض قبلی
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    "django-insecure-t&tg@de!xd4nbb1ci4(hl9#msk=3=^_^w0h((@m1&k=k8axhnu"
)

# خواندن DEBUG از متغیر محیطی داکر (پیش‌فرض True)
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() in ('true', '1')

# خواندن ALLOWED_HOSTS از محیط Docker یا استفاده از لیست پیش‌فرض
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS = [host.strip() for host in os.environ.get('ALLOWED_HOSTS').split(',')]
else:
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
        "zarvantrip.com",
        "www.zarvantrip.com",
        "cps.zarvantrip.com",
        "www.cps.zarvantrip.com",
        "chatbot.zarvantrip.com",
        "www.chatbot.zarvantrip.com",
        "37.152.181.133",
    ]

# خواندن CSRF_TRUSTED_ORIGINS از متغیر محیطی داکر یا استفاده از لیست پیش‌فرض
if os.environ.get('CSRF_TRUSTED_ORIGINS'):
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.environ.get('CSRF_TRUSTED_ORIGINS').split(',')]
else:
    CSRF_TRUSTED_ORIGINS = [
        "http://zarvantrip.com",
        "https://zarvantrip.com",
        "http://www.zarvantrip.com",
        "https://www.zarvantrip.com",
        "http://cps.zarvantrip.com",
        "https://cps.zarvantrip.com",
        "http://chatbot.zarvantrip.com",
        "https://chatbot.zarvantrip.com",
        "http://www.chatbot.zarvantrip.com",
        "https://www.chatbot.zarvantrip.com",
        "http://37.152.181.133",
        "http://37.152.181.133:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

INSTALLED_APPS = [
    'daphne',  # برای Channels 4 حتماً باید در سطر اول باشد
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
    
    # Django OTP apps
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    
    'authentication',
    'config',
    'contact',
    'blog',
    'reservation',
    'finance',
    'bashgah_moshtarian',
    'drf_yasg',
    'corsheaders',
    'zarvantrip',
    'icons',
    'setting_sms',
    'notification',
    'setting_payment',
    'favorite',
    'settingchatbot',
    'chat_api',
    'user_subscription_settings',
    'hotel_backup',
    
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
    'django_otp.middleware.OTPMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if DEBUG and 'test' not in sys.argv:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

ROOT_URLCONF = 'zarvantrip.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'zarvantrip.wsgi.application'
ASGI_APPLICATION = 'zarvantrip.asgi.application'

# تنظیمات Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(os.environ.get('REDIS_HOST', '127.0.0.1'), int(os.environ.get('REDIS_PORT', 6379)))],
        },
    },
}

# Cache backend
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.environ.get('REDIS_HOST', '127.0.0.1')}:{os.environ.get('REDIS_PORT', '6379')}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# تنظیمات Celery
_REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
_REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
CELERY_BROKER_URL = f'redis://{_REDIS_HOST}:{_REDIS_PORT}/0'
CELERY_RESULT_BACKEND = f'redis://{_REDIS_HOST}:{_REDIS_PORT}/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Tehran'

# زمان‌بندی تسک‌های Celery Beat (اصلاح‌شده، ایمن و کامل)
CELERY_BEAT_SCHEDULE = {
    'check-expired-reservations': {
        'task': 'reservation.tasks.check_and_reject_expired_reservations',
        'schedule': 900.0,  # هر ۱۵ دقیقه یک‌بار
    },
    'cancel-unpaid-confirmed-reservations': {
        'task': 'setting_payment.views.cancel_unpaid_reservations',
        'schedule': 300.0,  # هر ۵ دقیقه یک‌بار
    },
    'check-pending-snapptrip-inquiries': {
        'task': 'reservation.tasks.check_pending_snapptrip_inquiries_task',
        'schedule': 120.0,  # هر ۲ دقیقه یک‌بار (استعلام زنده رزروهای مسافران از اسنپ)
    },
    'auto-sync-snapptrip-prices-every-2-hours': {
        'task': 'reservation.tasks.auto_sync_snapptrip_prices_task',
        'schedule': 7200.0,  # هر ۲ ساعت یک‌بار (بروزرسانی خودکار قیمت و تقویم هتل‌های فعال)
    },
    'auto-sync-snapptrip-directory-weekly': {
        'task': 'reservation.tasks.auto_sync_snapptrip_directory_task',
        'schedule': crontab(minute=0, hour=3, day_of_week='fri'),  # جمعه‌ها ساعت ۳:۰۰ صبح (بروزرسانی کل بانک اطلاعاتی هتل‌های کشور)
    },
}

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST') or env('DB_HOST'),
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
    'DEFAULT_AUTO_SCHEMA_CLASS': 'zarvantrip.swagger_schemas.CustomSwaggerAutoSchema',
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

LOGIN_URL = 'admin:login'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/admin/'
TWO_FACTOR_PATCH_ADMIN = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'authentication.authentication.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'zarvantrip.pagination.Paginator',
    'PAGE_SIZE': 18,
}

if not DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'zarvantrip.renderers.ResponseRenderer',
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

# ==================== CORS ====================
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://zarvantrip.com",
    "https://zarvantrip.com",
    "http://www.zarvantrip.com",
    "https://www.zarvantrip.com",
    "http://cps.zarvantrip.com",
    "https://cps.zarvantrip.com",
    "http://chatbot.zarvantrip.com",
    "https://chatbot.zarvantrip.com",
    "http://www.chatbot.zarvantrip.com",
    "https://www.chatbot.zarvantrip.com",
    "http://addmins.zarvantrip.com",
    "https://addmins.zarvantrip.com",
    "http://37.152.181.133",
    "http://37.152.181.133:8000",
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_EXPOSE_HEADERS = [
    "Content-Type",
    "X-CSRFToken",
]

CORS_PREFLIGHT_MAX_AGE = 86400

# ==================== بقیه تنظیمات ====================

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
    'CALLBACK_URL': 'https://zarvantrip.com/gateways/verify/',
}

TINYMCE_DEFAULT_CONFIG = {
    "height": 600,
    "plugins": "advlist anchor autolink charmap code fullscreen help image insertdatetime link lists media preview searchreplace table visualblocks wordcount textcolor",
    "toolbar": "undo redo | styleselect | bold italic underline | forecolor backcolor | fontsize | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image media | table | charmap insertdatetime anchor | searchreplace code preview | fullscreen help",
    "menubar": "file edit view insert format tools table help",
    "extended_valid_elements": "script[src|type], iframe[src|width|height|frameborder|allowfullscreen], video[controls|preload|width|height|src|poster|autoplay|muted|loop]",
    "content_style": "body { font-family: Arial, sans-serif; font-size: 14px }",
    "images_upload_url": "/api/v1/auth/tinymce/upload/",
    "automatic_uploads": True,
    "file_picker_types": "image media",
}

# مشخص کردن محیط
ENVIRONMENT = 'production'  

# تنظیم URL پایه برای ریدایرکت callback
if ENVIRONMENT == 'local':
    CALLBACK_REDIRECT_BASE_URL = 'http://localhost:3000'
else:
    CALLBACK_REDIRECT_BASE_URL = 'https://zarvantrip.com'

# تنظیمات درگاه زرین‌پال
ZARINPAL_REQUEST_URL = 'https://payment.zarinpal.com/pg/v4/payment/request.json'
ZARINPAL_PAYMENT_URL = 'https://payment.zarinpal.com/pg/StartPay'
ZARINPAL_VERIFY_URL = 'https://payment.zarinpal.com/pg/v4/payment/verify.json'

# تنظیمات درگاه ایران‌درگاه
IRANIANGATEWAY_REFERER = 'https://zarvantrip.com'
APPEND_SLASH = True
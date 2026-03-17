
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-i#o#u(#l56e6wi=0a==d@*umjwt7&pr*v4ov8^s3m4fb-4bfm$'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "rest_framework",
    "exams",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware", 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "django.middleware.locale.LocaleMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://192.0.4.119:3000",
]


ROOT_URLCONF = 'config.urls'

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_USER_MODEL = "users.User"

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'testing',       # siz yaratgan DB nomi
        'USER': 'postgres',
        'PASSWORD': 'qazXSW12',  # yangi parol
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
UNFOLD = {
    "SITE_TITLE": "Testing Admin",
    "SITE_HEADER": "Testing Platform",
    "SITE_SUBHEADER": "Boshqaruv paneli",
    "STYLES": [
        "css/unfold_fix.css",
    ],
    "SIDEBAR": {
        "navigation": [
            {
                "title": "Imtihonlar",
                "items": [
                    {
                        "title": "Testlar",
                        "icon": "quiz",
                        "link": "/admin/exams/test/",
                    },
                    {
                        "title": "Savollar banki",
                        "icon": "help",
                        "link": "/admin/exams/question/",
                    },
                    {
                        "title": "Test qoidalari",
                        "icon": "rule",
                        "link": "/admin/exams/testrule/",
                    },
                    {
                        "title": "Urinishlar",
                        "icon": "fact_check",
                        "link": "/admin/exams/attempt/",
                    },
                    {
                        "title": "Urinish javoblari",
                        "icon": "task_alt",
                        "link": "/admin/exams/attemptanswer/",
                    },
                    {
                        "title": "Urinish qo'shish",
                        "icon": "task_alt",
                        "link": "/admin/exams/attemptpolicy/",
                    },
                ],
            },
            {
                "title": "Foydalanuvchilar",
                "items": [
                    {
                        "title": "Foydalanuvchilar",
                        "icon": "group",
                        "link": "/admin/users/user/",
                    },
                    {
                        "title": "Bo‘limlar",
                        "icon": "apartment",
                        "link": "/admin/users/department/",
                    },
                    {
                        "title": "Filiallar",
                        "icon": "business",
                        "link": "/admin/users/branch/",
                    },
                ],
            },
            {
                "title": "Sozlamalar",
                "items": [
                    {
                        "title": "Guruhlar",
                        "icon": "security",
                        "link": "/admin/auth/group/",
                    },
                ],
            },
        ],
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=2),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'uz'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/



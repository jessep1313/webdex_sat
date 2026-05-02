import os
from pathlib import Path
import environ

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Aquí agregaremos nuestras apps después
    'core',
    'empresas',
    'usuarios',
    'fiel',
    'cfdi',
    'proveedores',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'

# Base de datos central
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_CENTRAL_NAME'),
        'USER': env('DB_CENTRAL_USER'),
        'PASSWORD': env('DB_CENTRAL_PASSWORD'),
        'HOST': env('DB_CENTRAL_HOST'),
        'PORT': env('DB_CENTRAL_PORT'),
    }
}

AUTH_PASSWORD_VALIDATORS = [...]

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_ENGINE = 'django.contrib.sessions.backends.file'

# Al final del archivo, agregar:
LOGIN_URL = '/'

# Duración de la sesión en segundos (30 minutos = 1800 segundos)
SESSION_COOKIE_AGE = 1800

# Renovar la cookie en cada petición (reinicia el contador de tiempo)
SESSION_SAVE_EVERY_REQUEST = True

# Opcional: evitar que la sesión expire al cerrar el navegador (false = la sesión dura SESSION_COOKIE_AGE aunque cierres el navegador)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

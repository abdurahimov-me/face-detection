from .base import *  # noqa

###################################################################
# General
###################################################################

DEBUG = True

###################################################################
# Django security
###################################################################

"""
IF YOU WANT SET CSRF_TRUSTED_ORIGINS = ["*"] THEN YOU SHOULD SET:
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
"""

CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = [
    "https://api.hujjat24.uz",
    "https://demo-api.hujjat24.uz"
]

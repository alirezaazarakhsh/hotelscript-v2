# utils.py
import string
from django.utils.crypto import get_random_string

def generate_otp_code(length=4, allowed_chars=string.digits):
    return get_random_string(length=length, allowed_chars=allowed_chars)

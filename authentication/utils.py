import string
from django.utils.crypto import get_random_string

def generate_otp_code(length=6, allowed_chars=string.digits):
    return get_random_string(length=length, allowed_chars=allowed_chars)

# TODO: send sms based on panel settings
def send_otp_code(code, to):
    print(code)

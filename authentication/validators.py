from django.core.exceptions import ValidationError
import re

def validate_phone_number(value):
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError('شماره موبایل باید به فرمت 09xxxxxxxxx باشد')

def validate_national_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد ملی باید 10 رقمی باشد')

def validate_postal_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد پستی باید 10 رقمی باشد')

def validate_file_size(value):
    max_file_size = 25 * 1024 * 1024
    if value.size > max_file_size:
        raise ValidationError(f"حداکثر حجم فایل آپلودی، {max_file_size / (1024 * 1024)} مگابایت است.")
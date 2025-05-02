from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
import re

def validate_phone_number(value):
    if not re.match(r'^09\d{9}$', value):
        raise ValidationError('شماره موبایل باید به فرمت 09xxxxxxxxx باشد')

def validate_national_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد ملی باید 10 رقمی باشد')

    check_digits = int(value[9])
    total = sum(int(value[i]) * (10 - i) for i in range(9)) % 11

    if int(value[3:9]) == 0 or not ((total < 2 and check_digits == total) or (total >= 2 and check_digits == (11 - total))):
        raise ValidationError('کد ملی معتبر نیست')

def validate_postal_code(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('کد پستی باید 10 رقمی باشد')

@deconstructible
class FileSizeValidator:
    def __init__(self, max_file_size_in_MB):
        self.max_file_size_in_MB = max_file_size_in_MB

    def __call__(self, value):
        max_size = self.max_file_size_in_MB * 1024 * 1024
        if value.size > max_size:
            raise ValidationError(f"حداکثر حجم فایل آپلودی، {self.max_file_size_in_MB} مگابایت است.")

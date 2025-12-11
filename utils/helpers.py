import requests
import random
import string,re


def secure_random_string(length=6, chars=string.digits):
    return ''.join(random.choice(chars) for _ in range(length))


def generate_secure_password(length=12):
    chars = string.ascii_letters + string.digits + "@#$&"
    return ''.join(random.choice(chars) for _ in range(length))

def validate_email_format(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone_format(phone):
    return bool(re.match(r'^\d{10,15}$', phone.strip()))
#!/bin/bash

USERNAME="09120759419"
PASSWORD="alirezazzz9419@sasha"

python manage.py shell <<EOF
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

User = get_user_model()

try:
    user = User.objects.get(username="$USERNAME")
    print("User already exists!")
except ObjectDoesNotExist:
    user = User.objects.create_superuser(
        username="$USERNAME",
        phone_number="$USERNAME",
        password="$PASSWORD"
    )
    print("Superuser created!")
EOF

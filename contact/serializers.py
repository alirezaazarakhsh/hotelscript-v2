from rest_framework import serializers
from .models import (
    ContactMessage,
)

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        exclude = (
            'id',
        )
        read_only_fields = (
            'created',
        )

from rest_framework import serializers
from .models import SubscriptionDescription, SubscriptionPackage, SubscriptionOption, SubscriptionPaymentRequest, SubscriptionPeriod


class SubscriptionDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionDescription
        fields = ('id', 'description')


class SubscriptionPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPeriod
        fields = ('id', 'name', 'display_name')


class SubscriptionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionOption
        fields = ('id', 'name')


class SubscriptionPackageSerializer(serializers.ModelSerializer):
    options = SubscriptionOptionSerializer(many=True, read_only=True)
    upgrade_to_level = serializers.StringRelatedField()

    class Meta:
        model = SubscriptionPackage
        fields = ('id', 'name', 'short_description', 'monthly_cost', 'color', 'options', 'upgrade_to_level', 'period', 'period_fk')


class SubscriptionPaymentRequestSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    package = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPackage.objects.all())

    class Meta:
        model = SubscriptionPaymentRequest
        fields = ('id', 'user', 'package', 'full_name', 'phone_number', 'national_id', 'receipt', 'approved')
        read_only_fields = ('approved',)

from rest_framework import serializers

class CreateTransactionSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1000, help_text="مبلغ تراکنش به تومان")
    callback_url = serializers.URLField(help_text="آدرس بازگشت پس از پرداخت")
    order_id = serializers.CharField(max_length=100, help_text="شناسه سفارش")
    mobile = serializers.CharField(max_length=11, required=False, allow_blank=True, help_text="شماره موبایل (اختیاری)")
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, help_text="توضیحات تراکنش (اختیاری)")

class VerifyTransactionSerializer(serializers.Serializer):
    authority = serializers.CharField(max_length=100, help_text="شناسه تراکنش")
    amount = serializers.IntegerField(min_value=1000, help_text="مبلغ تراکنش به تومان")
    order_id = serializers.CharField(max_length=100, help_text="شناسه سفارش")

class TransactionResponseSerializer(serializers.Serializer):
    authority = serializers.CharField(max_length=100, help_text="شناسه تراکنش")
    payment_url = serializers.URLField(help_text="لینک پرداخت")
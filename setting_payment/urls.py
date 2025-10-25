from django.urls import path
from .views import PaymentGatewayAPIView, callback_view  # فرض می‌کنیم callback_view اضافه شده

app_name = 'payment'  # تعریف namespace برای این اپلیکیشن

urlpatterns = [
    path('create/', PaymentGatewayAPIView.as_view(), name='payment_create'),  # ایجاد تراکنش
    path('verify/', PaymentGatewayAPIView.as_view(), name='payment_verify'),  # تأیید تراکنش
    path('callback/', callback_view, name='payment_callback'),  # اضافه کردن ویو callback
]
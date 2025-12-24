from django import forms
from .models import BestHotels, City, Hotel, ReservationInvoiceSettings
from django.utils.safestring import mark_safe


class HotelAdminForm(forms.ModelForm):
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس (هتل نمایش داده نمی‌شود)'),
        ('published', 'منتشر شده (هتل نمایش داده می‌شود)'),
    ]
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.RadioSelect,
        label='وضعیت انتشار',
        help_text='اگر "پیش‌نویس" انتخاب شود، هتل در لیست‌ها نمایش داده نمی‌شود. اگر "منتشر شده" انتخاب شود، هتل نمایش داده می‌شود.',
    )

    class Meta:
        model = Hotel
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(HotelAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_fields = [
                'main_image', 'image1', 'image2',
                'image3', 'image4', 'image5', 'image6'
            ]
            for field_name in image_fields:
                field_value = getattr(self.instance, field_name, None)
                if field_value:
                    self.fields[field_name].widget = forms.FileInput(attrs={'accept': 'image/*'})
                    self.fields[field_name].help_text = f'<img src="{field_value.url}" style="max-height: 200px; max-width: 200px;" />'




class BestHotelsAdminForm(forms.ModelForm):
    class Meta:
        model = BestHotels
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(BestHotelsAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_field = 'image_logo_hotel'
            field_value = getattr(self.instance, image_field, None)
            if field_value:
                self.fields[image_field].widget = forms.FileInput(attrs={'accept': 'image/*'})
                self.fields[image_field].help_text = mark_safe(
                    f'<img src="{field_value.url}" style="max-height: 200px; max-width: 200px; margin-top: 10px;" />'
                )
                
                



class CityAdminForm(forms.ModelForm):
    class Meta:
        model = City
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(CityAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_field = 'image'
            field_value = getattr(self.instance, image_field, None)
            if field_value:
                self.fields[image_field].widget = forms.FileInput(attrs={'accept': 'image/*'})
                self.fields[image_field].help_text = mark_safe(
                    f'<img src="{field_value.url}" style="max-height: 200px; max-width: 200px; margin-top: 10px;" />'
                )




    
class ReservationInvoiceSettingsAdminForm(forms.ModelForm):
    class Meta:
        model = ReservationInvoiceSettings
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_field = 'signature_image'
            field_value = getattr(self.instance, image_field, None)
            if field_value:
                self.fields[image_field].widget = forms.FileInput(attrs={'accept': 'image/*'})
                self.fields[image_field].help_text = mark_safe(
                    '<div style="margin-top: 10px; text-align: center;">'
                    '<p class="text-muted small">امضا فعلی:</p>'
                    '<img src="{}" style="max-height: 180px; max-width: 250px; '
                    'border: 2px solid #4CAF50; border-radius: 8px; padding: 4px; '
                    'box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />'
                    '<p class="text-muted small mt-2">برای تغییر، فایل جدید انتخاب کنید.</p>'
                    '</div>'.format(field_value.url)
                )
            else:
                self.fields[image_field].help_text = mark_safe(
                    '<p class="text-muted small" style="margin-top: 10px;">'
                    'هنوز تصویری آپلود نشده است.'
                    '</p>'
                )
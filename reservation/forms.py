from django import forms
from .models import Hotel

class HotelAdminForm(forms.ModelForm):
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

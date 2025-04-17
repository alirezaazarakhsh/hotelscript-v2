from django import forms
from .models import (
    StoryCategory,
    Story,
    Article,
)
class StoryCategoryAdminForm(forms.ModelForm):
    class Meta:
        model = StoryCategory
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(StoryCategoryAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_fields = [field_name for field_name, field in self.fields.items() if isinstance(field, forms.ImageField)]

            for field_name in image_fields:
                field_value = getattr(self.instance, field_name, None)
                self.fields.get(field_name).widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
                self.fields.get(field_name).help_text = f'<img src="{field_value.url}" style="max-height: 200px; max-width: 200px;" />' if field_value else ""

class StoryAdminForm(forms.ModelForm):
    class Meta:
        model = Story
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(StoryAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_fields = [field_name for field_name, field in self.fields.items() if isinstance(field, forms.ImageField)]

            for field_name in image_fields:
                field_value = getattr(self.instance, field_name, None)
                self.fields.get(field_name).widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
                self.fields.get(field_name).help_text = f'<img src="{field_value.url}" style="max-height: 200px; max-width: 200px;" />' if field_value else ""

class ArticleAdminForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ArticleAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            image_fields = [field_name for field_name, field in self.fields.items() if isinstance(field, forms.ImageField)]

            for field_name in image_fields:
                field_value = getattr(self.instance, field_name, None)
                self.fields.get(field_name).widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
                self.fields.get(field_name).help_text = f'<img src="{field_value.url}" style="max-height: 200px; max-width: 200px;" />' if field_value else ""

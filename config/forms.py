from django import forms
from .models import (
    Section,
    SiteConfig,
    Slide,
    Service,
    ChooseReason,
    Banner,
    License,
    FakeComment,
    ComingSoon,
    Statistic,
)

class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SectionForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

class SiteConfigAdminForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SiteConfigAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['header_logo'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['header_logo'].help_text = f'<img src="{self.instance.header_logo.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.header_logo else ""

            self.fields['footer_logo'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['footer_logo'].help_text = f'<img src="{self.instance.footer_logo.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.footer_logo else ""

class SlideAdminForm(forms.ModelForm):
    class Meta:
        model = Slide
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SlideAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

class ChooseReasonForm(forms.ModelForm):
    class Meta:
        model = ChooseReason
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ChooseReasonForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ServiceForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(BannerForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

class LicenseForm(forms.ModelForm):
    class Meta:
        model = License
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(LicenseForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['image'].help_text = f'<img src="{self.instance.image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.image else ""

class FakeCommentForm(forms.ModelForm):
    class Meta:
        model = FakeComment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(FakeCommentForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['commenter_image'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['commenter_image'].help_text = f'<img src="{self.instance.commenter_image.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.commenter_image else ""

class ComingSoonAdminForm(forms.ModelForm):
    class Meta:
        model = ComingSoon
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ComingSoonAdminForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['logo'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['logo'].help_text = f'<img src="{self.instance.logo.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.logo else ""

            self.fields['background'].widget = forms.widgets.FileInput(attrs={'accept': 'image/*'})
            self.fields['background'].help_text = f'<img src="{self.instance.background.url}" style="max-height: 200px; max-width: 200px;" />' if self.instance.background else ""



class StatisticAdminForm(forms.ModelForm):
    class Meta:
        model = Statistic
        fields = '__all__'

            



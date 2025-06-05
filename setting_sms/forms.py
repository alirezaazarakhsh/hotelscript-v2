from django import forms
from .models import SMSPattern, PATTERN_SECTIONS


#این فرم جلوگیری از انتخاب پترن فارسی به صورت تکراری می باشد 
class SMSPatternInlineForm(forms.ModelForm):
    class Meta:
        model = SMSPattern
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instance = kwargs.get('instance', None)
        sms_setting = instance.sms_setting if instance else self.initial.get('sms_setting')

        used_sections = []
        if sms_setting:
            used_sections = SMSPattern.objects.filter(sms_setting=sms_setting).exclude(pk=getattr(instance, 'pk', None)).values_list('name_fa', flat=True)

        available_choices = [choice for choice in PATTERN_SECTIONS if choice[0] not in used_sections]
        self.fields['name_fa'].choices = available_choices

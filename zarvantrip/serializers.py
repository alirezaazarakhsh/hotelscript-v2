from rest_framework import serializers
from django.utils.translation import gettext_lazy as _, trans_real

class ErrorMessageSerializerMixin(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.apply_custom_error_messages()

    def apply_custom_error_messages(self):
        error_messages = {
            "blank": lambda field: _('%(field_label)s may not be blank') % {'field_label': field.label},
            "required": lambda field: _('%(field_label)s is required') % {'field_label': field.label},
            "invalid_choice": lambda field: _('%(field_label)s value is not valid. valid choices are: %(valid_choice)s') % {'field_label': field.label, 'valid_choice': ', '.join(map(lambda choice: str(choice), field.choices.values()))},
        }
        for field_name, field in self.fields.items():
            for error_type in field.error_messages:
                if error_message := error_messages.get(error_type):
                    field.error_messages[error_type] = error_message(field)

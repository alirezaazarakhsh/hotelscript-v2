from django.apps import AppConfig


class BashgahMoshtarianConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bashgah_moshtarian'

    def ready(self):
       import bashgah_moshtarian.sms.signals
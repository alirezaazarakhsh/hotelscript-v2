from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'
    verbose_name = '2- مدیریت کاربران و ادمین ها'

    def ready(self):
        import authentication.signals
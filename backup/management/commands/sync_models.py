from django.core.management.base import BaseCommand
from core.backup.apps_models_list import APPS_MODELS_LIST
from core.backup.models import AppModule, AppModel

class Command(BaseCommand):
    help = 'Sync AppModule and AppModel from APPS_MODELS_LIST'

    def handle(self, *args, **kwargs):
        for app_name, model_list in APPS_MODELS_LIST.items():
            app_module, created = AppModule.objects.get_or_create(name=app_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created AppModule: {app_name}'))

            for model_name in model_list:
                app_model, model_created = AppModel.objects.get_or_create(
                    app=app_module,
                    name=model_name
                )
                if model_created:
                    self.stdout.write(self.style.SUCCESS(f'  Created AppModel: {model_name}'))

        self.stdout.write(self.style.SUCCESS('✅ Sync complete!'))

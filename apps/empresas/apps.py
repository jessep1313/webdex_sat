# apps/empresas/apps.py
from django.apps import AppConfig
from django.conf import settings
import copy

class EmpresasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empresas'

    def ready(self):
        from .models import Empresa
        empresas = Empresa.objects.using('default').filter(activo=True)
        for emp in empresas:
            if emp.db_name not in settings.DATABASES:
                default_config = copy.deepcopy(settings.DATABASES['default'])
                default_config['NAME'] = emp.db_name
                settings.DATABASES[emp.db_name] = default_config
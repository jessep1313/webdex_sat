from django.apps import AppConfig
from django.conf import settings
import copy
import sys

class CoreConfig(AppConfig):
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        # Evitar que se ejecute durante migraciones o comandos que no necesitan la BD
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        
        try:
            from apps.empresas.models import Empresa
            empresas = Empresa.objects.using('default').filter(activo=True)
            for empresa in empresas:
                db_name = empresa.db_name
                if db_name and db_name not in settings.DATABASES:
                    # Clonar la configuración de la base 'default'
                    default_config = copy.deepcopy(settings.DATABASES['default'])
                    default_config['NAME'] = db_name
                    settings.DATABASES[db_name] = default_config
                    print(f"Cargada conexión para {db_name}")
        except Exception as e:
            print(f"Error al cargar conexiones dinámicas: {e}")

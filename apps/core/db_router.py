import threading

_thread_local = threading.local()

def set_db_name(db_name):
    _thread_local.db_name = db_name

def get_db_name():
    return getattr(_thread_local, 'db_name', 'default')

class EmpresaDatabaseRouter:
    """
    Enruta las consultas de los modelos de empresas a la base de datos correcta.
    """
    def _get_db(self, model, **hints):
        # Los modelos de las apps 'empresas', 'admin', 'auth', etc. siempre usan 'default'
        if model._meta.app_label in ('empresas', 'admin', 'auth', 'contenttypes', 'sessions'):
            return 'default'
        # Para el resto (proveedores, clientes, cfdi, etc.), usar la BD del hilo
        db = get_db_name()
        return db if db in settings.DATABASES else 'default'

    def db_for_read(self, model, **hints):
        return self._get_db(model, **hints)

    def db_for_write(self, model, **hints):
        return self._get_db(model, **hints)

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Las migraciones de las apps del sistema van a 'default'
        if app_label in ('empresas', 'admin', 'auth', 'contenttypes', 'sessions'):
            return db == 'default'
        # Para las demás, permitir migrar solo en la BD de la empresa actual
        return db == get_db_name()
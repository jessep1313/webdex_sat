from .db_router import set_db_name

class DatabaseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtener el nombre de la base de datos de la empresa desde la sesión
        db_name = request.session.get('empresa_db_name')
        if db_name:
            set_db_name(db_name)
        else:
            set_db_name('default')
        return self.get_response(request)
# apps/core/decorators.py
from django.shortcuts import redirect

def superadmin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') != 'SA':
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped

# (Si tienes otros decoradores como admin_required, actualízalos también)
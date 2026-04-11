from django.shortcuts import redirect

def superadmin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') != 'SA':
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped

def admin_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') != 'A':
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped

# Si tienes un decorador para usuarios normales, agrégalo también
def usuario_required(view_func):
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_type') != 'US':
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped
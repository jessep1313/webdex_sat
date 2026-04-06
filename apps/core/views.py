from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from empresas.models import SuperAdmin
from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = SuperAdmin.objects.get(email=email, activo=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_type'] = 'superadmin'
                request.session['user_nombre'] = user.nombre
                return redirect('dashboard_superadmin')
            else:
                messages.error(request, 'Contraseña incorrecta')
        except SuperAdmin.DoesNotExist:
            messages.error(request, 'Usuario no encontrado')
    return render(request, 'core/login.html')

def dashboard_superadmin(request):
    if request.session.get('user_type') != 'superadmin':
        return redirect('login')
    return render(request, 'core/superadmin/dashboard.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')

from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma

# Vistas para Catálogos
def grupos_lista(request):
    grupos = Grupo.objects.using('default').all()
    return render(request, 'core/catalogos/grupos_lista.html', {'grupos': grupos})

def empresas_lista(request):
    empresas = Empresa.objects.using('default').all()
    return render(request, 'core/catalogos/empresas_lista.html', {'empresas': empresas})

def sucursales_lista(request):
    sucursales = Sucursal.objects.using('default').all()
    return render(request, 'core/catalogos/sucursales_lista.html', {'sucursales': sucursales})

# Vistas para Usuarios
def admin_lista(request):
    admins = Admin.objects.using('default').all()
    return render(request, 'core/usuarios/admin_lista.html', {'admins': admins})

def usuarios_lista(request):
    usuarios = UsuarioCentral.objects.using('default').all()
    return render(request, 'core/usuarios/usuarios_lista.html', {'usuarios': usuarios})

# Vista para SAT - Efirma
def efirma_lista(request):
    efirmas = EFirma.objects.using('default').all()
    return render(request, 'core/sat/efirma_lista.html', {'efirmas': efirmas})
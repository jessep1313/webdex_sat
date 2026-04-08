from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from empresas.models import SuperAdmin, Admin, UsuarioCentral
from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma
from .decorators import superadmin_required
from django.conf import settings
import copy
import re
from .utils import crear_tablas_empresa
from django.db import connections



def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # 1. Buscar en superadmins
        try:
            user = SuperAdmin.objects.using('default').get(email=email, activo=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_nombre'] = user.nombre
                request.session['user_email'] = user.email
                request.session['user_type'] = 'SA'
                return redirect('dashboard')
            else:
                messages.error(request, 'Contraseña incorrecta')
                return render(request, 'core/login.html')
        except SuperAdmin.DoesNotExist:
            pass

        # 2. Buscar en admin
        try:
            user = Admin.objects.using('default').get(email=email, activo=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_nombre'] = user.nombre
                request.session['user_email'] = user.email
                request.session['user_type'] = 'A'
                # Opcional: guardar empresa_id, grupo_id si se necesita
                request.session['empresa_id'] = user.empresa_id if user.empresa else None
                return redirect('dashboard')
            else:
                messages.error(request, 'Contraseña incorrecta')
                return render(request, 'core/login.html')
        except Admin.DoesNotExist:
            pass

        # 3. Buscar en usuarios
        try:
            user = UsuarioCentral.objects.using('default').get(email=email, activo=True)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_nombre'] = user.nombre
                request.session['user_email'] = user.email
                request.session['user_type'] = 'US'
                # Opcional: guardar empresa_id, sucursal_id
                request.session['empresa_id'] = user.empresa_id if user.empresa else None
                request.session['sucursal_id'] = user.sucursal_id if user.sucursal else None
                return redirect('dashboard')
            else:
                messages.error(request, 'Contraseña incorrecta')
                return render(request, 'core/login.html')
        except UsuarioCentral.DoesNotExist:
            pass

        # Si no se encontró en ninguna tabla
        messages.error(request, 'Usuario no encontrado o inactivo')
        return render(request, 'core/login.html')

    return render(request, 'core/login.html')


def dashboard(request):
    user_type = request.session.get('user_type')
    if not user_type:
        return redirect('login')
    return render(request, 'core/dashboard.html')
    

def dashboard_superadmin(request):
    if request.session.get('user_type') != 'superadmin':
        return redirect('login')
    return render(request, 'core/superadmin/dashboard.html')


def logout_view(request):
    request.session.flush()
    return redirect('login')

from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma

@superadmin_required
def grupos_lista(request):
    grupos = Grupo.objects.using('default').all()
    return render(request, 'core/catalogos/grupos_lista.html', {'grupos': grupos})


@superadmin_required
def grupo_crear(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        activo = request.POST.get('activo') == 'on'
        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
            return render(request, 'core/catalogos/grupo_form.html', {'grupo': None})
        grupo = Grupo(nombre=nombre, descripcion=descripcion, activo=activo)
        grupo.save(using='default')
        messages.success(request, 'Grupo creado correctamente.')
        return redirect('grupos_lista')
    return render(request, 'core/catalogos/grupo_form.html', {'grupo': None})


@superadmin_required
def grupo_editar(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    if request.method == 'POST':
        grupo.nombre = request.POST.get('nombre')
        grupo.descripcion = request.POST.get('descripcion')
        grupo.activo = request.POST.get('activo') == 'on'
        grupo.save(using='default')
        messages.success(request, 'Grupo actualizado correctamente.')
        return redirect('grupos_lista')
    return render(request, 'core/catalogos/grupo_form.html', {'grupo': grupo})



@superadmin_required
def grupo_eliminar(request, pk):
    grupo = get_object_or_404(Grupo, pk=pk)
    # Verificar si hay empresas asociadas
    if Empresa.objects.using('default').filter(grupo=grupo).exists():
        messages.error(request, 'No se puede eliminar el grupo porque tiene empresas asociadas.')
        return redirect('grupos_lista')
    grupo.delete(using='default')
    messages.success(request, 'Grupo eliminado correctamente.')
    return redirect('grupos_lista')


# ... (código existente)

@superadmin_required
def empresas_lista(request):
    empresas = Empresa.objects.using('default').all()
    return render(request, 'core/catalogos/empresas_lista.html', {'empresas': empresas})

@superadmin_required
def empresa_crear(request):
    grupos = Grupo.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        rfc = request.POST.get('rfc').upper().strip()
        grupo_id = request.POST.get('grupo')
        activo = request.POST.get('activo') == 'on'

        # Validaciones
        if not nombre or not rfc or not grupo_id:
            messages.error(request, 'Nombre, RFC y Grupo son obligatorios.')
            return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})

        # Verificar RFC único
        if Empresa.objects.using('default').filter(rfc=rfc).exists():
            messages.error(request, f'Ya existe una empresa con RFC {rfc}.')
            return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})

        # Generar nombre de base de datos
        db_name = f"db_empresa_{rfc}"
        # Verificar que no exista ya una base de datos con ese nombre (por si acaso)
        # (Opcional: también verificar en settings.DATABASES)

        # 1. Crear la base de datos físicamente
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        except Exception as e:
            messages.error(request, f'Error creando la base de datos: {e}')
            return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})

        # 2. Agregar la conexión a settings.DATABASES (dinámicamente)
        default_config = copy.deepcopy(settings.DATABASES['default'])
        default_config['NAME'] = db_name
        settings.DATABASES[db_name] = default_config

        # 3. Crear las tablas en la nueva base
        try:
            crear_tablas_empresa(db_name)
        except Exception as e:
            messages.error(request, f'Error creando tablas: {e}')
            # Opcional: eliminar la base de datos recién creada
            with connections['default'].cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {db_name}")
            return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})

        # 4. Guardar el registro de la empresa en db_central
        grupo = Grupo.objects.using('default').get(pk=grupo_id)
        empresa = Empresa(
            nombre=nombre,
            rfc=rfc,
            grupo=grupo,
            db_name=db_name,
            activo=activo
        )
        empresa.save(using='default')

        messages.success(request, f'Empresa "{nombre}" creada exitosamente.')
        return redirect('empresas_lista')

    return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})

@superadmin_required
def empresa_editar(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    grupos = Grupo.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        rfc = request.POST.get('rfc').upper().strip()
        grupo_id = request.POST.get('grupo')
        activo = request.POST.get('activo') == 'on'

        if not nombre or not rfc or not grupo_id:
            messages.error(request, 'Nombre, RFC y Grupo son obligatorios.')
            return render(request, 'core/catalogos/empresa_form.html', {'empresa': empresa, 'grupos': grupos})

        # Validar que el RFC no esté en otra empresa (excepto esta misma)
        if Empresa.objects.using('default').filter(rfc=rfc).exclude(pk=pk).exists():
            messages.error(request, f'Ya existe otra empresa con RFC {rfc}.')
            return render(request, 'core/catalogos/empresa_form.html', {'empresa': empresa, 'grupos': grupos})

        # Si el RFC cambió, se debería renombrar la base de datos? Eso es complejo. Mejor no permitir cambiar RFC.
        if rfc != empresa.rfc:
            messages.error(request, 'No está permitido cambiar el RFC de una empresa existente.')
            return render(request, 'core/catalogos/empresa_form.html', {'empresa': empresa, 'grupos': grupos})

        empresa.nombre = nombre
        empresa.grupo_id = grupo_id
        empresa.activo = activo
        empresa.save(using='default')

        messages.success(request, 'Empresa actualizada correctamente.')
        return redirect('empresas_lista')

    return render(request, 'core/catalogos/empresa_form.html', {'empresa': empresa, 'grupos': grupos})

@superadmin_required
def empresa_eliminar(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    # Eliminación lógica: solo desactivar
    empresa.activo = False
    empresa.save(using='default')
    messages.success(request, f'Empresa "{empresa.nombre}" desactivada correctamente.')
    return redirect('empresas_lista')






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
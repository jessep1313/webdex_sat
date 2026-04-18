from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from empresas.models import SuperAdmin, Admin, UsuarioCentral
from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma
from .decorators import superadmin_required, admin_required, usuario_required
from django.conf import settings
import copy
import re
from .utils import crear_tablas_empresa
from django.db import connections
import json
import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt






def login_view_2(request):
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

##funcion para traernos el rfc 
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
                # Obtener datos de la empresa asociada
                if user.empresa_id:
                    empresa = Empresa.objects.using('default').get(pk=user.empresa_id)
                    request.session['empresa_id'] = empresa.id
                    request.session['empresa_nombre'] = empresa.nombre
                    request.session['empresa_rfc'] = empresa.rfc
                    request.session['empresa_db_name'] = empresa.db_name
                    if empresa.grupo:
                        request.session['grupo_id'] = empresa.grupo.id
                        request.session['grupo_nombre'] = empresa.grupo.nombre
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
                if user.empresa_id:
                    empresa = Empresa.objects.using('default').get(pk=user.empresa_id)
                    request.session['empresa_id'] = empresa.id
                    request.session['empresa_nombre'] = empresa.nombre
                    request.session['empresa_rfc'] = empresa.rfc
                    request.session['empresa_db_name'] = empresa.db_name
                    if empresa.grupo:
                        request.session['grupo_id'] = empresa.grupo.id
                        request.session['grupo_nombre'] = empresa.grupo.nombre
                if user.sucursal_id:
                    sucursal = Sucursal.objects.using('default').get(pk=user.sucursal_id)
                    request.session['sucursal_id'] = sucursal.id
                    request.session['sucursal_nombre'] = sucursal.nombre
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






# ========== SUCURSALES ==========
@superadmin_required
def sucursales_lista(request):
    sucursales = Sucursal.objects.using('default').select_related('empresa').all()
    return render(request, 'core/catalogos/sucursales_lista.html', {'sucursales': sucursales})

@superadmin_required
def sucursal_crear(request):
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        codigo = request.POST.get('codigo')
        empresa_id = request.POST.get('empresa')
        activo = request.POST.get('activo') == 'on'

        if not nombre or not codigo or not empresa_id:
            messages.error(request, 'Nombre, código y empresa son obligatorios.')
            return render(request, 'core/catalogos/sucursal_form.html', {'empresas': empresas})

        sucursal = Sucursal(
            nombre=nombre,
            codigo=codigo,
            empresa_id=empresa_id,
            activo=activo
        )
        sucursal.save(using='default')
        messages.success(request, 'Sucursal creada correctamente.')
        return redirect('sucursales_lista')
    return render(request, 'core/catalogos/sucursal_form.html', {'empresas': empresas})

@superadmin_required
def sucursal_editar(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        sucursal.nombre = request.POST.get('nombre')
        sucursal.codigo = request.POST.get('codigo')
        sucursal.empresa_id = request.POST.get('empresa')
        sucursal.activo = request.POST.get('activo') == 'on'
        sucursal.save(using='default')
        messages.success(request, 'Sucursal actualizada correctamente.')
        return redirect('sucursales_lista')
    return render(request, 'core/catalogos/sucursal_form.html', {'sucursal': sucursal, 'empresas': empresas})

@superadmin_required
def sucursal_eliminar(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    # Eliminación lógica
    sucursal.activo = False
    sucursal.save(using='default')
    messages.success(request, f'Sucursal "{sucursal.nombre}" desactivada correctamente.')
    return redirect('sucursales_lista')



# ========== ADMINISTRADORES ==========
@superadmin_required
def admin_lista(request):
    admins = Admin.objects.using('default').select_related('empresa', 'grupo').all()
    return render(request, 'core/usuarios/admin_lista.html', {'admins': admins})

@superadmin_required
def admin_crear(request):
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        empresa_id = request.POST.get('empresa')
        activo = request.POST.get('activo') == 'on'

        if not nombre or not email or not password or not empresa_id:
            messages.error(request, 'Nombre, email, contraseña y empresa son obligatorios.')
            return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})
        if Admin.objects.using('default').filter(email=email).exists():
            messages.error(request, 'Ya existe un administrador con ese email.')
            return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})

        # Obtener la empresa para conocer su grupo
        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        grupo_id = empresa.grupo_id  # puede ser None si la empresa no tiene grupo, pero normalmente sí

        admin = Admin(
            nombre=nombre,
            email=email,
            password=make_password(password),
            grupo_id=grupo_id,
            empresa_id=empresa_id,
            activo=activo
        )
        admin.save(using='default')
        messages.success(request, 'Administrador creado correctamente.')
        return redirect('admin_lista')
    return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})

@superadmin_required
def admin_editar(request, pk):
    admin = get_object_or_404(Admin, pk=pk)
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        empresa_id = request.POST.get('empresa')
        activo = request.POST.get('activo') == 'on'

        if not nombre or not email or not empresa_id:
            messages.error(request, 'Nombre, email y empresa son obligatorios.')
            return render(request, 'core/usuarios/admin_form.html', {'admin': admin, 'empresas': empresas})
        if Admin.objects.using('default').filter(email=email).exclude(pk=pk).exists():
            messages.error(request, 'Ya existe otro administrador con ese email.')
            return render(request, 'core/usuarios/admin_form.html', {'admin': admin, 'empresas': empresas})

        # Actualizar datos
        admin.nombre = nombre
        admin.email = email
        admin.empresa_id = empresa_id
        admin.activo = activo

        # Actualizar grupo según la nueva empresa (si cambió)
        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        admin.grupo_id = empresa.grupo_id

        # Si se proporciona nueva contraseña
        if password:
            if password != password2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return render(request, 'core/usuarios/admin_form.html', {'admin': admin, 'empresas': empresas})
            admin.password = make_password(password)

        admin.save(using='default')
        messages.success(request, 'Administrador actualizado correctamente.')
        return redirect('admin_lista')
    return render(request, 'core/usuarios/admin_form.html', {'admin': admin, 'empresas': empresas})

@superadmin_required
def admin_eliminar(request, pk):
    admin = get_object_or_404(Admin, pk=pk)
    admin.activo = False
    admin.save(using='default')
    messages.success(request, f'Administrador "{admin.nombre}" desactivado correctamente.')
    return redirect('admin_lista')




def usuarios_lista(request):
    usuarios = UsuarioCentral.objects.using('default').all()
    return render(request, 'core/usuarios/usuarios_lista.html', {'usuarios': usuarios})

# Vista para SAT - Efirma
def efirma_lista(request):
    efirmas = EFirma.objects.using('default').all()
    return render(request, 'core/sat/efirma_lista.html', {'efirmas': efirmas})



# ========== USUARIOS NORMALES ==========
@superadmin_required
def usuarios_lista(request):
    usuarios = UsuarioCentral.objects.using('default').select_related('empresa', 'sucursal').all()
    return render(request, 'core/usuarios/usuarios_lista.html', {'usuarios': usuarios})

@superadmin_required
def usuario_crear(request):
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        tipo = request.POST.get('tipo')
        empresa_id = request.POST.get('empresa')
        sucursal_id = request.POST.get('sucursal') or None
        activo = request.POST.get('activo') == 'on'

        if not nombre or not email or not password or not tipo or not empresa_id:
            messages.error(request, 'Nombre, email, contraseña, tipo y empresa son obligatorios.')
            return render(request, 'core/usuarios/usuario_form.html', {'empresas': empresas})
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'core/usuarios/usuario_form.html', {'empresas': empresas})
        if UsuarioCentral.objects.using('default').filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con ese email.')
            return render(request, 'core/usuarios/usuario_form.html', {'empresas': empresas})

        # Obtener la empresa para conocer su grupo
        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        grupo_id = empresa.grupo_id  # puede ser None

        usuario = UsuarioCentral(
            nombre=nombre,
            email=email,
            password=make_password(password),
            tipo=tipo,
            empresa_id=empresa_id,
            sucursal_id=sucursal_id,
            grupo_id=grupo_id,
            activo=activo
        )
        usuario.save(using='default')
        messages.success(request, 'Usuario creado correctamente.')
        return redirect('usuarios_lista')
    return render(request, 'core/usuarios/usuario_form.html', {'empresas': empresas})

@superadmin_required
def usuario_editar(request, pk):
    usuario = get_object_or_404(UsuarioCentral, pk=pk)
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        tipo = request.POST.get('tipo')
        empresa_id = request.POST.get('empresa')
        sucursal_id = request.POST.get('sucursal') or None
        activo = request.POST.get('activo') == 'on'

        if not nombre or not email or not tipo or not empresa_id:
            messages.error(request, 'Nombre, email, tipo y empresa son obligatorios.')
            return render(request, 'core/usuarios/usuario_form.html', {'usuario': usuario, 'empresas': empresas})
        if UsuarioCentral.objects.using('default').filter(email=email).exclude(pk=pk).exists():
            messages.error(request, 'Ya existe otro usuario con ese email.')
            return render(request, 'core/usuarios/usuario_form.html', {'usuario': usuario, 'empresas': empresas})

        # Actualizar grupo según la nueva empresa (si cambió)
        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        grupo_id = empresa.grupo_id

        usuario.nombre = nombre
        usuario.email = email
        usuario.tipo = tipo
        usuario.empresa_id = empresa_id
        usuario.sucursal_id = sucursal_id
        usuario.grupo_id = grupo_id
        usuario.activo = activo

        if password:
            if password != password2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return render(request, 'core/usuarios/usuario_form.html', {'usuario': usuario, 'empresas': empresas})
            usuario.password = make_password(password)

        usuario.save(using='default')
        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('usuarios_lista')
    return render(request, 'core/usuarios/usuario_form.html', {'usuario': usuario, 'empresas': empresas})

@superadmin_required
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(UsuarioCentral, pk=pk)
    usuario.activo = False
    usuario.save(using='default')
    messages.success(request, f'Usuario "{usuario.nombre}" desactivado correctamente.')
    return redirect('usuarios_lista')


from django.http import JsonResponse
from empresas.models import Sucursal

def api_sucursales(request):
    empresa_id = request.GET.get('empresa_id')
    if not empresa_id:
        return JsonResponse([], safe=False)
    sucursales = Sucursal.objects.using('default').filter(empresa_id=empresa_id, activo=True).values('id', 'nombre')
    return JsonResponse(list(sucursales), safe=False)




# ========== EFIRMAS (SAT) ==========
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.signing import dumps, loads
from django.conf import settings
import os
import tempfile
from satcfdi.models import Signer
from empresas.models import EFirmaLog

@superadmin_required
def efirma_crear(request):
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        empresa_id = request.POST.get('empresa')
        archivo_cer = request.FILES.get('archivo_cer')
        archivo_key = request.FILES.get('archivo_key')
        password = request.POST.get('password')

        if not empresa_id or not archivo_cer or not archivo_key or not password:
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'core/sat/efirma_form.html', {'empresas': empresas})

        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        grupo_nombre = empresa.grupo.nombre if empresa.grupo else 'Sin grupo'
        rfc_empresa = empresa.rfc
        upload_path = f"efirmas/{rfc_empresa}/"
        cer_name = f"{rfc_empresa}_certificado.cer"
        key_name = f"{rfc_empresa}_llave.key"

        cer_path = default_storage.save(upload_path + cer_name, ContentFile(archivo_cer.read()))
        key_path = default_storage.save(upload_path + key_name, ContentFile(archivo_key.read()))

        password_cifrada = dumps(password)

        efirma = EFirma(
            archivo_cer=cer_path,
            archivo_key=key_path,
            password=password_cifrada,
            estatus='pendiente',
            grupo=grupo_nombre,
            empresa=empresa.nombre
        )
        efirma.save(using='default')

        # Registrar en log
        usuario = request.session.get('user_nombre', request.session.get('user_email', 'Desconocido'))
        EFirmaLog.objects.using('default').create(
            efirma_id=efirma.id,
            accion=f"Creada por {usuario}"
        )
        messages.success(request, 'FIEL cargada correctamente. Puede validarla ahora.')
        return redirect('efirma_lista')
    return render(request, 'core/sat/efirma_form.html', {'empresas': empresas})

@superadmin_required
def efirma_validar(request, pk):
    efirma = get_object_or_404(EFirma, pk=pk)
    try:
        password = loads(efirma.password)
    except Exception:
        messages.error(request, 'Error al descifrar la contraseña.')
        return redirect('efirma_lista')

    cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
    key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)

    if not os.path.exists(cer_path) or not os.path.exists(key_path):
        messages.error(request, 'Los archivos de la FIEL no existen en el servidor.')
        efirma.estatus = 'rechazado'
        efirma.save(using='default')
        usuario = request.session.get('user_nombre', request.session.get('user_email', 'Desconocido'))
        EFirmaLog.objects.using('default').create(
            efirma_id=efirma.id,
            accion=f"Validación fallida (archivos no encontrados) por {usuario}"
        )
        return redirect('efirma_lista')

    try:
        with open(cer_path, 'rb') as cer_file, open(key_path, 'rb') as key_file:
            signer = Signer.load(
                certificate=cer_file.read(),
                key=key_file.read(),
                password=password
            )
        efirma.estatus = 'validado'
        mensaje = f"Validado - RFC: {signer.rfc}, Nombre: {signer.legal_name}"
        messages.success(request, mensaje)
    except Exception as e:
        efirma.estatus = 'rechazado'
        mensaje = f"Rechazado - Error: {str(e)}"
        messages.error(request, mensaje)
    efirma.save(using='default')
    usuario = request.session.get('user_nombre', request.session.get('user_email', 'Desconocido'))
    EFirmaLog.objects.using('default').create(
        efirma_id=efirma.id,
        accion=f"{mensaje} por {usuario}"
    )
    return redirect('efirma_lista')

@superadmin_required
def efirma_eliminar(request, pk):
    efirma = get_object_or_404(EFirma, pk=pk)
    cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
    key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)
    if os.path.exists(cer_path):
        os.remove(cer_path)
    if os.path.exists(key_path):
        os.remove(key_path)
    efirma.delete(using='default')
    usuario = request.session.get('user_nombre', request.session.get('user_email', 'Desconocido'))
    EFirmaLog.objects.using('default').create(
        efirma_id=pk,
        accion=f"Eliminada por {usuario}"
    )
    messages.success(request, 'Registro de FIEL eliminado correctamente.')
    return redirect('efirma_lista')



from cryptography import x509
from cryptography.hazmat.backends import default_backend

@superadmin_required
def efirma_actualizar_vigencia(request, pk):
    efirma = get_object_or_404(EFirma, pk=pk)
    cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
    if not os.path.exists(cer_path):
        messages.error(request, 'El archivo .cer no existe.')
        return redirect('efirma_lista')
    try:
        with open(cer_path, 'rb') as cer_file:
            cert_data = cer_file.read()
            # Intentar cargar como PEM primero
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except Exception:
                # Si falla, intentar como DER
                cert = x509.load_der_x509_certificate(cert_data, default_backend())
            efirma.vigencia = cert.not_valid_after.date()
        efirma.save(using='default')
        usuario = request.session.get('user_nombre', 'Desconocido')
        EFirmaLog.objects.using('default').create(
            efirma_id=efirma.id,
            accion=f"Vigencia actualizada: {efirma.vigencia} por {usuario}"
        )
        messages.success(request, 'Vigencia actualizada correctamente.')
    except Exception as e:
        messages.error(request, f'Error al leer la vigencia: {str(e)}')
    return redirect('efirma_lista')


@superadmin_required
def efirma_log_lista(request):
    logs = EFirmaLog.objects.using('default').select_related().all().order_by('-fecha')
    # Para cada log, obtenemos la empresa y grupo desde la eFirma asociada
    for log in logs:
        try:
            efirma = EFirma.objects.using('default').get(pk=log.efirma_id)
            log.empresa_nombre = efirma.empresa
            log.grupo_nombre = efirma.grupo
        except EFirma.DoesNotExist:
            log.empresa_nombre = 'Eliminada'
            log.grupo_nombre = '-'
    return render(request, 'core/sat/efirma_log_lista.html', {'logs': logs})


from django.contrib.auth.hashers import make_password

@admin_required
def admin_usuarios_lista(request):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    # Filtrar usuarios normales (tipo 'US') que pertenezcan a esta empresa
    usuarios = UsuarioCentral.objects.using('default').filter(empresa_id=empresa_id, activo=True).select_related('sucursal')
    return render(request, 'core/usuarios/admin_usuarios_lista.html', {'usuarios': usuarios})

@admin_required
def admin_usuario_crear(request):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    # Obtener sucursales de la empresa
    sucursales = Sucursal.objects.using('default').filter(empresa_id=empresa_id, activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        tipo = request.POST.get('tipo')
        sucursal_id = request.POST.get('sucursal') or None
        activo = request.POST.get('activo') == 'on'

        if not nombre or not email or not password or not tipo:
            messages.error(request, 'Nombre, email, contraseña y tipo son obligatorios.')
            return render(request, 'core/usuarios/admin_usuario_form.html', {'sucursales': sucursales})
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'core/usuarios/admin_usuario_form.html', {'sucursales': sucursales})
        if UsuarioCentral.objects.using('default').filter(email=email).exists():
            messages.error(request, 'Ya existe un usuario con ese email.')
            return render(request, 'core/usuarios/admin_usuario_form.html', {'sucursales': sucursales})

        usuario = UsuarioCentral(
            nombre=nombre,
            email=email,
            password=make_password(password),
            tipo=tipo,
            empresa_id=empresa_id,
            sucursal_id=sucursal_id,
            activo=activo
        )
        usuario.save(using='default')
        messages.success(request, 'Usuario creado correctamente.')
        return redirect('admin_usuarios_lista')
    return render(request, 'core/usuarios/admin_usuario_form.html', {'sucursales': sucursales})

@admin_required
def admin_usuario_editar(request, pk):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    usuario = get_object_or_404(UsuarioCentral, pk=pk, empresa_id=empresa_id)
    sucursales = Sucursal.objects.using('default').filter(empresa_id=empresa_id, activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        tipo = request.POST.get('tipo')
        sucursal_id = request.POST.get('sucursal') or None
        activo = request.POST.get('activo') == 'on'

        if not nombre or not email or not tipo:
            messages.error(request, 'Nombre, email y tipo son obligatorios.')
            return render(request, 'core/usuarios/admin_usuario_form.html', {'usuario': usuario, 'sucursales': sucursales})
        if UsuarioCentral.objects.using('default').filter(email=email).exclude(pk=pk).exists():
            messages.error(request, 'Ya existe otro usuario con ese email.')
            return render(request, 'core/usuarios/admin_usuario_form.html', {'usuario': usuario, 'sucursales': sucursales})

        usuario.nombre = nombre
        usuario.email = email
        usuario.tipo = tipo
        usuario.sucursal_id = sucursal_id
        usuario.activo = activo
        if password:
            if password != password2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return render(request, 'core/usuarios/admin_usuario_form.html', {'usuario': usuario, 'sucursales': sucursales})
            usuario.password = make_password(password)
        usuario.save(using='default')
        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('admin_usuarios_lista')
    return render(request, 'core/usuarios/admin_usuario_form.html', {'usuario': usuario, 'sucursales': sucursales})

@admin_required
def admin_usuario_eliminar(request, pk):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    usuario = get_object_or_404(UsuarioCentral, pk=pk, empresa_id=empresa_id)
    usuario.activo = False
    usuario.save(using='default')
    messages.success(request, f'Usuario "{usuario.nombre}" desactivado correctamente.')
    return redirect('admin_usuarios_lista')

# ========== EFIRMAS PARA ADMINISTRADOR ==========
@admin_required
def admin_efirma_lista(request):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    empresa = Empresa.objects.using('default').get(pk=empresa_id)
    efirmas = EFirma.objects.using('default').filter(empresa=empresa.nombre).order_by('-fecha_carga')
    return render(request, 'core/sat/admin_efirma_lista.html', {'efirmas': efirmas, 'empresa': empresa})

@admin_required
def admin_efirma_crear(request):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    empresa = Empresa.objects.using('default').get(pk=empresa_id)
    if request.method == 'POST':
        archivo_cer = request.FILES.get('archivo_cer')
        archivo_key = request.FILES.get('archivo_key')
        password = request.POST.get('password')
        if not archivo_cer or not archivo_key or not password:
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'core/sat/admin_efirma_form.html', {'empresa': empresa})
        # Validar extensiones
        if not archivo_cer.name.endswith('.cer') or not archivo_key.name.endswith('.key'):
            messages.error(request, 'Los archivos deben tener extensión .cer y .key.')
            return render(request, 'core/sat/admin_efirma_form.html', {'empresa': empresa})

        rfc_empresa = empresa.rfc
        upload_path = f"efirmas/{rfc_empresa}/"
        cer_name = f"{rfc_empresa}_certificado.cer"
        key_name = f"{rfc_empresa}_llave.key"
        cer_path = default_storage.save(upload_path + cer_name, ContentFile(archivo_cer.read()))
        key_path = default_storage.save(upload_path + key_name, ContentFile(archivo_key.read()))
        password_cifrada = dumps(password)
        grupo_nombre = empresa.grupo.nombre if empresa.grupo else 'Sin grupo'
        efirma = EFirma(
            archivo_cer=cer_path,
            archivo_key=key_path,
            password=password_cifrada,
            estatus='pendiente',
            grupo=grupo_nombre,
            empresa=empresa.nombre
        )
        efirma.save(using='default')
        usuario = request.session.get('user_nombre', 'Desconocido')
        EFirmaLog.objects.using('default').create(efirma_id=efirma.id, accion=f"Creada por {usuario}")
        messages.success(request, 'FIEL cargada correctamente.')
        return redirect('admin_efirma_lista')
    return render(request, 'core/sat/admin_efirma_form.html', {'empresa': empresa})

@admin_required
def admin_efirma_validar(request, pk):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    empresa = Empresa.objects.using('default').get(pk=empresa_id)
    efirma = get_object_or_404(EFirma, pk=pk, empresa=empresa.nombre)
    try:
        password = loads(efirma.password)
    except Exception:
        messages.error(request, 'Error al descifrar la contraseña.')
        return redirect('admin_efirma_lista')
    cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
    key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)
    if not os.path.exists(cer_path) or not os.path.exists(key_path):
        messages.error(request, 'Los archivos de la FIEL no existen en el servidor.')
        efirma.estatus = 'rechazado'
        efirma.save(using='default')
        EFirmaLog.objects.using('default').create(efirma_id=efirma.id, accion=f"Validación fallida (archivos no encontrados) por {request.session.get('user_nombre')}")
        return redirect('admin_efirma_lista')
    try:
        with open(cer_path, 'rb') as cer_file, open(key_path, 'rb') as key_file:
            signer = Signer.load(
                certificate=cer_file.read(),
                key=key_file.read(),
                password=password
            )
        efirma.estatus = 'validado'
        # Actualizar vigencia si se puede
        with open(cer_path, 'rb') as cer_file:
            cert_data = cer_file.read()
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except:
                cert = x509.load_der_x509_certificate(cert_data, default_backend())
            efirma.vigencia = cert.not_valid_after.date()
        efirma.save(using='default')
        EFirmaLog.objects.using('default').create(efirma_id=efirma.id, accion=f"Validada (vigencia hasta {efirma.vigencia}) por {request.session.get('user_nombre')}")
        messages.success(request, f'FIEL válida. RFC: {signer.rfc}, Nombre: {signer.legal_name}')
    except Exception as e:
        efirma.estatus = 'rechazado'
        efirma.save(using='default')
        EFirmaLog.objects.using('default').create(efirma_id=efirma.id, accion=f"Validación fallida: {str(e)} por {request.session.get('user_nombre')}")
        messages.error(request, f'FIEL inválida: {str(e)}')
    return redirect('admin_efirma_lista')

@admin_required
def admin_efirma_actualizar_vigencia(request, pk):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    empresa = Empresa.objects.using('default').get(pk=empresa_id)
    efirma = get_object_or_404(EFirma, pk=pk, empresa=empresa.nombre)
    cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
    if not os.path.exists(cer_path):
        messages.error(request, 'El archivo .cer no existe.')
        return redirect('admin_efirma_lista')
    try:
        with open(cer_path, 'rb') as cer_file:
            cert_data = cer_file.read()
            try:
                cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            except:
                cert = x509.load_der_x509_certificate(cert_data, default_backend())
            efirma.vigencia = cert.not_valid_after.date()
        efirma.save(using='default')
        EFirmaLog.objects.using('default').create(efirma_id=efirma.id, accion=f"Vigencia actualizada: {efirma.vigencia} por {request.session.get('user_nombre')}")
        messages.success(request, 'Vigencia actualizada correctamente.')
    except Exception as e:
        messages.error(request, f'Error al leer la vigencia: {str(e)}')
    return redirect('admin_efirma_lista')

@admin_required
def admin_efirma_eliminar(request, pk):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    empresa = Empresa.objects.using('default').get(pk=empresa_id)
    efirma = get_object_or_404(EFirma, pk=pk, empresa=empresa.nombre)
    cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
    key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)
    if os.path.exists(cer_path):
        os.remove(cer_path)
    if os.path.exists(key_path):
        os.remove(key_path)
    # Guardar log antes de eliminar
    EFirmaLog.objects.using('default').create(efirma_id=efirma.id, accion=f"Eliminada por {request.session.get('user_nombre')}")
    efirma.delete(using='default')
    messages.success(request, 'Registro de FIEL eliminado correctamente.')
    return redirect('admin_efirma_lista')

@admin_required
def admin_efirma_log_lista(request):
    empresa_id = request.session.get('empresa_id')
    if not empresa_id:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')
    empresa = Empresa.objects.using('default').get(pk=empresa_id)
    # Obtener IDs de eFirmas de la empresa
    efirmas_ids = EFirma.objects.using('default').filter(empresa=empresa.nombre).values_list('id', flat=True)
    logs = EFirmaLog.objects.using('default').filter(efirma_id__in=efirmas_ids).order_by('-fecha')
    # Añadir nombre de empresa y grupo para mostrar (opcional)
    for log in logs:
        try:
            ef = EFirma.objects.using('default').get(pk=log.efirma_id)
            log.empresa_nombre = ef.empresa
            log.grupo_nombre = ef.grupo
        except EFirma.DoesNotExist:
            log.empresa_nombre = empresa.nombre
            log.grupo_nombre = '-'
    return render(request, 'core/sat/admin_efirma_log_lista.html', {'logs': logs})



from django.db import connections

@admin_required
def admin_correos_lista(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        messages.error(request, 'No se ha identificado la base de datos de la empresa.')
        return redirect('dashboard')
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT id, tipo, titulo, cuerpo, created_at FROM configuracion_correos ORDER BY tipo")
        rows = cursor.fetchall()
    correos = []
    for row in rows:
        correos.append({
            'id': row[0],
            'tipo': row[1],
            'titulo': row[2],
            'cuerpo': row[3],
            'created_at': row[4],
        })
    return render(request, 'core/correos/admin_correos_lista.html', {'correos': correos})

@admin_required
def admin_correo_crear(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        messages.error(request, 'No se ha identificado la base de datos de la empresa.')
        return redirect('dashboard')
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        titulo = request.POST.get('titulo')
        cuerpo = request.POST.get('cuerpo')
        if not tipo or not titulo or not cuerpo:
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'core/correos/admin_correo_form.html')
        # Verificar si ya existe una configuración para ese tipo
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM configuracion_correos WHERE tipo = %s", [tipo])
            if cursor.fetchone()[0] > 0:
                messages.error(request, f'Ya existe una configuración para el tipo "{tipo}".')
                return render(request, 'core/correos/admin_correo_form.html')
            cursor.execute(
                "INSERT INTO configuracion_correos (tipo, titulo, cuerpo) VALUES (%s, %s, %s)",
                [tipo, titulo, cuerpo]
            )
        messages.success(request, 'Configuración de correo creada correctamente.')
        return redirect('admin_correos_lista')
    return render(request, 'core/correos/admin_correo_form.html')

@admin_required
def admin_correo_editar(request, pk):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        messages.error(request, 'No se ha identificado la base de datos de la empresa.')
        return redirect('dashboard')
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT id, tipo, titulo, cuerpo FROM configuracion_correos WHERE id = %s", [pk])
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Configuración no encontrada.')
            return redirect('admin_correos_lista')
        if request.method == 'POST':
            titulo = request.POST.get('titulo')
            cuerpo = request.POST.get('cuerpo')
            if not titulo or not cuerpo:
                messages.error(request, 'Título y cuerpo son obligatorios.')
                return render(request, 'core/correos/admin_correo_form.html', {'correo': {'id': pk, 'tipo': row[1], 'titulo': titulo, 'cuerpo': cuerpo}})
            cursor.execute(
                "UPDATE configuracion_correos SET titulo = %s, cuerpo = %s WHERE id = %s",
                [titulo, cuerpo, pk]
            )
            messages.success(request, 'Configuración actualizada correctamente.')
            return redirect('admin_correos_lista')
        correo = {'id': row[0], 'tipo': row[1], 'titulo': row[2], 'cuerpo': row[3]}
    return render(request, 'core/correos/admin_correo_form.html', {'correo': correo})

@admin_required
def admin_correo_eliminar(request, pk):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        messages.error(request, 'No se ha identificado la base de datos de la empresa.')
        return redirect('dashboard')
    with connections[db_name].cursor() as cursor:
        cursor.execute("DELETE FROM configuracion_correos WHERE id = %s", [pk])
    messages.success(request, 'Configuración eliminada correctamente.')
    return redirect('admin_correos_lista')



# ========== USUARIO NORMAL (US) ==========
@usuario_required
def usuario_dashboard(request):
    return render(request, 'core/usuario/dashboard.html')

import tempfile
import os
from datetime import date
from django.core.signing import loads
from django.conf import settings
from django.db import connections
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, TipoDescargaMasivaTerceros, EstadoComprobante
from empresas.models import EFirma
from .decorators import usuario_required
from .forms import PeticionSatForm


@usuario_required
def usuario_peticiones_sat(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    empresa_nombre = request.session.get('empresa_nombre')
    if not db_name or not rfc_empresa or not empresa_nombre:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')

    try:
        efirma = EFirma.objects.using('default').get(empresa=empresa_nombre, estatus='validado')
    except EFirma.DoesNotExist:
        messages.error(request, 'La empresa no tiene una FIEL válida cargada. Contacte al administrador.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = PeticionSatForm(request.POST)
        if form.is_valid():
            tipo = form.cleaned_data['tipo']
            fechainicio = form.cleaned_data['fechainicio']
            fechafinal = form.cleaned_data['fechafinal']
            if fechafinal > date.today():
                messages.error(request, 'La fecha final no puede ser mayor a hoy.')
                return render(request, 'core/usuario/peticiones_sat.html', {'form': form})

            cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
            key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)
            if not os.path.exists(cer_path) or not os.path.exists(key_path):
                messages.error(request, 'Los archivos de la FIEL no existen en el servidor.')
                return render(request, 'core/usuario/peticiones_sat.html', {'form': form})

            try:
                password = loads(efirma.password)
                with open(cer_path, 'rb') as cer_file, open(key_path, 'rb') as key_file:
                    signer = Signer.load(
                        certificate=cer_file.read(),
                        key=key_file.read(),
                        password=password
                    )
                sat = SAT(signer=signer)
                if tipo == 'R':
                    respuesta = sat.recover_comprobante_received_request(
                        fecha_inicial=fechainicio,
                        fecha_final=fechafinal,
                        rfc_receptor=signer.rfc,
                        tipo_solicitud=TipoDescargaMasivaTerceros.CFDI,
                        estado_comprobante=EstadoComprobante.VIGENTE
                    )
                else:  # tipo == 'E'
                    respuesta = sat.recover_comprobante_emitted_request(
                        fecha_inicial=fechainicio,
                        fecha_final=fechafinal,
                        rfc_emisor=signer.rfc,
                        tipo_solicitud=TipoDescargaMasivaTerceros.CFDI,
                        estado_comprobante=EstadoComprobante.VIGENTE
                    )

                print(respuesta)
                # Guardar petición en la base de datos de la empresa
                with connections[db_name].cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO peticiones_sat 
                        (idpeticion, estatuspeticion, fechainicio, fechafinal, rfc, CodEstatus, Mensaje, RfcSolicitante, tipo, idusuario_central)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [
                        respuesta['IdSolicitud'],
                        0,  # pendiente de descarga
                        fechainicio,
                        fechafinal,
                        rfc_empresa,
                        respuesta.get('CodEstatus', ''),
                        respuesta.get('Mensaje', ''),
                        respuesta.get('RfcSolicitante', ''),
                        tipo,
                        request.session.get('user_id')
                    ])
                messages.success(request, f'Solicitud de {"Recibidas" if tipo=="R" else "Emitidas"} creada. ID: {respuesta["IdSolicitud"]}')
                return redirect('usuario_peticiones_sat')
            except Exception as e:
                messages.error(request, f'Error en la petición: {str(e)}')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = PeticionSatForm()

    # Obtener listado de peticiones (ambos tipos)
    peticiones = []
    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT idpeticion, fechainicio, fechafinal, CodEstatus, Mensaje, created_at, tipo
            FROM peticiones_sat
            WHERE rfc = %s
            ORDER BY created_at DESC
        """, [rfc_empresa])
        for row in cursor.fetchall():
            peticiones.append({
                'idpeticion': row[0],
                'fechainicio': row[1],
                'fechafinal': row[2],
                'CodEstatus': row[3],
                'Mensaje': row[4],
                'created_at': row[5],
                'tipo': row[6],
            })
    return render(request, 'core/usuario/peticiones_sat.html', {
        'form': form,
        'peticiones': peticiones
    })




from django.db import connections
from datetime import date
from .forms import FechasForm

@usuario_required
def usuario_recibidas_2(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')

    # Tabla fija para recibidos
    tabla = "cfdi_recibido"

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if not fecha_inicio and not fecha_fin:
        hoy = date.today()
        fecha_inicio = hoy.replace(day=1).isoformat()
        fecha_fin = hoy.isoformat()
        form = FechasForm(initial={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
    else:
        form = FechasForm(request.GET)

    where_clause = ""
    params = [rfc_empresa]
    print(fecha_inicio)
    print(fecha_fin)
    if fecha_inicio:
        where_clause += " AND fecha_comprobante >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        where_clause += " AND fecha_comprobante <= %s"
        params.append(fecha_fin)

    with connections[db_name].cursor() as cursor:
        # Datos de la tabla
        cursor.execute(f"""
            SELECT uuid, fecha_comprobante, rfc_emisor, rfc_receptor, total,
                   moneda, forma_pago, metodo_pago, fecha_timbrado, saldo_pendiente
            FROM {tabla}
            WHERE rfc_receptor = %s {where_clause}
            ORDER BY fecha_comprobante DESC
        """, params)
        cfdis = cursor.fetchall()

        # Resumen
        cursor.execute(f"""
            SELECT COUNT(*) as total, SUM(CAST(total AS DECIMAL(18,2))) as suma_total
            FROM {tabla}
            WHERE rfc_receptor = %s {where_clause}
        """, params)
        resumen = cursor.fetchone()
        total_registros = resumen[0] or 0
        suma_total = float(resumen[1] or 0)

        # Datos para gráficos por mes
        cursor.execute(f"""
            SELECT
                CONCAT(YEAR(fecha_comprobante), '-', LPAD(MONTH(fecha_comprobante), 2, '0')) as mes,
                COUNT(*) as cantidad,
                SUM(CAST(total AS DECIMAL(18,2))) as monto
            FROM {tabla}
            WHERE rfc_receptor = %s AND fecha_comprobante IS NOT NULL {where_clause}
            GROUP BY YEAR(fecha_comprobante), MONTH(fecha_comprobante)
            ORDER BY mes
        """, params)
        datos_meses = cursor.fetchall()

    meses = [row[0] for row in datos_meses]
    cantidades = [row[1] for row in datos_meses]
    montos = [float(row[2]) for row in datos_meses]

    # Formatear datos para la tabla
    data = []
    for row in cfdis:
        data.append({
            'uuid': row[0],
            'fecha': row[1].strftime('%d/%m/%Y') if row[1] else '',
            'rfc_emisor': row[2],
            'rfc_receptor': row[3],
            'total': f"{float(row[4]):.2f}",
            'moneda': row[5],
            'forma_pago': row[6],
            'metodo_pago': row[7],
            'fecha_timbrado': row[8] if row[8] else '',
            'saldo_pendiente': f"{float(row[9]):.2f}"
        })

    context = {
        'form': form,
        'cfdis': data,
        'total_registros': total_registros,
        'suma_total': suma_total,
        'meses': meses,
        'cantidades': cantidades,
        'montos': montos,
    }
    print(f"DEBUG: total_registros = {total_registros}")
    print(f"DEBUG: primeros 3 cfdis = {data[:3] if data else []}")
    return render(request, 'core/usuario/recibidas.html', context)

from django.http import JsonResponse
import traceback

@usuario_required
def usuario_recibidas(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')

    tabla = "cfdi_recibido"
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if not fecha_inicio and not fecha_fin:
        hoy = date.today()
        fecha_inicio = hoy.replace(day=1).isoformat()
        fecha_fin = hoy.isoformat()
        form = FechasForm(initial={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
    else:
        form = FechasForm(request.GET)

    where_clause = ""
    params = [rfc_empresa]
    if fecha_inicio:
        where_clause += " AND fecha_comprobante >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        where_clause += " AND fecha_comprobante <= %s"
        params.append(fecha_fin)

    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(f"""
                SELECT uuid, fecha_comprobante, rfc_emisor, rfc_receptor, total,
                       moneda, forma_pago, metodo_pago, fecha_timbrado, saldo_pendiente
                FROM {tabla}
                WHERE rfc_receptor = %s {where_clause}
                ORDER BY fecha_comprobante DESC
            """, params)
            cfdis = cursor.fetchall()

            cursor.execute(f"""
                SELECT COUNT(*) as total, SUM(CAST(total AS DECIMAL(18,2))) as suma_total
                FROM {tabla}
                WHERE rfc_receptor = %s {where_clause}
            """, params)
            resumen = cursor.fetchone()
            total_registros = resumen[0] or 0
            suma_total = float(resumen[1] or 0)

            cursor.execute(f"""
                SELECT
                    CONCAT(YEAR(fecha_comprobante), '-', LPAD(MONTH(fecha_comprobante), 2, '0')) as mes,
                    COUNT(*) as cantidad,
                    SUM(CAST(total AS DECIMAL(18,2))) as monto
                FROM {tabla}
                WHERE rfc_receptor = %s AND fecha_comprobante IS NOT NULL {where_clause}
                GROUP BY YEAR(fecha_comprobante), MONTH(fecha_comprobante)
                ORDER BY mes
            """, params)
            datos_meses = cursor.fetchall()
    except Exception as e:
        print(f"Error en consulta: {e}")
        traceback.print_exc()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        messages.error(request, 'Error al consultar los datos')
        return redirect('dashboard')

    meses = [row[0] for row in datos_meses]
    cantidades = [row[1] for row in datos_meses]
    montos = [float(row[2]) for row in datos_meses]

    # Formatear datos
    data = []
    for row in cfdis:
        fecha_timbrado = row[8]
        if fecha_timbrado:
            if hasattr(fecha_timbrado, 'strftime'):
                fecha_timbrado = fecha_timbrado.strftime('%d/%m/%Y %H:%M')
            else:
                fecha_timbrado = str(fecha_timbrado)
        else:
            fecha_timbrado = ''
        data.append({
            'uuid': row[0],
            'fecha': row[1].strftime('%d/%m/%Y') if row[1] else '',
            'rfc_emisor': row[2],
            'rfc_receptor': row[3],
            'total': f"{float(row[4]):.2f}",
            'moneda': row[5],
            'forma_pago': row[6],
            'metodo_pago': row[7],
            'fecha_timbrado': fecha_timbrado,
            'saldo_pendiente': f"{float(row[9]):.2f}"
        })

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'data': data,
            'total': total_registros,
            'suma_total': suma_total,
            'meses': meses,
            'cantidades': cantidades,
            'montos': montos,
        })

    context = {
        'form': form,
        'total_registros': total_registros,
        'suma_total': suma_total,
        'meses': meses,
        'cantidades': cantidades,
        'montos': montos,
        'data_json': data,
    }
    return render(request, 'core/usuario/recibidas.html', context)


import os
import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, date
import base64
import glob
from django.db import connections
from django.core.signing import loads
from django.conf import settings
from django.http import JsonResponse
from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, EstadoSolicitud
from .decorators import usuario_required

# Diccionarios de códigos (mismos del comando original)
FORMAS_PAGO = {
    '01': '01 - Efectivo', '02': '02 - Cheque nominativo', '03': '03 - Transferencia electrónica de fondos',
    '04': '04 - Tarjeta de crédito', '05': '05 - Monedero electrónico', '06': '06 - Dinero electrónico',
    '08': '08 - Vales de despensa', '12': '12 - Dación en pago', '13': '13 - Pago por subrogación',
    '14': '14 - Pago por consignación', '15': '15 - Condonación', '17': '17 - Compensación',
    '23': '23 - Novación', '24': '24 - Confusión', '25': '25 - Remisión de deuda',
    '26': '26 - Prescripción o caducidad', '27': '27 - A satisfacción del acreedor',
    '28': '28 - Tarjeta de débito', '29': '29 - Tarjeta de servicios', '30': '30 - Aplicación de anticipos',
    '31': '31 - Intermediario pagos', '99': '99 - Por definir'
}
METODOS_PAGO = {
    'PUE': 'PUE - Pago en una sola exhibición', 'PPD': 'PPD - Pago en parcialidades o diferido'
}


@usuario_required
def usuario_revisar_peticiones(request):
    # ========== Funciones auxiliares (definidas primero) ==========
    def extraer_datos_factura(xml_path, rfc_receptor):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4',
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                'pago10': 'http://www.sat.gob.mx/Pagos',
                'pago20': 'http://www.sat.gob.mx/Pagos20'
            }
            receptor = root.find('cfdi:Receptor', ns)
            if receptor is None or receptor.get('Rfc') != rfc_receptor:
                return {'error': 'Receptor no coincide'}
            complemento_pago = root.find('.//pago10:Pagos', ns) or root.find('.//pago20:Pagos', ns)
            if complemento_pago is not None:
                return procesar_complemento_pago(root, ns, rfc_receptor)
            else:
                return procesar_factura_normal(root, ns, rfc_receptor)
        except ET.ParseError as e:
            return {'error': f'XML inválido: {e}'}
        except Exception as e:
            return {'error': str(e)}

    def procesar_factura_normal(root, ns, rfc_receptor):
        emisor = root.find('cfdi:Emisor', ns)
        rfc_emisor = emisor.get('Rfc') if emisor is not None else ''
        nombre_emisor = emisor.get('Nombre') if emisor is not None else ''
        subtotal = root.get('SubTotal', '0.00')
        total = root.get('Total', '0.00')
        iva = '0.00'
        impuestos = root.find('cfdi:Impuestos', ns)
        if impuestos is not None:
            traslados = impuestos.find('cfdi:Traslados', ns)
            if traslados is not None:
                for traslado in traslados.findall('cfdi:Traslado', ns):
                    if traslado.get('Impuesto') == '002':
                        iva = traslado.get('Importe', '0.00')
                        break
        forma_pago_cod = root.get('FormaPago', '99')
        forma_pago_desc = FORMAS_PAGO.get(forma_pago_cod, f"{forma_pago_cod} - Desconocido")
        metodo_pago_cod = root.get('MetodoPago', 'PPD')
        metodo_pago_desc = METODOS_PAGO.get(metodo_pago_cod, f"{metodo_pago_cod} - Desconocido")
        datos = {
            'rfc_emisor': rfc_emisor, 'rfc_receptor': rfc_receptor, 'folio': root.get('Folio'), 'uuid': None,
            'fecha_comprobante': root.get('Fecha')[:10] if root.get('Fecha') else None, 'total': total, 'iva': iva,
            'suma': f"{float(subtotal) + float(iva):.2f}", 'status_sat': 'R', 'moneda': root.get('Moneda', 'MXN'),
            'tipo_cambio': root.get('TipoCambio', '1.0'), 'forma_pago': forma_pago_desc, 'metodo_pago': metodo_pago_desc,
            'fecha_timbrado': None, 'saldo_pendiente': total, 'nombre_emisor': nombre_emisor
        }
        timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
        if timbre is not None:
            datos['uuid'] = timbre.get('UUID')
            datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None
        return datos

    def procesar_complemento_pago(root, ns, rfc_receptor):
        emisor = root.find('cfdi:Emisor', ns)
        rfc_emisor = emisor.get('Rfc') if emisor is not None else ''
        nombre_emisor = emisor.get('Nombre') if emisor is not None else ''
        pagos = root.find('.//pago10:Pagos', ns) or root.find('.//pago20:Pagos', ns)
        monto_total = '0.00'
        fecha_pago = None
        num_operacion = ''
        uuids_relacionados = []
        if pagos is not None:
            pago = pagos.find('.//pago10:Pago', ns) or pagos.find('.//pago20:Pago', ns)
            if pago is not None:
                monto_total = pago.get('Monto', '0.00')
                fecha_pago = pago.get('FechaPago')
                num_operacion = pago.get('NumOperacion', '')
                doctos = pago.findall('.//pago10:DoctoRelacionado', ns) or pago.findall('.//pago20:DoctoRelacionado', ns)
                for docto in doctos:
                    uuid = docto.get('IdDocumento')
                    if uuid:
                        uuids_relacionados.append(uuid)
        forma_pago_cod = root.get('FormaPago', '99')
        forma_pago_desc = FORMAS_PAGO.get(forma_pago_cod, f"{forma_pago_cod} - Desconocido")
        datos = {
            'rfc_emisor': rfc_emisor, 'rfc_receptor': rfc_receptor, 'folio': root.get('Folio') or f"CP-{num_operacion}",
            'uuid': None, 'fecha_comprobante': fecha_pago[:10] if fecha_pago else root.get('Fecha')[:10] if root.get('Fecha') else None,
            'total': monto_total, 'moneda': root.get('Moneda', 'MXN'), 'forma_pago': forma_pago_desc,
            'uso_cfdi': receptor.get('UsoCFDI', '') if (receptor := root.find('cfdi:Receptor', ns)) else '',
            'uudirelacion': ','.join(uuids_relacionados), 'iva': '0.00', 'suma': monto_total, 'status_sat': 'R',
            'tipo_cambio': root.get('TipoCambio', '1.0'), 'metodo_pago': '', 'fecha_timbrado': None,
            'saldo_pendiente': monto_total, 'nombre_emisor': nombre_emisor
        }
        timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
        if timbre is not None:
            datos['uuid'] = timbre.get('UUID')
            datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None
        return datos

    def insertar_cfdi(db_name, datos, logs):
        print(f"    Insertando CFDI UUID {datos['uuid']}...", flush=True)
        try:
            with connections[db_name].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM cfdi_recibido WHERE uuid = %s", [datos['uuid']])
                if cursor.fetchone()[0] > 0:
                    logs.append(f"    UUID {datos['uuid']} ya existe, omitiendo.")
                    return
                cursor.execute("""
                    INSERT INTO cfdi_recibido (
                        rfc_emisor, rfc_receptor, folio, uuid, fecha_comprobante, total, iva, suma,
                        status_sat, moneda, tipo_cambio, forma_pago, metodo_pago, fecha_timbrado, saldo_pendiente
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    datos['rfc_emisor'], datos['rfc_receptor'], datos['folio'], datos['uuid'],
                    datos['fecha_comprobante'], datos['total'], datos['iva'], datos['suma'],
                    datos['status_sat'], datos['moneda'], datos['tipo_cambio'], datos['forma_pago'],
                    datos['metodo_pago'], datos['fecha_timbrado'], datos['saldo_pendiente']
                ])
            logs.append(f"    CFDI insertado: UUID {datos['uuid']}")
        except Exception as e:
            logs.append(f"    Error insertando CFDI: {str(e)}")

    def registrar_proveedor(db_name, rfc_prov, nombre, rfc_cliente, logs):
        print(f"    Registrando proveedor {rfc_prov}...", flush=True)
        try:
            with connections[db_name].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM proveedores WHERE RFC = %s AND rfc_identy = %s", [rfc_prov, rfc_cliente])
                if cursor.fetchone()[0] > 0:
                    return
                cursor.execute("""
                    INSERT INTO proveedores (RFC, RazonSocial, Estatus, tipoProveedor, Correo, rfc_identy)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [rfc_prov, nombre, 'SinRespuesta', 'Otro', 'generico@generico.com', rfc_cliente])
            logs.append(f"    Proveedor registrado: {rfc_prov} - {nombre}")
            print(f"    Proveedor registrado: {rfc_prov} - {nombre}")
        except Exception as e:
            logs.append(f"    Error registrando proveedor: {str(e)}")
            print(f"    Error registrando proveedor: {str(e)}")

    # ========== Lógica principal ==========
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    empresa_nombre = request.session.get('empresa_nombre')
    if not db_name or not rfc_empresa or not empresa_nombre:
        return JsonResponse({'status': 'error', 'message': 'No se ha identificado la empresa.'})

    print(f"\n=== REVISANDO PETICIONES PARA EMPRESA {empresa_nombre} (RFC: {rfc_empresa}, DB: {db_name}) ===", flush=True)

    try:
        from empresas.models import EFirma
        efirma = EFirma.objects.using('default').get(empresa=empresa_nombre, estatus='validado')
    except EFirma.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'La empresa no tiene una FIEL válida cargada.'})

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT idpeticion, fechainicio
            FROM peticiones_sat
            WHERE rfc = %s AND estatuspeticion = 0 AND tipo = 'R'
        """, [rfc_empresa])
        peticiones_descarga = cursor.fetchall()
        cursor.execute("""
            SELECT idpeticion, fechainicio
            FROM peticiones_sat
            WHERE rfc = %s AND estatuspeticion = 1 AND cargadoxml = 0 AND tipo = 'R'
        """, [rfc_empresa])
        peticiones_procesar = cursor.fetchall()

    logs = []
    total_descargas = 0
    total_procesados = 0

    # ========== 1. Descarga ==========
    print('descarga')
    print(peticiones_descarga)
    for id_peticion, fechainicio in peticiones_descarga:
        logs.append(f"Verificando petición {id_peticion}...")
        try:
            if isinstance(fechainicio, date):
                fecha = fechainicio
            else:
                fecha = datetime.strptime(fechainicio, '%Y-%m-%d').date()
            cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
            key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)
            if not os.path.exists(cer_path) or not os.path.exists(key_path):
                logs.append("  Archivos FIEL no encontrados.")
                continue
            password = loads(efirma.password)
            with open(cer_path, 'rb') as cer_file, open(key_path, 'rb') as key_file:
                signer = Signer.load(certificate=cer_file.read(), key=key_file.read(), password=password)
            sat = SAT(signer=signer)
            respuesta = sat.recover_comprobante_status(id_peticion)
            estado = respuesta.get("EstadoSolicitud")
            if estado == EstadoSolicitud.TERMINADA:
                ids_paquetes = respuesta.get('IdsPaquetes', [])
                if ids_paquetes:
                    folder = os.path.join(settings.MEDIA_ROOT, 'cfdi', rfc_empresa, str(fecha.year), f"{fecha.month:02d}")
                    os.makedirs(folder, exist_ok=True)
                    descargados = 0
                    for id_paquete in ids_paquetes:
                        try:
                            _, paquete_base64 = sat.recover_comprobante_download(id_paquete)
                            if paquete_base64 is None:
                                logs.append(f"  Paquete {id_paquete} no disponible (None).")
                                continue
                            paquete_bytes = base64.b64decode(paquete_base64)
                            zip_path = os.path.join(folder, f"{id_paquete}.zip")
                            with open(zip_path, 'wb') as f:
                                f.write(paquete_bytes)
                            descargados += 1
                            logs.append(f"  Paquete {id_paquete} descargado.")
                        except Exception as e:
                            logs.append(f"  Error descargando paquete {id_paquete}: {str(e)}")
                    if descargados > 0:
                        with connections[db_name].cursor() as cursor_upd:
                            cursor_upd.execute("UPDATE peticiones_sat SET estatuspeticion = 1 WHERE idpeticion = %s", [id_peticion])
                        logs.append(f"  Petición {id_peticion} marcada como descargada ({descargados} paquete(s)).")
                        total_descargas += 1
                    else:
                        logs.append("  No se pudo descargar ningún paquete. La petición permanece pendiente.")
                else:
                    logs.append("  Petición terminada sin paquetes.")
            elif estado in (EstadoSolicitud.ACEPTADA, EstadoSolicitud.EN_PROCESO):
                logs.append("  Petición aún en proceso (no hay respuesta del SAT).")
            else:
                logs.append(f"  Petición falló: {respuesta.get('CodEstatus')} - {respuesta.get('Mensaje')}")
        except Exception as e:
            logs.append(f"  Error en petición {id_peticion}: {str(e)}")

    # ========== 2. Procesamiento XML ==========
    print('xml')
    print(peticiones_procesar)
    for id_peticion, fechainicio in peticiones_procesar:
        print(f"Procesando XML de petición {id_peticion}...", flush=True)
        logs.append(f"Procesando XML de petición {id_peticion}...")
        try:
            if isinstance(fechainicio, date):
                fecha = fechainicio
            else:
                fecha = datetime.strptime(fechainicio, '%Y-%m-%d').date()
            print(fecha)

            zip_folder = os.path.join(settings.MEDIA_ROOT, 'cfdi', rfc_empresa, str(fecha.year), f"{fecha.month:02d}")
            print(zip_folder)
            # Buscar ZIP que empiece con el ID de la petición (puede tener sufijo como _01.zip)
            id_peticion_mayus = id_peticion.upper()  # Convertir a mayúsculas
            zips = glob.glob(os.path.join(zip_folder, f"{id_peticion_mayus}_*.zip"))
            print(zips)
            if not zips:
                logs.append(f"  No se encontraron ZIP para la petición {id_peticion} en {zip_folder}")
                print(f"  No se encontraron ZIP para la petición {id_peticion} en {zip_folder}")
                continue
            for zip_path in zips:
                logs.append(f"  Procesando ZIP: {os.path.basename(zip_path)}")
                temp_dir = tempfile.mkdtemp()
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        zf.extractall(temp_dir)
                    xml_files = []
                    for root_dir, _, files in os.walk(temp_dir):
                        for file in files:
                            if file.lower().endswith('.xml'):
                                xml_files.append(os.path.join(root_dir, file))
                    if not xml_files:
                        logs.append("    No se encontraron XML en el ZIP.")
                    for xml_path in xml_files:
                        datos = extraer_datos_factura(xml_path, rfc_empresa)
                        if datos and 'error' not in datos:
                            insertar_cfdi(db_name, datos, logs)
                            if datos.get('rfc_emisor') and datos.get('nombre_emisor'):
                                registrar_proveedor(db_name, datos['rfc_emisor'], datos['nombre_emisor'], rfc_empresa, logs)
                        else:
                            error_msg = datos.get('error', 'Desconocido') if datos else 'No se extrajeron datos'
                            logs.append(f"    Error al extraer datos de {os.path.basename(xml_path)}: {error_msg}")
                except Exception as e:
                    logs.append(f"    Error procesando ZIP: {str(e)}")
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            # Marcar como procesado (cargadoxml = 1) solo si se encontraron ZIPs
            if zips:
                with connections[db_name].cursor() as cursor_upd:
                    cursor_upd.execute("UPDATE peticiones_sat SET cargadoxml = 1 WHERE idpeticion = %s", [id_peticion])
                logs.append("  Petición marcada como procesada (XML cargados).")
                total_procesados += 1
        except Exception as e:
            logs.append(f"  Error procesando petición {id_peticion}: {str(e)}")

    if total_descargas == 0 and total_procesados == 0:
        status = 'warning'
        message = 'No se encontraron peticiones pendientes o no se pudo descargar ningún paquete.'
    else:
        status = 'ok'
        message = f'Proceso completado. Descargas: {total_descargas}, XML procesados: {total_procesados}.'

    return JsonResponse({'status': status, 'message': message, 'logs': logs})






@usuario_required
def usuario_revisar_peticiones_emitidas(request):
    # ========== Funciones auxiliares ==========
    def extraer_datos_factura_emitida(xml_path, rfc_emisor):
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            ns = {
                'cfdi': 'http://www.sat.gob.mx/cfd/4',
                'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital',
                'pago10': 'http://www.sat.gob.mx/Pagos',
                'pago20': 'http://www.sat.gob.mx/Pagos20'
            }
            # Verificar que el emisor coincide con el RFC de la empresa
            emisor = root.find('cfdi:Emisor', ns)
            if emisor is None or emisor.get('Rfc') != rfc_emisor:
                return {'error': 'Emisor no coincide'}
            complemento_pago = root.find('.//pago10:Pagos', ns) or root.find('.//pago20:Pagos', ns)
            if complemento_pago is not None:
                return procesar_complemento_pago_emitida(root, ns, rfc_emisor)
            else:
                return procesar_factura_normal_emitida(root, ns, rfc_emisor)
        except ET.ParseError as e:
            return {'error': f'XML inválido: {e}'}
        except Exception as e:
            return {'error': str(e)}

    def procesar_factura_normal_emitida(root, ns, rfc_emisor):
        emisor = root.find('cfdi:Emisor', ns)
        rfc_emisor_xml = emisor.get('Rfc') if emisor is not None else ''
        nombre_emisor = emisor.get('Nombre') if emisor is not None else ''
        receptor = root.find('cfdi:Receptor', ns)
        rfc_receptor = receptor.get('Rfc') if receptor is not None else ''
        nombre_receptor = receptor.get('Nombre') if receptor is not None else ''
        subtotal = root.get('SubTotal', '0.00')
        total = root.get('Total', '0.00')
        iva = '0.00'
        impuestos = root.find('cfdi:Impuestos', ns)
        if impuestos is not None:
            traslados = impuestos.find('cfdi:Traslados', ns)
            if traslados is not None:
                for traslado in traslados.findall('cfdi:Traslado', ns):
                    if traslado.get('Impuesto') == '002':
                        iva = traslado.get('Importe', '0.00')
                        break
        forma_pago_cod = root.get('FormaPago', '99')
        forma_pago_desc = FORMAS_PAGO.get(forma_pago_cod, f"{forma_pago_cod} - Desconocido")
        metodo_pago_cod = root.get('MetodoPago', 'PPD')
        metodo_pago_desc = METODOS_PAGO.get(metodo_pago_cod, f"{metodo_pago_cod} - Desconocido")
        datos = {
            'rfc_emisor': rfc_emisor_xml,
            'rfc_receptor': rfc_receptor,
            'folio': root.get('Folio'),
            'uuid': None,
            'fecha_comprobante': root.get('Fecha')[:10] if root.get('Fecha') else None,
            'total': total,
            'iva': iva,
            'suma': f"{float(subtotal) + float(iva):.2f}",
            'status_sat': 'R',
            'moneda': root.get('Moneda', 'MXN'),
            'tipo_cambio': root.get('TipoCambio', '1.0'),
            'forma_pago': forma_pago_desc,
            'metodo_pago': metodo_pago_desc,
            'fecha_timbrado': None,
            'saldo_pendiente': total,
            'nombre_emisor': nombre_emisor,
            'nombre_receptor': nombre_receptor,
            'rfc_receptor': rfc_receptor,
        }
        timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
        if timbre is not None:
            datos['uuid'] = timbre.get('UUID')
            datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None
        return datos

    def procesar_complemento_pago_emitida(root, ns, rfc_emisor):
        # Similar a procesar_complemento_pago pero para emitidos
        emisor = root.find('cfdi:Emisor', ns)
        rfc_emisor_xml = emisor.get('Rfc') if emisor is not None else ''
        nombre_emisor = emisor.get('Nombre') if emisor is not None else ''
        receptor = root.find('cfdi:Receptor', ns)
        rfc_receptor = receptor.get('Rfc') if receptor is not None else ''
        nombre_receptor = receptor.get('Nombre') if receptor is not None else ''
        pagos = root.find('.//pago10:Pagos', ns) or root.find('.//pago20:Pagos', ns)
        monto_total = '0.00'
        fecha_pago = None
        num_operacion = ''
        uuids_relacionados = []
        if pagos is not None:
            pago = pagos.find('.//pago10:Pago', ns) or pagos.find('.//pago20:Pago', ns)
            if pago is not None:
                monto_total = pago.get('Monto', '0.00')
                fecha_pago = pago.get('FechaPago')
                num_operacion = pago.get('NumOperacion', '')
                doctos = pago.findall('.//pago10:DoctoRelacionado', ns) or pago.findall('.//pago20:DoctoRelacionado', ns)
                for docto in doctos:
                    uuid = docto.get('IdDocumento')
                    if uuid:
                        uuids_relacionados.append(uuid)
        forma_pago_cod = root.get('FormaPago', '99')
        forma_pago_desc = FORMAS_PAGO.get(forma_pago_cod, f"{forma_pago_cod} - Desconocido")
        datos = {
            'rfc_emisor': rfc_emisor_xml,
            'rfc_receptor': rfc_receptor,
            'folio': root.get('Folio') or f"CP-{num_operacion}",
            'uuid': None,
            'fecha_comprobante': fecha_pago[:10] if fecha_pago else root.get('Fecha')[:10] if root.get('Fecha') else None,
            'total': monto_total,
            'moneda': root.get('Moneda', 'MXN'),
            'forma_pago': forma_pago_desc,
            'uso_cfdi': receptor.get('UsoCFDI', '') if receptor else '',
            'uudirelacion': ','.join(uuids_relacionados),
            'iva': '0.00',
            'suma': monto_total,
            'status_sat': 'R',
            'tipo_cambio': root.get('TipoCambio', '1.0'),
            'metodo_pago': '',
            'fecha_timbrado': None,
            'saldo_pendiente': monto_total,
            'nombre_emisor': nombre_emisor,
            'nombre_receptor': nombre_receptor
        }
        timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
        if timbre is not None:
            datos['uuid'] = timbre.get('UUID')
            datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None
        return datos

    def insertar_cfdi_emitido(db_name, datos, logs):
        print(f"    Insertando CFDI emitido UUID {datos['uuid']}...", flush=True)
        try:
            with connections[db_name].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM cfdi_emitidos WHERE uuid = %s", [datos['uuid']])
                if cursor.fetchone()[0] > 0:
                    logs.append(f"    UUID {datos['uuid']} ya existe, omitiendo.")
                    return
                cursor.execute("""
                    INSERT INTO cfdi_emitidos (
                        rfc_emisor, rfc_receptor, folio, uuid, fecha_comprobante, total, iva, suma,
                        status_sat, moneda, tipo_cambio, forma_pago, metodo_pago, fecha_timbrado, saldo_pendiente
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    datos['rfc_emisor'], datos['rfc_receptor'], datos['folio'], datos['uuid'],
                    datos['fecha_comprobante'], datos['total'], datos['iva'], datos['suma'],
                    datos['status_sat'], datos['moneda'], datos['tipo_cambio'], datos['forma_pago'],
                    datos['metodo_pago'], datos['fecha_timbrado'], datos['saldo_pendiente']
                ])
            logs.append(f"    CFDI emitido insertado: UUID {datos['uuid']}")
        except Exception as e:
            logs.append(f"    Error insertando CFDI emitido: {str(e)}")

    def registrar_cliente(db_name, rfc_cliente, nombre, rfc_empresa, logs):
        """Registra un cliente en la tabla clientes (si no existe para esta empresa)."""
        print(f"    Registrando cliente {rfc_cliente}...", flush=True)
        try:
            with connections[db_name].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM clientes WHERE RFC = %s AND rfc_identy = %s", [rfc_cliente, rfc_empresa])
                if cursor.fetchone()[0] > 0:
                    print("      Cliente ya existe.", flush=True)
                    return
                cursor.execute("""
                    INSERT INTO clientes (RFC, RazonSocial, Estatus, tipoProveedor, Correo, rfc_identy)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, [rfc_cliente, nombre, 'SinRespuesta', 'Otro', 'generico@generico.com', rfc_empresa])
            logs.append(f"    Cliente registrado: {rfc_cliente} - {nombre}")
            print(f"    Cliente registrado: {rfc_cliente} - {nombre}", flush=True)
        except Exception as e:
            logs.append(f"    Error registrando cliente: {str(e)}")
            print(f"    Error registrando cliente: {str(e)}", flush=True)

    # ========== Lógica principal ==========
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    empresa_nombre = request.session.get('empresa_nombre')
    if not db_name or not rfc_empresa or not empresa_nombre:
        return JsonResponse({'status': 'error', 'message': 'No se ha identificado la empresa.'})

    print(f"\n=== REVISANDO PETICIONES EMITIDAS PARA EMPRESA {empresa_nombre} (RFC: {rfc_empresa}, DB: {db_name}) ===", flush=True)

    try:
        from empresas.models import EFirma
        efirma = EFirma.objects.using('default').get(empresa=empresa_nombre, estatus='validado')
    except EFirma.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'La empresa no tiene una FIEL válida cargada.'})

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT idpeticion, fechainicio
            FROM peticiones_sat
            WHERE rfc = %s AND estatuspeticion = 0 AND tipo = 'E'
        """, [rfc_empresa])
        peticiones_descarga = cursor.fetchall()
        cursor.execute("""
            SELECT idpeticion, fechainicio
            FROM peticiones_sat
            WHERE rfc = %s AND estatuspeticion = 1 AND cargadoxml = 0 AND tipo = 'E'
        """, [rfc_empresa])
        peticiones_procesar = cursor.fetchall()

    logs = []
    total_descargas = 0
    total_procesados = 0

    # ========== 1. Descarga ==========
    for id_peticion, fechainicio in peticiones_descarga:
        logs.append(f"Verificando petición emitida {id_peticion}...")
        try:
            if isinstance(fechainicio, date):
                fecha = fechainicio
            else:
                fecha = datetime.strptime(fechainicio, '%Y-%m-%d').date()
            cer_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_cer)
            key_path = os.path.join(settings.MEDIA_ROOT, efirma.archivo_key)
            if not os.path.exists(cer_path) or not os.path.exists(key_path):
                logs.append("  Archivos FIEL no encontrados.")
                continue
            password = loads(efirma.password)
            with open(cer_path, 'rb') as cer_file, open(key_path, 'rb') as key_file:
                signer = Signer.load(certificate=cer_file.read(), key=key_file.read(), password=password)
            sat = SAT(signer=signer)
            respuesta = sat.recover_comprobante_status(id_peticion)
            estado = respuesta.get("EstadoSolicitud")
            if estado == EstadoSolicitud.TERMINADA:
                ids_paquetes = respuesta.get('IdsPaquetes', [])
                if ids_paquetes:
                    folder = os.path.join(settings.MEDIA_ROOT, 'cfdi', rfc_empresa, str(fecha.year), f"{fecha.month:02d}")
                    os.makedirs(folder, exist_ok=True)
                    descargados = 0
                    for id_paquete in ids_paquetes:
                        try:
                            _, paquete_base64 = sat.recover_comprobante_download(id_paquete)
                            if paquete_base64 is None:
                                logs.append(f"  Paquete {id_paquete} no disponible (None).")
                                continue
                            paquete_bytes = base64.b64decode(paquete_base64)
                            zip_path = os.path.join(folder, f"{id_paquete}.zip")
                            with open(zip_path, 'wb') as f:
                                f.write(paquete_bytes)
                            descargados += 1
                            logs.append(f"  Paquete {id_paquete} descargado.")
                        except Exception as e:
                            logs.append(f"  Error descargando paquete {id_paquete}: {str(e)}")
                    if descargados > 0:
                        with connections[db_name].cursor() as cursor_upd:
                            cursor_upd.execute("UPDATE peticiones_sat SET estatuspeticion = 1 WHERE idpeticion = %s", [id_peticion])
                        logs.append(f"  Petición emitida {id_peticion} marcada como descargada ({descargados} paquete(s)).")
                        total_descargas += 1
                    else:
                        logs.append("  No se pudo descargar ningún paquete. La petición permanece pendiente.")
                else:
                    logs.append("  Petición terminada sin paquetes.")
            elif estado in (EstadoSolicitud.ACEPTADA, EstadoSolicitud.EN_PROCESO):
                logs.append("  Petición aún en proceso (no hay respuesta del SAT).")
            else:
                logs.append(f"  Petición falló: {respuesta.get('CodEstatus')} - {respuesta.get('Mensaje')}")
        except Exception as e:
            logs.append(f"  Error en petición {id_peticion}: {str(e)}")

    # ========== 2. Procesamiento XML ==========
    for id_peticion, fechainicio in peticiones_procesar:
        logs.append(f"Procesando XML de petición emitida {id_peticion}...")
        try:
            if isinstance(fechainicio, date):
                fecha = fechainicio
            else:
                fecha = datetime.strptime(fechainicio, '%Y-%m-%d').date()
            zip_folder = os.path.join(settings.MEDIA_ROOT, 'cfdi', rfc_empresa, str(fecha.year), f"{fecha.month:02d}")
            id_peticion_mayus = id_peticion.upper()
            zips = glob.glob(os.path.join(zip_folder, f"{id_peticion_mayus}_*.zip"))
            if not zips:
                logs.append(f"  No se encontraron ZIP para la petición {id_peticion} en {zip_folder}")
                continue
            for zip_path in zips:
                logs.append(f"  Procesando ZIP: {os.path.basename(zip_path)}")
                temp_dir = tempfile.mkdtemp()
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        zf.extractall(temp_dir)
                    xml_files = []
                    for root_dir, _, files in os.walk(temp_dir):
                        for file in files:
                            if file.lower().endswith('.xml'):
                                xml_files.append(os.path.join(root_dir, file))
                    if not xml_files:
                        logs.append("    No se encontraron XML en el ZIP.")
                    for xml_path in xml_files:
                        datos = extraer_datos_factura_emitida(xml_path, rfc_empresa)
                        if datos and 'error' not in datos:
                            insertar_cfdi_emitido(db_name, datos, logs)
                            if datos.get('rfc_receptor') and datos.get('nombre_receptor'):
                                registrar_cliente(db_name, datos['rfc_receptor'], datos['nombre_receptor'], rfc_empresa, logs)
                        else:
                            error_msg = datos.get('error', 'Desconocido') if datos else 'No se extrajeron datos'
                            logs.append(f"    Error al extraer datos de {os.path.basename(xml_path)}: {error_msg}")
                except Exception as e:
                    logs.append(f"    Error procesando ZIP: {str(e)}")
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            if zips:
                with connections[db_name].cursor() as cursor_upd:
                    cursor_upd.execute("UPDATE peticiones_sat SET cargadoxml = 1 WHERE idpeticion = %s", [id_peticion])
                logs.append("  Petición emitida marcada como procesada (XML cargados).")
                total_procesados += 1
        except Exception as e:
            logs.append(f"  Error procesando petición {id_peticion}: {str(e)}")

    if total_descargas == 0 and total_procesados == 0:
        status = 'warning'
        message = 'No se encontraron peticiones emitidas pendientes o no se pudo descargar ningún paquete.'
    else:
        status = 'ok'
        message = f'Proceso completado. Descargas: {total_descargas}, XML procesados: {total_procesados}.'

    return JsonResponse({'status': status, 'message': message, 'logs': logs})




@usuario_required
def usuario_emitidas(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
        messages.error(request, 'No se ha identificado la empresa asociada a su cuenta.')
        return redirect('dashboard')

    tabla = "cfdi_emitidos"
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    if not fecha_inicio and not fecha_fin:
        hoy = date.today()
        fecha_inicio = hoy.replace(day=1).isoformat()
        fecha_fin = hoy.isoformat()
        form = FechasForm(initial={'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin})
    else:
        form = FechasForm(request.GET)

    where_clause = ""
    params = [rfc_empresa]
    if fecha_inicio:
        where_clause += " AND fecha_comprobante >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        where_clause += " AND fecha_comprobante <= %s"
        params.append(fecha_fin)

    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(f"""
                SELECT uuid, fecha_comprobante, rfc_emisor, rfc_receptor, total,
                       moneda, forma_pago, metodo_pago, fecha_timbrado, saldo_pendiente
                FROM {tabla}
                WHERE rfc_emisor = %s {where_clause}
                ORDER BY fecha_comprobante DESC
            """, params)
            cfdis = cursor.fetchall()

            cursor.execute(f"""
                SELECT COUNT(*) as total, SUM(CAST(total AS DECIMAL(18,2))) as suma_total
                FROM {tabla}
                WHERE rfc_emisor = %s {where_clause}
            """, params)
            resumen = cursor.fetchone()
            total_registros = resumen[0] or 0
            suma_total = float(resumen[1] or 0)

            cursor.execute(f"""
                SELECT
                    CONCAT(YEAR(fecha_comprobante), '-', LPAD(MONTH(fecha_comprobante), 2, '0')) as mes,
                    COUNT(*) as cantidad,
                    SUM(CAST(total AS DECIMAL(18,2))) as monto
                FROM {tabla}
                WHERE rfc_emisor = %s AND fecha_comprobante IS NOT NULL {where_clause}
                GROUP BY YEAR(fecha_comprobante), MONTH(fecha_comprobante)
                ORDER BY mes
            """, params)
            datos_meses = cursor.fetchall()
    except Exception as e:
        print(f"Error en consulta: {e}")
        traceback.print_exc()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        messages.error(request, 'Error al consultar los datos')
        return redirect('dashboard')

    meses = [row[0] for row in datos_meses]
    cantidades = [row[1] for row in datos_meses]
    montos = [float(row[2]) for row in datos_meses]

    data = []
    for row in cfdis:
        fecha_timbrado = row[8]
        if fecha_timbrado:
            if hasattr(fecha_timbrado, 'strftime'):
                fecha_timbrado = fecha_timbrado.strftime('%d/%m/%Y %H:%M')
            else:
                fecha_timbrado = str(fecha_timbrado)
        else:
            fecha_timbrado = ''
        data.append({
            'uuid': row[0],
            'fecha': row[1].strftime('%d/%m/%Y') if row[1] else '',
            'rfc_emisor': row[2],
            'rfc_receptor': row[3],
            'total': f"{float(row[4]):.2f}",
            'moneda': row[5],
            'forma_pago': row[6],
            'metodo_pago': row[7],
            'fecha_timbrado': fecha_timbrado,
            'saldo_pendiente': f"{float(row[9]):.2f}"
        })

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'data': data,
            'total': total_registros,
            'suma_total': suma_total,
            'meses': meses,
            'cantidades': cantidades,
            'montos': montos,
        })

    context = {
        'form': form,
        'total_registros': total_registros,
        'suma_total': suma_total,
        'meses': meses,
        'cantidades': cantidades,
        'montos': montos,
        'data_json': data,
    }
    return render(request, 'core/usuario/emitidas.html', context)








import csv
import io
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connections

@usuario_required
def proveedores_lista(request):
    """Página principal del listado de proveedores."""
    return render(request, 'core/usuario/proveedores_lista.html')

@usuario_required
def proveedores_data(request):
    """Devuelve JSON con los proveedores del cliente actual para DataTable."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor
            FROM proveedores
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'RFC': row[1] or '',
            'RazonSocial': row[2] or '',
            'Correo': row[3] or '',
            'Correo2': row[4] or '',
            'Correo3': row[5] or '',
            'tipoProveedor': row[6] or '',
        })
    return JsonResponse(data, safe=False)

@usuario_required
def proveedor_detalle(request, pk):
    """Obtiene todos los datos de un proveedor para editar."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
                   nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM proveedores
            WHERE id = %s AND rfc_identy = %s
        """, [pk, rfc_empresa])
        row = cursor.fetchone()
        if not row:
            return JsonResponse({'error': 'Proveedor no encontrado'}, status=404)

    data = {
        'id': row[0],
        'RFC': row[1] or '',
        'RazonSocial': row[2] or '',
        'Correo': row[3] or '',
        'Correo2': row[4] or '',
        'Correo3': row[5] or '',
        'tipoProveedor': row[6] or '',
        'nombre': row[7] or '',
        'apellidoPaterno': row[8] or '',
        'apellidoMaterno': row[9] or '',
        'Nombrecomercial': row[10] or '',
        'tipoPersona': row[11] or '',
        'codigoPostal': row[12] or '',
        'calle': row[13] or '',
        'noInt': row[14] or '',
        'noExt': row[15] or '',
        'colonia': row[16] or '',
        'estado': row[17] or '',
        'municipio': row[18] or '',
        'ciudad': row[19] or '',
        'telefono': row[20] or '',
    }
    return JsonResponse(data)

@usuario_required
@csrf_exempt
def proveedor_actualizar(request, pk):
    """Actualiza los campos editables de un proveedor."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # Leer y decodificar JSON con manejo de errores
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error al leer datos: {str(e)}'}, status=400)

    # Campos editables (nombres exactos de columnas en la base de datos)
    campos = [
        'tipoProveedor', 'nombre', 'apellidoPaterno', 'apellidoMaterno',
        'Nombrecomercial', 'tipoPersona', 'codigoPostal', 'calle', 'noInt',
        'noExt', 'colonia', 'estado', 'municipio', 'ciudad', 'telefono',
        'Correo', 'Correo2', 'Correo3'
    ]
    set_clause = []
    valores = []
    for campo in campos:
        if campo in data:
            valor = data[campo]
            # Si el valor es None o cadena vacía, lo guardamos como None (NULL en BD)
            if valor is None or valor == '':
                valor = None
            set_clause.append(f"`{campo}` = %s")
            valores.append(valor)

    if not set_clause:
        return JsonResponse({'error': 'No hay campos para actualizar'}, status=400)

    sql = f"UPDATE proveedores SET {', '.join(set_clause)} WHERE id = %s AND rfc_identy = %s"
    valores.extend([pk, rfc_empresa])

    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(sql, valores)
            if cursor.rowcount == 0:
                return JsonResponse({'error': 'Proveedor no encontrado o no pertenece a esta empresa'}, status=404)
    except Exception as e:
        # Log del error en consola del servidor
        print(f"Error actualizando proveedor {pk}: {str(e)}")
        traceback.print_exc()
        return JsonResponse({'error': f'Error en base de datos: {str(e)}'}, status=500)

    return JsonResponse({'success': True})





@usuario_required
def proveedores_exportar_plantilla(request):
    """Exporta CSV con RFC, RazonSocial, Correo, Correo2, Correo3 de los proveedores actuales."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        messages.error(request, 'No se ha identificado la empresa.')
        return redirect('usuario_proveedores_lista')

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT RFC, RazonSocial, Correo, Correo2, Correo3
            FROM proveedores
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="proveedores_plantilla.csv"'
    writer = csv.writer(response)
    writer.writerow(['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3'])
    for row in rows:
        writer.writerow(row)
    return response

@usuario_required
@csrf_exempt
def proveedores_importar(request):
    """Importa un archivo CSV y actualiza los proveedores (por RFC)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['file']
    if not archivo.name.endswith('.csv'):
        return JsonResponse({'error': 'Solo se aceptan archivos CSV'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        decoded = archivo.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        # Verificar columnas esperadas
        expected = ['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3']
        if not all(col in reader.fieldnames for col in expected):
            return JsonResponse({'error': 'El archivo no tiene las columnas requeridas'}, status=400)

        actualizados = 0
        with connections[db_name].cursor() as cursor:
            for row in reader:
                rfc = row.get('RFC')
                if not rfc:
                    continue
                # Verificar que el proveedor existe y pertenece a esta empresa
                cursor.execute("SELECT id FROM proveedores WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
                if not cursor.fetchone():
                    continue
                # Actualizar solo los campos de correo y razón social (si se permite)
                sql = """
                    UPDATE proveedores
                    SET RazonSocial = %s, Correo = %s, Correo2 = %s, Correo3 = %s
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [
                    row.get('RazonSocial', ''),
                    row.get('Correo', ''),
                    row.get('Correo2', ''),
                    row.get('Correo3', ''),
                    rfc, rfc_empresa
                ])
                actualizados += cursor.rowcount
        return JsonResponse({'success': True, 'actualizados': actualizados})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)






# ========== PROVEEDORES SIN CFDI ==========
@usuario_required
def proveedores_sin_cfdi_lista(request):
    """Página principal del listado de proveedores sin CFDI."""
    return render(request, 'core/usuario/proveedores_sin_cfdi_lista.html')

@usuario_required
def proveedores_sin_cfdi_data(request):
    """Devuelve JSON con los proveedores sin CFDI del cliente actual."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'RFC': row[1] or '',
            'RazonSocial': row[2] or '',
            'Correo': row[3] or '',
            'Correo2': row[4] or '',
            'Correo3': row[5] or '',
            'tipoProveedor': row[6] or '',
        })
    return JsonResponse(data, safe=False)

@usuario_required
def proveedor_sin_cfdi_detalle(request, pk):
    """Obtiene todos los datos de un proveedor sin CFDI para editar."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
                   nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM proveedores_sin_cfdi
            WHERE id = %s AND rfc_identy = %s
        """, [pk, rfc_empresa])
        row = cursor.fetchone()
        if not row:
            return JsonResponse({'error': 'Proveedor no encontrado'}, status=404)

    data = {
        'id': row[0],
        'RFC': row[1] or '',
        'RazonSocial': row[2] or '',
        'Correo': row[3] or '',
        'Correo2': row[4] or '',
        'Correo3': row[5] or '',
        'tipoProveedor': row[6] or '',
        'nombre': row[7] or '',
        'apellidoPaterno': row[8] or '',
        'apellidoMaterno': row[9] or '',
        'Nombrecomercial': row[10] or '',
        'tipoPersona': row[11] or '',
        'codigoPostal': row[12] or '',
        'calle': row[13] or '',
        'noInt': row[14] or '',
        'noExt': row[15] or '',
        'colonia': row[16] or '',
        'estado': row[17] or '',
        'municipio': row[18] or '',
        'ciudad': row[19] or '',
        'telefono': row[20] or '',
    }
    return JsonResponse(data)

@usuario_required
@csrf_exempt
def proveedor_sin_cfdi_actualizar(request, pk):
    """Actualiza los campos editables de un proveedor sin CFDI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)

    campos = [
        'tipoProveedor', 'nombre', 'apellidoPaterno', 'apellidoMaterno',
        'Nombrecomercial', 'tipoPersona', 'codigoPostal', 'calle', 'noInt',
        'noExt', 'colonia', 'estado', 'municipio', 'ciudad', 'telefono',
        'Correo', 'Correo2', 'Correo3'
    ]
    set_clause = []
    valores = []
    for campo in campos:
        if campo in data:
            valor = data[campo]
            if valor is None or valor == '':
                valor = None
            set_clause.append(f"`{campo}` = %s")
            valores.append(valor)

    if not set_clause:
        return JsonResponse({'error': 'No hay campos para actualizar'}, status=400)

    sql = f"UPDATE proveedores_sin_cfdi SET {', '.join(set_clause)} WHERE id = %s AND rfc_identy = %s"
    valores.extend([pk, rfc_empresa])

    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(sql, valores)
            if cursor.rowcount == 0:
                return JsonResponse({'error': 'Proveedor no encontrado'}, status=404)
    except Exception as e:
        print(f"Error actualizando proveedor sin CFDI {pk}: {e}")
        return JsonResponse({'error': f'Error en base de datos: {str(e)}'}, status=500)

    return JsonResponse({'success': True})

@usuario_required
@csrf_exempt
def proveedor_sin_cfdi_crear(request):
    """Crea un nuevo proveedor sin CFDI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)

    # Campos requeridos: RFC y RazonSocial
    rfc = data.get('RFC')
    razon_social = data.get('RazonSocial')
    if not rfc or not razon_social:
        return JsonResponse({'error': 'RFC y Razón Social son obligatorios'}, status=400)

    # Verificar si ya existe un proveedor con ese RFC para esta empresa
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT id FROM proveedores_sin_cfdi WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
        if cursor.fetchone():
            return JsonResponse({'error': 'Ya existe un proveedor con ese RFC'}, status=400)

        # Insertar nuevo registro
        sql = """
            INSERT INTO proveedores_sin_cfdi
            (RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
             nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
             codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono,
             rfc_identy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            rfc, razon_social,
            data.get('Correo', ''), data.get('Correo2', ''), data.get('Correo3', ''),
            data.get('tipoProveedor', ''),
            data.get('nombre', ''), data.get('apellidoPaterno', ''), data.get('apellidoMaterno', ''),
            data.get('Nombrecomercial', ''), data.get('tipoPersona', ''),
            data.get('codigoPostal', ''), data.get('calle', ''), data.get('noInt', ''),
            data.get('noExt', ''), data.get('colonia', ''), data.get('estado', ''),
            data.get('municipio', ''), data.get('ciudad', ''), data.get('telefono', ''),
            rfc_empresa
        )
        cursor.execute(sql, valores)
        new_id = cursor.lastrowid

    return JsonResponse({'success': True, 'id': new_id})

@usuario_required
def proveedores_sin_cfdi_exportar(request):
    """Exporta CSV con los proveedores sin CFDI del cliente."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        messages.error(request, 'No se ha identificado la empresa.')
        return redirect('usuario_proveedores_sin_cfdi')

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT RFC, RazonSocial, Correo, Correo2, Correo3
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="proveedores_sin_cfdi.csv"'
    writer = csv.writer(response)
    writer.writerow(['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3'])
    for row in rows:
        writer.writerow(row)
    return response

@usuario_required
@csrf_exempt
def proveedores_sin_cfdi_importar(request):
    """Importa CSV y actualiza o crea proveedores sin CFDI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['file']
    if not archivo.name.endswith('.csv'):
        return JsonResponse({'error': 'Solo se aceptan archivos CSV'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        decoded = archivo.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        expected = ['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3']
        if not all(col in reader.fieldnames for col in expected):
            return JsonResponse({'error': 'El archivo no tiene las columnas requeridas'}, status=400)

        creados = 0
        actualizados = 0
        with connections[db_name].cursor() as cursor:
            for row in reader:
                rfc = row.get('RFC')
                if not rfc:
                    continue
                # Verificar si ya existe
                cursor.execute("SELECT id FROM proveedores_sin_cfdi WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
                exists = cursor.fetchone()
                if exists:
                    # Actualizar
                    sql = """
                        UPDATE proveedores_sin_cfdi
                        SET RazonSocial = %s, Correo = %s, Correo2 = %s, Correo3 = %s
                        WHERE RFC = %s AND rfc_identy = %s
                    """
                    cursor.execute(sql, [
                        row.get('RazonSocial', ''),
                        row.get('Correo', ''),
                        row.get('Correo2', ''),
                        row.get('Correo3', ''),
                        rfc, rfc_empresa
                    ])
                    actualizados += cursor.rowcount
                else:
                    # Crear nuevo
                    sql = """
                        INSERT INTO proveedores_sin_cfdi
                        (RFC, RazonSocial, Correo, Correo2, Correo3, rfc_identy)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, [
                        rfc, row.get('RazonSocial', ''),
                        row.get('Correo', ''), row.get('Correo2', ''), row.get('Correo3', ''),
                        rfc_empresa
                    ])
                    creados += 1
        return JsonResponse({'success': True, 'creados': creados, 'actualizados': actualizados})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



# ========== CLIENTES ==========
@usuario_required
def clientes_lista(request):
    """Página principal del listado de clientes."""
    return render(request, 'core/usuario/clientes_lista.html')

@usuario_required
def clientes_data(request):
    """Devuelve JSON con los clientes del cliente actual."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor
            FROM clientes
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'RFC': row[1] or '',
            'RazonSocial': row[2] or '',
            'Correo': row[3] or '',
            'Correo2': row[4] or '',
            'Correo3': row[5] or '',
            'tipoProveedor': row[6] or '',
        })
    return JsonResponse(data, safe=False)

@usuario_required
def cliente_detalle(request, pk):
    """Obtiene todos los datos de un cliente para editar."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
                   nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM clientes
            WHERE id = %s AND rfc_identy = %s
        """, [pk, rfc_empresa])
        row = cursor.fetchone()
        if not row:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

    data = {
        'id': row[0],
        'RFC': row[1] or '',
        'RazonSocial': row[2] or '',
        'Correo': row[3] or '',
        'Correo2': row[4] or '',
        'Correo3': row[5] or '',
        'tipoProveedor': row[6] or '',
        'nombre': row[7] or '',
        'apellidoPaterno': row[8] or '',
        'apellidoMaterno': row[9] or '',
        'Nombrecomercial': row[10] or '',
        'tipoPersona': row[11] or '',
        'codigoPostal': row[12] or '',
        'calle': row[13] or '',
        'noInt': row[14] or '',
        'noExt': row[15] or '',
        'colonia': row[16] or '',
        'estado': row[17] or '',
        'municipio': row[18] or '',
        'ciudad': row[19] or '',
        'telefono': row[20] or '',
    }
    return JsonResponse(data)

@usuario_required
@csrf_exempt
def cliente_actualizar(request, pk):
    """Actualiza los campos editables de un cliente."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)

    campos = [
        'tipoProveedor', 'nombre', 'apellidoPaterno', 'apellidoMaterno',
        'Nombrecomercial', 'tipoPersona', 'codigoPostal', 'calle', 'noInt',
        'noExt', 'colonia', 'estado', 'municipio', 'ciudad', 'telefono',
        'Correo', 'Correo2', 'Correo3'
    ]
    set_clause = []
    valores = []
    for campo in campos:
        if campo in data:
            valor = data[campo]
            if valor is None or valor == '':
                valor = None
            set_clause.append(f"`{campo}` = %s")
            valores.append(valor)

    if not set_clause:
        return JsonResponse({'error': 'No hay campos para actualizar'}, status=400)

    sql = f"UPDATE clientes SET {', '.join(set_clause)} WHERE id = %s AND rfc_identy = %s"
    valores.extend([pk, rfc_empresa])

    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(sql, valores)
            if cursor.rowcount == 0:
                return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    except Exception as e:
        print(f"Error actualizando cliente {pk}: {e}")
        return JsonResponse({'error': f'Error en base de datos: {str(e)}'}, status=500)

    return JsonResponse({'success': True})

@usuario_required
@csrf_exempt
def cliente_crear(request):
    """Crea un nuevo cliente."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)

    rfc = data.get('RFC')
    razon_social = data.get('RazonSocial')
    if not rfc or not razon_social:
        return JsonResponse({'error': 'RFC y Razón Social son obligatorios'}, status=400)

    with connections[db_name].cursor() as cursor:
        # Verificar si ya existe
        cursor.execute("SELECT id FROM clientes WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
        if cursor.fetchone():
            return JsonResponse({'error': 'Ya existe un cliente con ese RFC'}, status=400)

        sql = """
            INSERT INTO clientes
            (RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
             nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
             codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono,
             rfc_identy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            rfc, razon_social,
            data.get('Correo', ''), data.get('Correo2', ''), data.get('Correo3', ''),
            data.get('tipoProveedor', ''),
            data.get('nombre', ''), data.get('apellidoPaterno', ''), data.get('apellidoMaterno', ''),
            data.get('Nombrecomercial', ''), data.get('tipoPersona', ''),
            data.get('codigoPostal', ''), data.get('calle', ''), data.get('noInt', ''),
            data.get('noExt', ''), data.get('colonia', ''), data.get('estado', ''),
            data.get('municipio', ''), data.get('ciudad', ''), data.get('telefono', ''),
            rfc_empresa
        )
        cursor.execute(sql, valores)
        new_id = cursor.lastrowid

    return JsonResponse({'success': True, 'id': new_id})

@usuario_required
def clientes_exportar(request):
    """Exporta CSV con los clientes del cliente actual."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        messages.error(request, 'No se ha identificado la empresa.')
        return redirect('usuario_clientes_lista')

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT RFC, RazonSocial, Correo, Correo2, Correo3
            FROM clientes
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clientes.csv"'
    writer = csv.writer(response)
    writer.writerow(['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3'])
    for row in rows:
        writer.writerow(row)
    return response

@usuario_required
@csrf_exempt
def clientes_importar(request):
    """Importa CSV y actualiza o crea clientes."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['file']
    if not archivo.name.endswith('.csv'):
        return JsonResponse({'error': 'Solo se aceptan archivos CSV'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        decoded = archivo.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        expected = ['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3']
        if not all(col in reader.fieldnames for col in expected):
            return JsonResponse({'error': 'El archivo no tiene las columnas requeridas'}, status=400)

        creados = 0
        actualizados = 0
        with connections[db_name].cursor() as cursor:
            for row in reader:
                rfc = row.get('RFC')
                if not rfc:
                    continue
                # Verificar si ya existe
                cursor.execute("SELECT id FROM clientes WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
                exists = cursor.fetchone()
                if exists:
                    sql = """
                        UPDATE clientes
                        SET RazonSocial = %s, Correo = %s, Correo2 = %s, Correo3 = %s
                        WHERE RFC = %s AND rfc_identy = %s
                    """
                    cursor.execute(sql, [
                        row.get('RazonSocial', ''),
                        row.get('Correo', ''),
                        row.get('Correo2', ''),
                        row.get('Correo3', ''),
                        rfc, rfc_empresa
                    ])
                    actualizados += cursor.rowcount
                else:
                    sql = """
                        INSERT INTO clientes
                        (RFC, RazonSocial, Correo, Correo2, Correo3, rfc_identy)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, [
                        rfc, row.get('RazonSocial', ''),
                        row.get('Correo', ''), row.get('Correo2', ''), row.get('Correo3', ''),
                        rfc_empresa
                    ])
                    creados += 1
        return JsonResponse({'success': True, 'creados': creados, 'actualizados': actualizados})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========== CLIENTES SIN CFDI ==========
@usuario_required
def clientes_sin_cfdi_lista(request):
    """Página principal del listado de clientes sin CFDI."""
    return render(request, 'core/usuario/clientes_sin_cfdi_lista.html')

@usuario_required
def clientes_sin_cfdi_data(request):
    """Devuelve JSON con los clientes sin CFDI del cliente actual."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor
            FROM clientes_sin_cfdi
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'RFC': row[1] or '',
            'RazonSocial': row[2] or '',
            'Correo': row[3] or '',
            'Correo2': row[4] or '',
            'Correo3': row[5] or '',
            'tipoProveedor': row[6] or '',
        })
    return JsonResponse(data, safe=False)

@usuario_required
def cliente_sin_cfdi_detalle(request, pk):
    """Obtiene todos los datos de un cliente sin CFDI para editar."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
                   nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono
            FROM clientes_sin_cfdi
            WHERE id = %s AND rfc_identy = %s
        """, [pk, rfc_empresa])
        row = cursor.fetchone()
        if not row:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)

    data = {
        'id': row[0],
        'RFC': row[1] or '',
        'RazonSocial': row[2] or '',
        'Correo': row[3] or '',
        'Correo2': row[4] or '',
        'Correo3': row[5] or '',
        'tipoProveedor': row[6] or '',
        'nombre': row[7] or '',
        'apellidoPaterno': row[8] or '',
        'apellidoMaterno': row[9] or '',
        'Nombrecomercial': row[10] or '',
        'tipoPersona': row[11] or '',
        'codigoPostal': row[12] or '',
        'calle': row[13] or '',
        'noInt': row[14] or '',
        'noExt': row[15] or '',
        'colonia': row[16] or '',
        'estado': row[17] or '',
        'municipio': row[18] or '',
        'ciudad': row[19] or '',
        'telefono': row[20] or '',
    }
    return JsonResponse(data)

@usuario_required
@csrf_exempt
def cliente_sin_cfdi_actualizar(request, pk):
    """Actualiza los campos editables de un cliente sin CFDI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)

    campos = [
        'tipoProveedor', 'nombre', 'apellidoPaterno', 'apellidoMaterno',
        'Nombrecomercial', 'tipoPersona', 'codigoPostal', 'calle', 'noInt',
        'noExt', 'colonia', 'estado', 'municipio', 'ciudad', 'telefono',
        'Correo', 'Correo2', 'Correo3'
    ]
    set_clause = []
    valores = []
    for campo in campos:
        if campo in data:
            valor = data[campo]
            if valor is None or valor == '':
                valor = None
            set_clause.append(f"`{campo}` = %s")
            valores.append(valor)

    if not set_clause:
        return JsonResponse({'error': 'No hay campos para actualizar'}, status=400)

    sql = f"UPDATE clientes_sin_cfdi SET {', '.join(set_clause)} WHERE id = %s AND rfc_identy = %s"
    valores.extend([pk, rfc_empresa])

    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(sql, valores)
            if cursor.rowcount == 0:
                return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
    except Exception as e:
        print(f"Error actualizando cliente sin CFDI {pk}: {e}")
        return JsonResponse({'error': f'Error en base de datos: {str(e)}'}, status=500)

    return JsonResponse({'success': True})

@usuario_required
@csrf_exempt
def cliente_sin_cfdi_crear(request):
    """Crea un nuevo cliente sin CFDI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        return JsonResponse({'error': f'JSON inválido: {str(e)}'}, status=400)

    rfc = data.get('RFC')
    razon_social = data.get('RazonSocial')
    if not rfc or not razon_social:
        return JsonResponse({'error': 'RFC y Razón Social son obligatorios'}, status=400)

    with connections[db_name].cursor() as cursor:
        # Verificar si ya existe
        cursor.execute("SELECT id FROM clientes_sin_cfdi WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
        if cursor.fetchone():
            return JsonResponse({'error': 'Ya existe un cliente con ese RFC'}, status=400)

        sql = """
            INSERT INTO clientes_sin_cfdi
            (RFC, RazonSocial, Correo, Correo2, Correo3, tipoProveedor,
             nombre, apellidoPaterno, apellidoMaterno, Nombrecomercial, tipoPersona,
             codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad, telefono,
             rfc_identy)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        valores = (
            rfc, razon_social,
            data.get('Correo', ''), data.get('Correo2', ''), data.get('Correo3', ''),
            data.get('tipoProveedor', ''),
            data.get('nombre', ''), data.get('apellidoPaterno', ''), data.get('apellidoMaterno', ''),
            data.get('Nombrecomercial', ''), data.get('tipoPersona', ''),
            data.get('codigoPostal', ''), data.get('calle', ''), data.get('noInt', ''),
            data.get('noExt', ''), data.get('colonia', ''), data.get('estado', ''),
            data.get('municipio', ''), data.get('ciudad', ''), data.get('telefono', ''),
            rfc_empresa
        )
        cursor.execute(sql, valores)
        new_id = cursor.lastrowid

    return JsonResponse({'success': True, 'id': new_id})

@usuario_required
def clientes_sin_cfdi_exportar(request):
    """Exporta CSV con los clientes sin CFDI del cliente actual."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        messages.error(request, 'No se ha identificado la empresa.')
        return redirect('usuario_clientes_sin_cfdi')

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT RFC, RazonSocial, Correo, Correo2, Correo3
            FROM clientes_sin_cfdi
            WHERE rfc_identy = %s
            ORDER BY RazonSocial
        """, [rfc_empresa])
        rows = cursor.fetchall()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clientes_sin_cfdi.csv"'
    writer = csv.writer(response)
    writer.writerow(['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3'])
    for row in rows:
        writer.writerow(row)
    return response

@usuario_required
@csrf_exempt
def clientes_sin_cfdi_importar(request):
    """Importa CSV y actualiza o crea clientes sin CFDI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['file']
    if not archivo.name.endswith('.csv'):
        return JsonResponse({'error': 'Solo se aceptan archivos CSV'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        decoded = archivo.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(decoded))
        expected = ['RFC', 'RazonSocial', 'Correo', 'Correo2', 'Correo3']
        if not all(col in reader.fieldnames for col in expected):
            return JsonResponse({'error': 'El archivo no tiene las columnas requeridas'}, status=400)

        creados = 0
        actualizados = 0
        with connections[db_name].cursor() as cursor:
            for row in reader:
                rfc = row.get('RFC')
                if not rfc:
                    continue
                # Verificar si ya existe
                cursor.execute("SELECT id FROM clientes_sin_cfdi WHERE RFC = %s AND rfc_identy = %s", [rfc, rfc_empresa])
                exists = cursor.fetchone()
                if exists:
                    sql = """
                        UPDATE clientes_sin_cfdi
                        SET RazonSocial = %s, Correo = %s, Correo2 = %s, Correo3 = %s
                        WHERE RFC = %s AND rfc_identy = %s
                    """
                    cursor.execute(sql, [
                        row.get('RazonSocial', ''),
                        row.get('Correo', ''),
                        row.get('Correo2', ''),
                        row.get('Correo3', ''),
                        rfc, rfc_empresa
                    ])
                    actualizados += cursor.rowcount
                else:
                    sql = """
                        INSERT INTO clientes_sin_cfdi
                        (RFC, RazonSocial, Correo, Correo2, Correo3, rfc_identy)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, [
                        rfc, row.get('RazonSocial', ''),
                        row.get('Correo', ''), row.get('Correo2', ''), row.get('Correo3', ''),
                        rfc_empresa
                    ])
                    creados += 1
        return JsonResponse({'success': True, 'creados': creados, 'actualizados': actualizados})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


import re
from datetime import datetime
from django.db import connections
from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os
import PyPDF2
import io
import csv
from .decorators import usuario_required

# ========== OPINIONES DE CUMPLIMIENTO ==========
@usuario_required
def usuario_opiniones(request):
    """Página principal del listado de opiniones."""
    return render(request, 'core/usuario/opiniones_lista.html')

@usuario_required
def usuario_opiniones_data(request):
    """Devuelve JSON con los datos consolidados de todas las entidades."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # Consultas consolidadas
    with connections[db_name].cursor() as cursor:
        # Proveedores
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'proveedor' as tipo
            FROM proveedores
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows = list(cursor.fetchall())

        # Proveedores sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'proveedor_sin_cfdi' as tipo
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        # Clientes
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'cliente' as tipo
            FROM clientes
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        # Clientes sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'cliente_sin_cfdi' as tipo
            FROM clientes_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

    data = []
    for row in rows:
        data.append({
            'rfc': row[0] or '',
            'razon_social': row[1] or '',
            'estatus': row[2] or 'SinRespuesta',
            'fecha_opinion': row[3].strftime('%Y-%m-%d') if row[3] else '',
            'opinion': row[4] or 0,
            'tipo': row[5],
        })
    return JsonResponse(data, safe=False)

def extraer_datos_pdf(pdf_file):
    """Extrae fecha y resultado del PDF de opinión."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        texto = ""
        for page in pdf_reader.pages:
            texto += page.extract_text()
        # Buscar fecha en formato "15 de abril de 2026 a las 11:11 horas"
        patron_fecha = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+a\s+las\s+(\d{1,2}:\d{2})\s+horas'
        match_fecha = re.search(patron_fecha, texto)
        if not match_fecha:
            raise ValueError("No se pudo encontrar la fecha en el PDF")
        dia = int(match_fecha.group(1))
        mes_str = match_fecha.group(2).lower()
        anio = int(match_fecha.group(3))
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = meses.get(mes_str, 1)
        fecha_opinion = datetime(anio, mes, dia).date()

        # Buscar resultado en cadena original: "|...|...|...|P||" o "|...|...|...|N||"
        patron_resultado = r'\|[^|]*\|[^|]*\|[^|]*\|([PN])\|\|'
        match_res = re.search(patron_resultado, texto)
        resultado = 'Positivo' if match_res and match_res.group(1) == 'P' else 'Negativo' if match_res and match_res.group(1) == 'N' else 'SinRespuesta'
        return fecha_opinion, resultado
    except Exception as e:
        raise ValueError(f"Error al procesar PDF: {str(e)}")

@usuario_required
@csrf_exempt
def usuario_opiniones_subir(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'pdf' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['pdf']
    if not archivo.name.endswith('.pdf'):
        return JsonResponse({'error': 'Solo se aceptan archivos PDF'}, status=400)

    rfc = request.POST.get('rfc')
    tipo = request.POST.get('tipo')
    if not rfc or not tipo:
        return JsonResponse({'error': 'Faltan datos (RFC o tipo)'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # 1. Leer el contenido completo del archivo en bytes
    archivo_bytes = archivo.read()
    if not archivo_bytes:
        return JsonResponse({'error': 'El archivo está vacío'}, status=400)

    # 2. Extraer datos del PDF usando los bytes (sin modificar el archivo original)
    try:
        import io
        from PyPDF2 import PdfReader
        import re
        from datetime import datetime

        pdf_io = io.BytesIO(archivo_bytes)
        reader = PdfReader(pdf_io)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text()

        # Buscar fecha en formato "15 de abril de 2026 a las 11:11 horas"
        patron_fecha = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+a\s+las\s+(\d{1,2}:\d{2})\s+horas'
        match_fecha = re.search(patron_fecha, texto)
        if not match_fecha:
            raise ValueError("No se pudo encontrar la fecha en el PDF")
        dia = int(match_fecha.group(1))
        mes_str = match_fecha.group(2).lower()
        anio = int(match_fecha.group(3))
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = meses.get(mes_str, 1)
        fecha_opinion = datetime(anio, mes, dia).date()

        # Buscar resultado en cadena original: "|...|...|...|P||" o "|...|...|...|N||"
        patron_resultado = r'\|[^|]*\|[^|]*\|[^|]*\|([PN])\|\|'
        match_res = re.search(patron_resultado, texto)
        resultado = 'Positivo' if match_res and match_res.group(1) == 'P' else 'Negativo' if match_res and match_res.group(1) == 'N' else 'SinRespuesta'

    except Exception as e:
        return JsonResponse({'error': f'Error al procesar PDF: {str(e)}'}, status=400)

    # 3. Guardar el archivo en media/opinion/<rfc>/<año>/<mes>/
    año = fecha_opinion.year
    mes = fecha_opinion.month
    ruta = os.path.join('opinion', rfc, str(año), f"{mes:02d}")
    nombre_archivo = f"{rfc}_{fecha_opinion.strftime('%Y%m%d')}.pdf"
    path = default_storage.save(os.path.join(ruta, nombre_archivo), ContentFile(archivo_bytes))

    # 4. Guardar en historial y actualizar la tabla correspondiente
    tabla_map = {
        'proveedor': 'proveedores',
        'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
        'cliente': 'clientes',
        'cliente_sin_cfdi': 'clientes_sin_cfdi'
    }
    tabla = tabla_map.get(tipo)
    if not tabla:
        return JsonResponse({'error': 'Tipo de entidad inválido'}, status=400)

    try:
        with connections[db_name].cursor() as cursor:
            # Insertar en historial
            cursor.execute("""
                INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                VALUES (%s, %s, %s, %s, %s)
            """, [rfc, tipo, path, resultado, fecha_opinion])

            # Actualizar la tabla principal
            sql = f"""
                UPDATE {tabla}
                SET Estatus = %s, fecha_opinion = %s, opinion = 1
                WHERE RFC = %s AND rfc_identy = %s
            """
            cursor.execute(sql, [resultado, fecha_opinion, rfc, rfc_empresa])
            if cursor.rowcount == 0:
                return JsonResponse({'error': 'No se encontró el registro para actualizar'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error en base de datos: {str(e)}'}, status=500)

    return JsonResponse({'success': True, 'fecha': fecha_opinion.strftime('%Y-%m-%d'), 'resultado': resultado})



@usuario_required
def usuario_opiniones_historial(request, rfc):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, archivo_pdf, resultado, fecha_opinion, created_at
            FROM opiniones_historial
            WHERE rfc = %s
            ORDER BY created_at DESC
        """, [rfc])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'archivo': row[1],
            'resultado': row[2],
            'fecha_opinion': row[3].strftime('%Y-%m-%d') if row[3] else '',
            'created_at': row[4].strftime('%d/%m/%Y %H:%M') if row[4] else '',
        })
    return JsonResponse(data, safe=False)


from django.http import FileResponse, Http404
import os

@usuario_required
def usuario_opiniones_descargar_historial(request, id_historial):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        raise Http404("No se ha identificado la empresa")

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT archivo_pdf FROM opiniones_historial
            WHERE id = %s
        """, [id_historial])
        row = cursor.fetchone()
        if not row:
            raise Http404("Registro no encontrado")
        pdf_path = row[0]

    file_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado")
    return FileResponse(open(file_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=os.path.basename(pdf_path))


@usuario_required
def usuario_opiniones_descargar_pdf(request, rfc):
    """Descarga el último PDF de opinión para un RFC."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        raise Http404("No se ha identificado la empresa")

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT archivo_pdf FROM opiniones_historial
            WHERE rfc = %s
            ORDER BY created_at DESC LIMIT 1
        """, [rfc])
        row = cursor.fetchone()
        if not row:
            raise Http404("No hay opinión cargada para este RFC")
        pdf_path = row[0]

    file_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado")

    return FileResponse(open(file_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=os.path.basename(pdf_path))




import os
import time
import re
import shutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import usuario_required
import uuid
import threading


def obtener_opinion_sat___(rfc, download_dir, logs):
    """
    Realiza la consulta al SAT y devuelve:
    - 'pdf': ruta del archivo descargado, fecha, resultado
    - 'status': estado (Positivo, Negativo, SinRespuesta) cuando no hay PDF
    - None si falla
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('prefs', {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    })

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    logs.append("✅ Navegador iniciado")

    try:
        url = 'https://ptsc32d.clouda.sat.gob.mx/ConsultaPublico'
        driver.get(url)
        logs.append("🌐 Entrando al SAT...")

        # Configurar descarga
        params = {'behavior': 'allow', 'downloadPath': download_dir}
        driver.execute_cdp_cmd('Page.setDownloadBehavior', params)

        # Esperar campo RFC
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "txtRfc")))
        logs.append("📄 Formulario cargado")

        # Ingresar RFC letra por letra
        rfc_input = driver.find_element(By.ID, "txtRfc")
        rfc_input.clear()
        for c in rfc:
            rfc_input.send_keys(c)
            time.sleep(0.1)
        logs.append(f"🔑 Ingresando RFC {rfc}")

        # Hacer clic en buscar
        driver.find_element(By.ID, "buqueda").click()
        logs.append("🔍 Buscando...")
        time.sleep(5)

        # Verificar si hay mensaje de error en el body (sin PDF)
        body = driver.find_element(By.TAG_NAME, "body")
        texto_pagina = body.text

        # Patrones de mensajes
        patron_negativo = r"El RFC o CURP, no cumple con los requisitos para hacer pública su opinión positiva"
        patron_sin_respuesta = r"El RFC o CURP consultado no se encuentra autorizado para hacerse público."
        patron_positivo = r"Opinión Positiva.* Información a la fecha de la consulta."

        print(texto_pagina)

        if re.search(patron_negativo, texto_pagina):
            logs.append("⚠️ RFC no cumple requisitos → Estatus Negativo")
            driver.quit()
            return {'status': 'Negativo', 'fecha': datetime.now().date()}
        elif re.search(patron_sin_respuesta, texto_pagina):
            logs.append("⚠️ RFC no autorizado → Estatus SinRespuesta")
            driver.quit()
            return {'status': 'SinRespuesta', 'fecha': datetime.now().date()}
        elif re.search(patron_positivo, texto_pagina):
            # En teoría, si es positivo debería mostrar el PDF, pero podría haber un mensaje
            logs.append("✅ Opinión positiva detectada, se intentará descargar PDF")
            # Continuar con la descarga del PDF
        else:
            logs.append("📄 No se detectó mensaje de error, intentando descargar PDF...")

        # Si llegamos aquí, intentamos descargar el PDF (caso positivo o sin mensaje claro)
        try:
            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div/main/div[2]/div/label/div[2]/div[1]/iframe"))
            )
            driver.switch_to.frame(iframe)
            logs.append("🖱️ Cambiando al iframe...")
        except Exception as e:
            logs.append(f"❌ No se pudo acceder al iframe: {str(e)}")
            driver.quit()
            return None

        try:
            boton = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/a/button"))
            )
            boton.click()
            logs.append("⬇️ Descargando PDF...")
        except Exception as e:
            logs.append(f"❌ Error al hacer clic en el botón de descarga: {str(e)}")
            driver.quit()
            return None

        # Esperar a que se descargue el archivo
        time.sleep(10)
        archivos = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
        if not archivos:
            logs.append("❌ No se detectó ningún PDF descargado")
            driver.quit()
            return None

        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
        pdf_path = os.path.join(download_dir, archivos[0])
        logs.append(f"✅ PDF descargado: {os.path.basename(pdf_path)}")

        # Extraer datos del PDF
        from PyPDF2 import PdfReader
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()

        # Extraer fecha
        patron_fecha = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+a\s+las\s+(\d{1,2}:\d{2})\s+horas'
        match_fecha = re.search(patron_fecha, texto)
        if not match_fecha:
            raise ValueError("No se encontró la fecha en el PDF")
        dia = int(match_fecha.group(1))
        mes_str = match_fecha.group(2).lower()
        anio = int(match_fecha.group(3))
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = meses.get(mes_str, 1)
        fecha_opinion = datetime(anio, mes, dia).date()

        # Extraer resultado (P o N)
        patron_resultado = r'\|[^|]*\|[^|]*\|[^|]*\|([PN])\|\|'
        match_res = re.search(patron_resultado, texto)
        resultado = 'Positivo' if match_res and match_res.group(1) == 'P' else 'Negativo' if match_res and match_res.group(1) == 'N' else 'SinRespuesta'
        logs.append(f"📊 Datos extraídos: fecha={fecha_opinion}, resultado={resultado}")

        driver.quit()
        return {'pdf_path': pdf_path, 'fecha': fecha_opinion, 'resultado': resultado}
    except Exception as e:
        logs.append(f"❌ Error general: {str(e)}")
        driver.quit()
        return None

@usuario_required
@csrf_exempt
def usuario_opiniones_obtener_sat_____(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    rfc = request.POST.get('rfc')
    tipo = request.POST.get('tipo')
    if not rfc or not tipo:
        return JsonResponse({'error': 'Faltan datos (RFC o tipo)'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    logs = []
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_opinions', rfc)
    os.makedirs(temp_dir, exist_ok=True)

    # Iniciar proceso
    logs.append("🚀 Iniciando el proceso de obtención de opinión del SAT...")
    resultado = obtener_opinion_sat(rfc, temp_dir, logs)

    if resultado is None:
        return JsonResponse({'error': 'No se pudo completar la operación', 'logs': logs}, status=500)

    # Mapeo de tipo a tabla
    tabla_map = {
        'proveedor': 'proveedores',
        'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
        'cliente': 'clientes',
        'cliente_sin_cfdi': 'clientes_sin_cfdi'
    }
    tabla = tabla_map.get(tipo)
    if not tabla:
        return JsonResponse({'error': 'Tipo de entidad inválido', 'logs': logs}, status=400)

    try:
        with connections[db_name].cursor() as cursor:
            # Si hay PDF (caso con descarga)
            if 'pdf_path' in resultado:
                # Mover PDF a la ruta definitiva
                año = resultado['fecha'].year
                mes = resultado['fecha'].month
                ruta_destino = os.path.join('opinion', rfc, str(año), f"{mes:02d}")
                nombre_archivo = f"{rfc}_{resultado['fecha'].strftime('%Y%m%d')}.pdf"
                destino = default_storage.save(os.path.join(ruta_destino, nombre_archivo),
                                               ContentFile(open(resultado['pdf_path'], 'rb').read()))
                logs.append(f"📁 PDF guardado en: {destino}")

                # Insertar en historial
                cursor.execute("""
                    INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, tipo, destino, resultado['resultado'], resultado['fecha']])

                # Actualizar tabla principal
                sql = f"""
                    UPDATE {tabla}
                    SET Estatus = %s, fecha_opinion = %s, opinion = 1
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [resultado['resultado'], resultado['fecha'], rfc, rfc_empresa])
                logs.append(f"✅ Registro actualizado con PDF (resultado: {resultado['resultado']})")

                # Eliminar archivo temporal
                os.remove(resultado['pdf_path'])

            else:
                # Caso sin PDF (solo actualización de estatus)
                fecha_actual = resultado['fecha']
                sql = f"""
                    UPDATE {tabla}
                    SET Estatus = %s, fecha_opinion = %s, opinion = 0
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [resultado['status'], fecha_actual, rfc, rfc_empresa])
                logs.append(f"✅ Registro actualizado sin PDF (estatus: {resultado['status']})")

                # También podemos registrar en historial que se consultó sin PDF (opcional)
                cursor.execute("""
                    INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, tipo, '', resultado['status'], fecha_actual])

            if cursor.rowcount == 0:
                logs.append("⚠️ Advertencia: No se encontró el registro en la tabla principal")
    except Exception as e:
        logs.append(f"❌ Error en base de datos: {str(e)}")
        return JsonResponse({'error': f'Error en base de datos: {str(e)}', 'logs': logs}, status=500)

    logs.append("🎉 Proceso terminado correctamente")
    return JsonResponse({'success': True, 'logs': logs})



# Diccionario en memoria para almacenar el estado de las tareas
tasks_status = {}

def obtener_opinion_sat(rfc, download_dir, logs):
    """
    Realiza la consulta al SAT y devuelve:
    - 'pdf': ruta del archivo descargado, fecha, resultado
    - 'status': estado (Positivo, Negativo, SinRespuesta) cuando no hay PDF
    - None si falla
    """
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option('prefs', {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    })

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    logs.append("✅ Navegador iniciado")

    try:
        url = 'https://ptsc32d.clouda.sat.gob.mx/ConsultaPublico'
        driver.get(url)
        logs.append("🌐 Entrando al SAT...")

        params = {'behavior': 'allow', 'downloadPath': download_dir}
        driver.execute_cdp_cmd('Page.setDownloadBehavior', params)

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "txtRfc")))
        logs.append("📄 Formulario cargado")

        rfc_input = driver.find_element(By.ID, "txtRfc")
        rfc_input.clear()
        for c in rfc:
            rfc_input.send_keys(c)
            time.sleep(0.1)
        logs.append(f"🔑 Ingresando RFC {rfc}")

        driver.find_element(By.ID, "buqueda").click()
        logs.append("🔍 Buscando...")
        time.sleep(5)

        body = driver.find_element(By.TAG_NAME, "body")
        texto_pagina = body.text

        patron_negativo = r"El RFC o CURP, no cumple con los requisitos para hacer pública su opinión positiva"
        patron_sin_respuesta = r"El RFC o CURP consultado no se encuentra autorizado para hacerse público"
        patron_positivo = r"Opinión Positiva.* Información a la fecha de la consulta."

        print(texto_pagina)
        
        if re.search(patron_negativo, texto_pagina):
            logs.append("⚠️ RFC no cumple requisitos → Estatus Negativo")
            driver.quit()
            return {'status': 'Negativo', 'fecha': datetime.now().date()}
        elif re.search(patron_sin_respuesta, texto_pagina):
            logs.append("⚠️ RFC no autorizado → Estatus SinRespuesta")
            driver.quit()
            return {'status': 'SinRespuesta', 'fecha': datetime.now().date()}
        elif re.search(patron_positivo, texto_pagina):
            logs.append("✅ Opinión positiva detectada, se intentará descargar PDF")
        else:
            logs.append("📄 No se detectó mensaje de error, intentando descargar PDF...")

        try:
            iframe = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div/main/div[2]/div/label/div[2]/div[1]/iframe"))
            )
            driver.switch_to.frame(iframe)
            logs.append("🖱️ Cambiando al iframe...")
        except Exception as e:
            logs.append(f"❌ No se pudo acceder al iframe: {str(e)}")
            driver.quit()
            return None

        try:
            boton = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div/a/button"))
            )
            boton.click()
            logs.append("⬇️ Descargando PDF...")
        except Exception as e:
            logs.append(f"❌ Error al hacer clic en el botón de descarga: {str(e)}")
            driver.quit()
            return None

        time.sleep(10)
        archivos = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
        if not archivos:
            logs.append("❌ No se detectó ningún PDF descargado")
            driver.quit()
            return None

        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
        pdf_path = os.path.join(download_dir, archivos[0])
        logs.append(f"✅ PDF descargado: {os.path.basename(pdf_path)}")

        from PyPDF2 import PdfReader
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            texto = ""
            for page in reader.pages:
                texto += page.extract_text()

        patron_fecha = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+a\s+las\s+(\d{1,2}:\d{2})\s+horas'
        match_fecha = re.search(patron_fecha, texto)
        if not match_fecha:
            raise ValueError("No se encontró la fecha en el PDF")
        dia = int(match_fecha.group(1))
        mes_str = match_fecha.group(2).lower()
        anio = int(match_fecha.group(3))
        meses = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        mes = meses.get(mes_str, 1)
        fecha_opinion = datetime(anio, mes, dia).date()

        patron_resultado = r'\|[^|]*\|[^|]*\|[^|]*\|([PN])\|\|'
        match_res = re.search(patron_resultado, texto)
        resultado = 'Positivo' if match_res and match_res.group(1) == 'P' else 'Negativo' if match_res and match_res.group(1) == 'N' else 'SinRespuesta'
        logs.append(f"📊 Datos extraídos: fecha={fecha_opinion}, resultado={resultado}")

        driver.quit()
        return {'pdf_path': pdf_path, 'fecha': fecha_opinion, 'resultado': resultado}
    except Exception as e:
        logs.append(f"❌ Error general: {str(e)}")
        driver.quit()
        return None

def run_opinion_task(task_id, rfc, tipo, db_name, rfc_empresa):
    """Ejecuta el proceso en segundo plano y actualiza el diccionario de estado."""
    logs = []
    tasks_status[task_id] = {'logs': logs, 'finished': False, 'success': False, 'error': None}
    try:
        logs.append("🚀 Iniciando el proceso de obtención de opinión del SAT...")
        tasks_status[task_id]['logs'] = logs

        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_opinions', rfc)
        os.makedirs(temp_dir, exist_ok=True)
        logs.append("📁 Directorio temporal creado")

        resultado = obtener_opinion_sat(rfc, temp_dir, logs)
        tasks_status[task_id]['logs'] = logs

        if resultado is None:
            tasks_status[task_id]['error'] = 'No se pudo completar la operación'
            tasks_status[task_id]['finished'] = True
            return

        tabla_map = {
            'proveedor': 'proveedores',
            'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
            'cliente': 'clientes',
            'cliente_sin_cfdi': 'clientes_sin_cfdi'
        }
        tabla = tabla_map.get(tipo)
        if not tabla:
            tasks_status[task_id]['error'] = 'Tipo de entidad inválido'
            tasks_status[task_id]['finished'] = True
            return

        with connections[db_name].cursor() as cursor:
            if 'pdf_path' in resultado:
                año = resultado['fecha'].year
                mes = resultado['fecha'].month
                ruta_destino = os.path.join('opinion', rfc, str(año), f"{mes:02d}")
                nombre_archivo = f"{rfc}_{resultado['fecha'].strftime('%Y%m%d')}.pdf"
                destino = default_storage.save(
                    os.path.join(ruta_destino, nombre_archivo),
                    ContentFile(open(resultado['pdf_path'], 'rb').read())
                )
                logs.append(f"📁 PDF guardado en: {destino}")

                cursor.execute("""
                    INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, tipo, destino, resultado['resultado'], resultado['fecha']])

                sql = f"""
                    UPDATE {tabla}
                    SET Estatus = %s, fecha_opinion = %s, opinion = 1
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [resultado['resultado'], resultado['fecha'], rfc, rfc_empresa])
                logs.append(f"✅ Registro actualizado con PDF (resultado: {resultado['resultado']})")
                os.remove(resultado['pdf_path'])
            else:
                fecha_actual = resultado['fecha']
                sql = f"""
                    UPDATE {tabla}
                    SET Estatus = %s, fecha_opinion = %s, opinion = 0
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [resultado['status'], fecha_actual, rfc, rfc_empresa])
                logs.append(f"✅ Registro actualizado sin PDF (estatus: {resultado['status']})")
                cursor.execute("""
                    INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, tipo, '', resultado['status'], fecha_actual])

        tasks_status[task_id]['success'] = True
        logs.append("🎉 Proceso terminado correctamente")
    except Exception as e:
        logs.append(f"❌ Error: {str(e)}")
        tasks_status[task_id]['error'] = str(e)
    finally:
        tasks_status[task_id]['finished'] = True
        tasks_status[task_id]['logs'] = logs

@usuario_required
@csrf_exempt
def usuario_opiniones_obtener_sat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    rfc = request.POST.get('rfc')
    tipo = request.POST.get('tipo')
    if not rfc or not tipo:
        return JsonResponse({'error': 'Faltan datos (RFC o tipo)'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {'logs': [], 'finished': False, 'success': False, 'error': None}

    thread = threading.Thread(target=run_opinion_task, args=(task_id, rfc, tipo, db_name, rfc_empresa))
    thread.daemon = True
    thread.start()

    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_opiniones_obtener_sat_status(request, task_id):
    """Devuelve el estado y los logs de una tarea."""
    status = tasks_status.get(task_id)
    if not status:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse({
        'finished': status['finished'],
        'logs': status['logs'],
        'success': status.get('success', False),
        'error': status.get('error')
    })



import os
import re
from datetime import datetime
from PyPDF2 import PdfReader
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connections
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib import messages
from .decorators import usuario_required

# ========== CONSTANCIAS ==========
@usuario_required
def usuario_constancias(request):
    return render(request, 'core/usuario/constancias_lista.html')

@usuario_required
def usuario_constancias_data(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        # Proveedores
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_constancia, constancia, 'proveedor' as tipo
            FROM proveedores
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows = list(cursor.fetchall())

        # Proveedores sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_constancia, constancia, 'proveedor_sin_cfdi' as tipo
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        # Clientes
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_constancia, constancia, 'cliente' as tipo
            FROM clientes
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        # Clientes sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_constancia, constancia, 'cliente_sin_cfdi' as tipo
            FROM clientes_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

    data = []
    for row in rows:
        data.append({
            'rfc': row[0] or '',
            'razon_social': row[1] or '',
            'estatus': row[2] or 'SinRespuesta',
            'fecha_constancia': row[3].strftime('%Y-%m-%d') if row[3] else '',
            'constancia': row[4] or 0,
            'tipo': row[5],
        })
    return JsonResponse(data, safe=False)

def extraer_datos_constancia(pdf_file):
    """Extrae RFC y datos de domicilio de un PDF de constancia."""
    try:
        reader = PdfReader(pdf_file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text()

        # Extraer RFC
        rfc_match = re.search(r'RFC:\s*([A-Z0-9]{12,13})', texto, re.IGNORECASE)
        if not rfc_match:
            raise ValueError("No se pudo encontrar el RFC en el documento")
        rfc = rfc_match.group(1).upper()

        # Extraer datos de ubicación
        cp_match = re.search(r'Código Postal:\s*(\d{5})', texto, re.IGNORECASE)
        codigoPostal = cp_match.group(1) if cp_match else ''

        calle_match = re.search(r'Nombre de Vialidad:\s*([^\n]+)', texto, re.IGNORECASE)
        calle = calle_match.group(1).strip() if calle_match else ''

        noExt_match = re.search(r'Número Exterior:\s*([^\n]+)', texto, re.IGNORECASE)
        noExt = noExt_match.group(1).strip() if noExt_match else ''

        noInt_match = re.search(r'Número Interior:\s*([^\n]+)', texto, re.IGNORECASE)
        noInt = noInt_match.group(1).strip() if noInt_match else ''

        colonia_match = re.search(r'Nombre de la Colonia:\s*([^\n]+)', texto, re.IGNORECASE)
        colonia = colonia_match.group(1).strip() if colonia_match else ''

        municipio_match = re.search(r'Nombre del Municipio o Demarcación Territorial:\s*([^\n]+)', texto, re.IGNORECASE)
        municipio = municipio_match.group(1).strip() if municipio_match else ''

        estado_match = re.search(r'Nombre del Estado:\s*([^\n]+)', texto, re.IGNORECASE)
        estado = estado_match.group(1).strip() if estado_match else ''

        ciudad_match = re.search(r'Nombre de la Localidad:\s*([^\n]+)', texto, re.IGNORECASE)
        ciudad = ciudad_match.group(1).strip() if ciudad_match else ''

        # Fecha de la constancia (del documento, se puede extraer de alguna parte o usar fecha actual)
        # Por simplicidad, usamos fecha actual. Si el PDF tiene fecha, se puede extraer.
        fecha_constancia = datetime.now().date()

        return {
            'rfc': rfc,
            'fecha_constancia': fecha_constancia,
            'codigoPostal': codigoPostal,
            'calle': calle,
            'noInt': noInt,
            'noExt': noExt,
            'colonia': colonia,
            'estado': estado,
            'municipio': municipio,
            'ciudad': ciudad,
        }
    except Exception as e:
        raise ValueError(f"Error al procesar el PDF: {str(e)}")

@usuario_required
@csrf_exempt
def usuario_constancias_subir(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'pdf' not in request.FILES:
        return JsonResponse({'error': 'No se envió ningún archivo'}, status=400)

    archivo = request.FILES['pdf']
    if not archivo.name.endswith('.pdf'):
        return JsonResponse({'error': 'Solo se aceptan archivos PDF'}, status=400)

    rfc_seleccionado = request.POST.get('rfc')
    tipo = request.POST.get('tipo')
    if not rfc_seleccionado or not tipo:
        return JsonResponse({'error': 'Faltan datos (RFC o tipo)'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # Extraer datos del PDF
    try:
        datos = extraer_datos_constancia(archivo)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    # Verificar que el RFC extraído coincida con el seleccionado
    if datos['rfc'] != rfc_seleccionado:
        # Devolver los datos extraídos para que el frontend muestre un modal de confirmación
        return JsonResponse({
            'error': 'RFC no coincide',
            'extracted_rfc': datos['rfc'],
            'extracted_data': {
                'codigoPostal': datos['codigoPostal'],
                'calle': datos['calle'],
                'noInt': datos['noInt'],
                'noExt': datos['noExt'],
                'colonia': datos['colonia'],
                'estado': datos['estado'],
                'municipio': datos['municipio'],
                'ciudad': datos['ciudad'],
            }
        }, status=409)

    # Guardar el PDF en la ruta definitiva
    año = datos['fecha_constancia'].year
    mes = datos['fecha_constancia'].month
    ruta = os.path.join('constancia', rfc_seleccionado, str(año), f"{mes:02d}")
    nombre_archivo = f"{rfc_seleccionado}_{datos['fecha_constancia'].strftime('%Y%m%d')}.pdf"
    archivo.seek(0)  # Reiniciar puntero
    path = default_storage.save(os.path.join(ruta, nombre_archivo), ContentFile(archivo.read()))

    # Mapeo de tipo a tabla
    tabla_map = {
        'proveedor': 'proveedores',
        'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
        'cliente': 'clientes',
        'cliente_sin_cfdi': 'clientes_sin_cfdi'
    }
    tabla = tabla_map.get(tipo)
    if not tabla:
        return JsonResponse({'error': 'Tipo de entidad inválido'}, status=400)

    # Actualizar la base de datos
    try:
        with connections[db_name].cursor() as cursor:
            # Insertar en historial
            cursor.execute("""
                INSERT INTO constancias_historial 
                (rfc, tipo, archivo_pdf, fecha_constancia, codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                rfc_seleccionado, tipo, path, datos['fecha_constancia'],
                datos['codigoPostal'], datos['calle'], datos['noInt'], datos['noExt'],
                datos['colonia'], datos['estado'], datos['municipio'], datos['ciudad']
            ])

            # Actualizar la tabla principal
            sql = f"""
                UPDATE {tabla}
                SET constancia = 1, fecha_constancia = %s,
                    codigoPostal = %s, calle = %s, noInt = %s, noExt = %s,
                    colonia = %s, estado = %s, municipio = %s, ciudad = %s
                WHERE RFC = %s AND rfc_identy = %s
            """
            cursor.execute(sql, [
                datos['fecha_constancia'],
                datos['codigoPostal'], datos['calle'], datos['noInt'], datos['noExt'],
                datos['colonia'], datos['estado'], datos['municipio'], datos['ciudad'],
                rfc_seleccionado, rfc_empresa
            ])
            if cursor.rowcount == 0:
                return JsonResponse({'error': 'No se encontró el registro para actualizar'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error en base de datos: {str(e)}'}, status=500)

    return JsonResponse({'success': True, 'fecha': datos['fecha_constancia'].strftime('%Y-%m-%d')})

@usuario_required
def usuario_constancias_historial(request, rfc):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, archivo_pdf, fecha_constancia, created_at,
                   codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad
            FROM constancias_historial
            WHERE rfc = %s
            ORDER BY created_at DESC
        """, [rfc])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'archivo': row[1],
            'fecha_constancia': row[2].strftime('%Y-%m-%d') if row[2] else '',
            'created_at': row[3].strftime('%d/%m/%Y %H:%M') if row[3] else '',
            'codigoPostal': row[4] or '',
            'calle': row[5] or '',
            'noInt': row[6] or '',
            'noExt': row[7] or '',
            'colonia': row[8] or '',
            'estado': row[9] or '',
            'municipio': row[10] or '',
            'ciudad': row[11] or '',
        })
    return JsonResponse(data, safe=False)

@usuario_required
def usuario_constancias_descargar_pdf(request, rfc):
    """Descarga la última constancia subida para un RFC."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        raise Http404("No se ha identificado la empresa")

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT archivo_pdf FROM constancias_historial
            WHERE rfc = %s
            ORDER BY created_at DESC LIMIT 1
        """, [rfc])
        row = cursor.fetchone()
        if not row:
            raise Http404("No hay constancia cargada para este RFC")
        pdf_path = row[0]

    file_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado")
    return FileResponse(open(file_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=os.path.basename(pdf_path))

@usuario_required
def usuario_constancias_descargar_historial(request, id_historial):
    """Descarga una constancia específica del historial por ID."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        raise Http404("No se ha identificado la empresa")

    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT archivo_pdf FROM constancias_historial WHERE id = %s", [id_historial])
        row = cursor.fetchone()
        if not row:
            raise Http404("Registro no encontrado")
        pdf_path = row[0]

    file_path = os.path.join(settings.MEDIA_ROOT, pdf_path)
    if not os.path.exists(file_path):
        raise Http404("Archivo no encontrado")
    return FileResponse(open(file_path, 'rb'), content_type='application/pdf', as_attachment=True, filename=os.path.basename(pdf_path))




@usuario_required
def usuario_validacion_domicilio(request):
    return render(request, 'core/usuario/validacion_domicilio_lista.html')

@usuario_required
def usuario_validacion_domicilio_data(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        # Proveedores
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal, municipio, estado, ciudad
            FROM proveedores
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows = list(cursor.fetchall())

        # Proveedores sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal, municipio, estado, ciudad
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        # Clientes
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal, municipio, estado, ciudad
            FROM clientes
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        # Clientes sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal, municipio, estado, ciudad
            FROM clientes_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

    data = []
    for row in rows:
        data.append({
            'rfc': row[0] or '',
            'razon_social': row[1] or '',
            'calle': row[2] or '',
            'noExt': row[3] or '',
            'noInt': row[4] or '',
            'colonia': row[5] or '',
            'codigoPostal': row[6] or '',
            'municipio': row[7] or '',
            'estado': row[8] or '',
            'ciudad': row[9] or '',
        })
    return JsonResponse(data, safe=False)


import threading
import uuid
from datetime import datetime
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import usuario_required
from .utils import obtener_fecha_publicacion_sat, descargar_csv, obtener_rfcs_existentes


tasks_status = {}  # Diccionario para almacenar estado de tareas

def run_articulo69_task(task_id, db_name):
    logs = []
    tasks_status[task_id] = {'logs': logs, 'finished': False, 'success': False, 'error': None}
    try:
        logs.append("🚀 Iniciando actualización de Artículo 69...")
        fecha_publicacion = obtener_fecha_publicacion_sat(1)
        logs.append(f"📅 Fecha publicación: {fecha_publicacion}")
        urls = [
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Exigibles.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Firmes.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/No_localizados.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/AGR/03_02_26/Sentencias.csv'
        ]
        rfcs_validos = obtener_rfcs_existentes(db_name)
        logs.append(f"🔍 RFCs válidos en la empresa: {len(rfcs_validos)}")
        all_records = {}
        for url in urls:
            logs.append(f"📥 Descargando {url}...")
            data = descargar_csv(url)
            logs.append(f"   {len(data)} registros.")
            for row in data:
                rfc = row.get('RFC', '').strip()
                if rfc and rfc in rfcs_validos:
                    nombre = row.get('RAZON SOCIAL', row.get('Nombre del Contribuyente', '')).strip()
                    supuesto = row.get('SUPUESTO', '').strip()
                    # Truncar a 255 caracteres por si acaso
                    nombre = nombre[:255]
                    supuesto = supuesto[:255]
                    if rfc not in all_records:
                        all_records[rfc] = {'nombre': nombre, 'supuesto': supuesto}
        logs.append(f"📊 RFCs a insertar: {len(all_records)}")
        fecha_validacion = datetime.now().date()
        with connections[db_name].cursor() as cursor:
            cursor.execute("DELETE FROM articulo69")
            for rfc, info in all_records.items():
                cursor.execute("""
                    INSERT INTO articulo69 (rfc, nombre, tipo_supuesto, fecha_validacion, fecha_publicacion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, info['nombre'], info['supuesto'], fecha_validacion, fecha_publicacion])
        logs.append("✅ Artículo 69 actualizado correctamente.")
        tasks_status[task_id]['success'] = True
    except Exception as e:
        logs.append(f"❌ Error: {str(e)}")
        tasks_status[task_id]['error'] = str(e)
    finally:
        tasks_status[task_id]['finished'] = True
        tasks_status[task_id]['logs'] = logs


def run_articulo69b_task(task_id, db_name):
    logs = []
    tasks_status[task_id] = {'logs': logs, 'finished': False, 'success': False, 'error': None}
    try:
        logs.append("🚀 Iniciando actualización de Artículo 69-B...")
        fecha_publicacion = obtener_fecha_publicacion_sat(2)
        logs.append(f"📅 Fecha publicación: {fecha_publicacion}")
        urls = [
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Definitivos.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Desvirtuados.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/Presuntos.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGAFF/SentenciasFavorables.csv'
        ]
        rfcs_validos = obtener_rfcs_existentes(db_name)
        logs.append(f"🔍 RFCs válidos en la empresa: {len(rfcs_validos)}")
        all_records = {}
        for url in urls:
            logs.append(f"📥 Descargando {url}...")
            data = descargar_csv(url)
            logs.append(f"   {len(data)} registros.")
            for row in data:
                rfc = row.get('RFC', '').strip()
                if rfc and rfc in rfcs_validos:
                    nombre = row.get('Nombre del Contribuyente', '').strip()
                    situacion = row.get('Situación del contribuyente', '').strip()
                    nombre = nombre[:255]
                    situacion = situacion[:255]
                    if rfc not in all_records:
                        all_records[rfc] = {'nombre': nombre, 'situacion': situacion}
        logs.append(f"📊 RFCs a insertar: {len(all_records)}")
        fecha_validacion = datetime.now().date()
        with connections[db_name].cursor() as cursor:
            cursor.execute("DELETE FROM articulo69b")
            for rfc, info in all_records.items():
                cursor.execute("""
                    INSERT INTO articulo69b (rfc, nombre, tipo_supuesto, fecha_validacion, fecha_publicacion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, info['nombre'], info['situacion'], fecha_validacion, fecha_publicacion])
        logs.append("✅ Artículo 69-B actualizado correctamente.")
        tasks_status[task_id]['success'] = True
    except Exception as e:
        logs.append(f"❌ Error: {str(e)}")
        tasks_status[task_id]['error'] = str(e)
    finally:
        tasks_status[task_id]['finished'] = True
        tasks_status[task_id]['logs'] = logs



def run_articulo69bis_task(task_id, db_name):
    logs = []
    tasks_status[task_id] = {'logs': logs, 'finished': False, 'success': False, 'error': None}
    try:
        logs.append("🚀 Iniciando actualización de Artículo 69-Bis...")
        fecha_publicacion = obtener_fecha_publicacion_sat(3)
        logs.append(f"📅 Fecha publicación: {fecha_publicacion}")
        urls = [
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGGC/Listado_69_B_Bis_Definitivo.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGGC/Listado_69_B_Bis_SentenciaFa.csv'
        ]
        rfcs_validos = obtener_rfcs_existentes(db_name)
        logs.append(f"🔍 RFCs válidos en la empresa: {len(rfcs_validos)}")
        all_records = {}
        for url in urls:
            logs.append(f"📥 Descargando {url}...")
            data = descargar_csv(url)
            logs.append(f"   {len(data)} registros.")
            for row in data:
                rfc = row.get('RFC', '').strip()
                if rfc and rfc in rfcs_validos:
                    nombre = row.get('Nombre del Contribuyente', '').strip()
                    situacion = row.get('Situación del contribuyente', '').strip()
                    nombre = nombre[:255]
                    situacion = situacion[:255]
                    if rfc not in all_records:
                        all_records[rfc] = {'nombre': nombre, 'situacion': situacion}
        logs.append(f"📊 RFCs a insertar: {len(all_records)}")
        fecha_validacion = datetime.now().date()
        with connections[db_name].cursor() as cursor:
            cursor.execute("DELETE FROM articulo69bis")
            for rfc, info in all_records.items():
                cursor.execute("""
                    INSERT INTO articulo69bis (rfc, nombre, tipo_supuesto, fecha_validacion, fecha_publicacion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, info['nombre'], info['situacion'], fecha_validacion, fecha_publicacion])
        logs.append("✅ Artículo 69-Bis actualizado correctamente.")
        tasks_status[task_id]['success'] = True
    except Exception as e:
        logs.append(f"❌ Error: {str(e)}")
        tasks_status[task_id]['error'] = str(e)
    finally:
        tasks_status[task_id]['finished'] = True
        tasks_status[task_id]['logs'] = logs


# ================== ARTÍCULO 69 ==================
@usuario_required
def usuario_articulo69(request):
    return render(request, 'core/usuario/articulo69_lista.html')

@usuario_required
def usuario_articulo69_data(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT rfc, nombre, tipo_supuesto, fecha_validacion, fecha_publicacion FROM articulo69 ORDER BY rfc")
        rows = cursor.fetchall()
    data = [{'rfc': r[0], 'nombre': r[1], 'tipo_supuesto': r[2], 'fecha_validacion': r[3].isoformat() if r[3] else '', 'fecha_publicacion': r[4].isoformat() if r[4] else ''} for r in rows]
    return JsonResponse(data, safe=False)

@usuario_required
@csrf_exempt
def usuario_articulo69_actualizar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {'logs': [], 'finished': False, 'success': False, 'error': None}
    thread = threading.Thread(target=run_articulo69_task, args=(task_id, db_name))
    thread.daemon = True
    thread.start()
    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_articulo69_status(request, task_id):
    status = tasks_status.get(task_id)
    if not status:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse({
        'finished': status['finished'],
        'logs': status['logs'],
        'success': status.get('success', False),
        'error': status.get('error')
    })

# ================== ARTÍCULO 69-B ==================
@usuario_required
def usuario_articulo69b(request):
    return render(request, 'core/usuario/articulo69b_lista.html')

@usuario_required
def usuario_articulo69b_data(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT rfc, nombre, tipo_supuesto, fecha_validacion, fecha_publicacion FROM articulo69b ORDER BY rfc")
        rows = cursor.fetchall()
    data = [{'rfc': r[0], 'nombre': r[1], 'tipo_supuesto': r[2], 'fecha_validacion': r[3].isoformat() if r[3] else '', 'fecha_publicacion': r[4].isoformat() if r[4] else ''} for r in rows]
    return JsonResponse(data, safe=False)

@usuario_required
@csrf_exempt
def usuario_articulo69b_actualizar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {'logs': [], 'finished': False, 'success': False, 'error': None}
    thread = threading.Thread(target=run_articulo69b_task, args=(task_id, db_name))
    thread.daemon = True
    thread.start()
    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_articulo69b_status(request, task_id):
    status = tasks_status.get(task_id)
    if not status:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse({
        'finished': status['finished'],
        'logs': status['logs'],
        'success': status.get('success', False),
        'error': status.get('error')
    })

# ================== ARTÍCULO 69-BIS ==================
@usuario_required
def usuario_articulo69bis(request):
    return render(request, 'core/usuario/articulo69bis_lista.html')

@usuario_required
def usuario_articulo69bis_data(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT rfc, nombre, tipo_supuesto, fecha_validacion, fecha_publicacion FROM articulo69bis ORDER BY rfc")
        rows = cursor.fetchall()
    data = [{'rfc': r[0], 'nombre': r[1], 'tipo_supuesto': r[2], 'fecha_validacion': r[3].isoformat() if r[3] else '', 'fecha_publicacion': r[4].isoformat() if r[4] else ''} for r in rows]
    return JsonResponse(data, safe=False)

@usuario_required
@csrf_exempt
def usuario_articulo69bis_actualizar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    task_id = str(uuid.uuid4())
    tasks_status[task_id] = {'logs': [], 'finished': False, 'success': False, 'error': None}
    thread = threading.Thread(target=run_articulo69bis_task, args=(task_id, db_name))
    thread.daemon = True
    thread.start()
    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_articulo69bis_status(request, task_id):
    status = tasks_status.get(task_id)
    if not status:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse({
        'finished': status['finished'],
        'logs': status['logs'],
        'success': status.get('success', False),
        'error': status.get('error')
    })
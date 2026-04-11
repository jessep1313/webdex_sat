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
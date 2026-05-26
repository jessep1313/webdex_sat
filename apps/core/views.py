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
from .views_reportes import reporte_adhoc, reporte_metadata, reporte_ejecutar


def email_existe_en_sistema(email, exclude_id=None, exclude_model=None):
    """
    Verifica si un email ya existe en SuperAdmin, Admin o UsuarioCentral.
    Parámetros:
    - email: correo a verificar
    - exclude_id: ID del registro que se está editando (para omitirlo de la verificación)
    - exclude_model: modelo del registro que se edita (para omitir la tabla correspondiente)
    Retorna True si el email ya existe en alguna de las otras tablas (o en la misma si no se excluye).
    """
    email = email.strip().lower()
    
    # Verificar en SuperAdmin
    if exclude_model != SuperAdmin:
        if SuperAdmin.objects.using('default').filter(email__iexact=email).exists():
            return True
    # Verificar en Admin
    if exclude_model != Admin:
        qs = Admin.objects.using('default').filter(email__iexact=email)
        if exclude_id and exclude_model == Admin:
            qs = qs.exclude(pk=exclude_id)
        if qs.exists():
            return True
    # Verificar en UsuarioCentral
    if exclude_model != UsuarioCentral:
        qs = UsuarioCentral.objects.using('default').filter(email__iexact=email)
        if exclude_id and exclude_model == UsuarioCentral:
            qs = qs.exclude(pk=exclude_id)
        if qs.exists():
            return True
    return False



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

        print(email)
        print(password)
        # 1. Buscar en superadmins
        try:
            user = SuperAdmin.objects.using('default').get(email=email, activo=True)
            print(user)
            if check_password(password, user.password):
                print('entro')
                request.session['user_id'] = user.id
                request.session['user_nombre'] = user.nombre
                request.session['user_email'] = user.email
                request.session['user_type'] = 'SA'
                request.session.save()   # 👈 fuerza la escritura

                print("Sesión guardada:", request.session.items())   # 👈 ver qué contiene

                return redirect('dashboard')
            else:
                print('no entro')
                messages.error(request, 'Contraseña incorrecta')
                return render(request, 'core/login.html')
        except SuperAdmin.DoesNotExist:
            print('error superadmin')
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
                request.session.save()   # 👈 fuerza la escritura
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
                request.session.save()   # 👈 fuerza la escritura

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


def dashboard_(request):
    user_type = request.session.get('user_type')
    if not user_type:
        return redirect('login')
    return render(request, 'core/dashboard.html')




def dashboard___2(request):
    user_type = request.session.get('user_type')
    if not user_type:
        return redirect('login')

    # Obtener datos de la empresa solo para roles tenant
    db_name = None
    rfc_empresa = None
    if user_type in ('A', 'US'):
        db_name = request.session.get('empresa_db_name')
        rfc_empresa = request.session.get('empresa_rfc')
        if not db_name or not rfc_empresa:
            # Si no hay datos de empresa, mostrar solo bienvenida
            return render(request, 'core/dashboard.html', {'stats': None})

    stats = {}
    if db_name and rfc_empresa:
        with connections[db_name].cursor() as cursor:
            # 1. Conteo de entidades (usando rfc_empresa)
            cursor.execute("SELECT COUNT(*) FROM proveedores WHERE rfc_identy = %s", [rfc_empresa])
            stats['proveedores'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM proveedores_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
            stats['proveedores_sin_cfdi'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM clientes WHERE rfc_identy = %s", [rfc_empresa])
            stats['clientes'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM clientes_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
            stats['clientes_sin_cfdi'] = cursor.fetchone()[0]

            # 2. Opiniones del mes actual
            hoy = date.today()
            primer_dia_mes = hoy.replace(day=1)
            sql_opiniones = """
                SELECT Estatus, COUNT(*) FROM (
                    SELECT Estatus FROM proveedores WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                    UNION ALL
                    SELECT Estatus FROM proveedores_sin_cfdi WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                    UNION ALL
                    SELECT Estatus FROM clientes WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                    UNION ALL
                    SELECT Estatus FROM clientes_sin_cfdi WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                ) AS t GROUP BY Estatus
            """
            params = [rfc_empresa, primer_dia_mes, hoy] * 4
            cursor.execute(sql_opiniones, params)
            rows = cursor.fetchall()
            opiniones = {'Positivo': 0, 'Negativo': 0, 'SinRespuesta': 0}
            for estatus, count in rows:
                if estatus in opiniones:
                    opiniones[estatus] = count
            stats['opiniones'] = opiniones

            # 3. CFDI recibidos y emitidos (usando rfc_empresa)
            cursor.execute("SELECT COUNT(*) FROM cfdi_recibido WHERE rfc_receptor = %s", [rfc_empresa])
            stats['cfdi_recibidos'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM cfdi_emitidos WHERE rfc_emisor = %s", [rfc_empresa])
            stats['cfdi_emitidos'] = cursor.fetchone()[0]

    context = {
        'user_type': user_type,
        'stats': stats,
    }
    return render(request, 'core/dashboard.html', context)




def dashboard_2(request):
    user_type = request.session.get('user_type')
    print("Dashboard session:", request.session.items())
    if not user_type:
        return redirect('login')


    if user_type == 'SA':
        from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma
        grupos = Grupo.objects.using('default').count()
        empresas = Empresa.objects.using('default').count()
        sucursales = Sucursal.objects.using('default').count()
        admins = Admin.objects.using('default').count()
        usuarios = UsuarioCentral.objects.using('default').count()
        efirmas_validas = EFirma.objects.using('default').filter(estatus='validado').values('empresa').distinct().count()
        sin_fiel = empresas - efirmas_validas

        empresas_con_sucursales = []
        for empresa in Empresa.objects.using('default').all():
            suc_count = Sucursal.objects.using('default').filter(empresa=empresa).count()
            empresas_con_sucursales.append({
                'nombre': empresa.nombre,
                'sucursales': suc_count,
                'rfc': empresa.rfc,
                'activo': empresa.activo,
                'db_name': empresa.db_name,
                'fiel': EFirma.objects.using('default').filter(empresa=empresa.nombre, estatus='validado').exists()
            })

        context = {
            'user_type': user_type,
            'stats': {
                'grupos': grupos,
                'empresas': empresas,
                'sucursales': sucursales,
                'admins': admins,
                'usuarios': usuarios,
                'fiel_validas': efirmas_validas,
                'sin_fiel': sin_fiel,
            },
            'empresas_con_sucursales': empresas_con_sucursales,
        }
        return render(request, 'core/dashboard.html', context)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return render(request, 'core/dashboard.html', {'user_type': user_type, 'stats': None})

    stats = {}
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM proveedores WHERE rfc_identy = %s", [rfc_empresa])
        stats['proveedores'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM proveedores_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
        stats['proveedores_sin_cfdi'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clientes WHERE rfc_identy = %s", [rfc_empresa])
        stats['clientes'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clientes_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
        stats['clientes_sin_cfdi'] = cursor.fetchone()[0]

        hoy = date.today()
        primer_dia_mes = hoy.replace(day=1)
        sql_opiniones = """
            SELECT Estatus, COUNT(*) FROM (
                SELECT Estatus FROM proveedores WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                UNION ALL
                SELECT Estatus FROM proveedores_sin_cfdi WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                UNION ALL
                SELECT Estatus FROM clientes WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
                UNION ALL
                SELECT Estatus FROM clientes_sin_cfdi WHERE rfc_identy = %s AND fecha_opinion >= %s AND fecha_opinion <= %s
            ) AS t GROUP BY Estatus
        """
        params = [rfc_empresa, primer_dia_mes, hoy] * 4
        cursor.execute(sql_opiniones, params)
        rows = cursor.fetchall()
        opiniones = {'Positivo': 0, 'Negativo': 0, 'SinRespuesta': 0}
        for estatus, count in rows:
            if estatus in opiniones:
                opiniones[estatus] = count
        stats['opiniones'] = opiniones

        cursor.execute("SELECT COUNT(*) FROM cfdi_recibido WHERE rfc_receptor = %s", [rfc_empresa])
        stats['cfdi_recibidos'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM cfdi_emitidos WHERE rfc_emisor = %s", [rfc_empresa])
        stats['cfdi_emitidos'] = cursor.fetchone()[0]

    context = {
        'user_type': user_type,
        'stats': stats,
    }
    print('Print context:')
    print(context)
    return render(request, 'core/dashboard.html', context)




def dashboard(request):
    user_type = request.session.get('user_type')
    if not user_type:
        return redirect('login')

    if user_type == 'SA':
        from empresas.models import Grupo, Empresa, Sucursal, Admin, UsuarioCentral, EFirma
        grupos = Grupo.objects.using('default').count()
        empresas = Empresa.objects.using('default').count()
        sucursales = Sucursal.objects.using('default').count()
        admins = Admin.objects.using('default').count()
        usuarios = UsuarioCentral.objects.using('default').count()
        efirmas_validas = EFirma.objects.using('default').filter(estatus='validado').values('empresa').distinct().count()
        sin_fiel = empresas - efirmas_validas

        empresas_con_sucursales = []
        for empresa in Empresa.objects.using('default').all():
            suc_count = Sucursal.objects.using('default').filter(empresa=empresa).count()
            empresas_con_sucursales.append({
                'nombre': empresa.nombre,
                'sucursales': suc_count,
                'rfc': empresa.rfc,
                'activo': empresa.activo,
                'db_name': empresa.db_name,
                'fiel': EFirma.objects.using('default').filter(empresa=empresa.nombre, estatus='validado').exists()
            })

        context = {
            'user_type': user_type,
            'stats': {
                'grupos': grupos,
                'empresas': empresas,
                'sucursales': sucursales,
                'admins': admins,
                'usuarios': usuarios,
                'fiel_validas': efirmas_validas,
                'sin_fiel': sin_fiel,
            },
            'empresas_con_sucursales': empresas_con_sucursales,
        }
        return render(request, 'core/dashboard.html', context)

    else:
        # Para A y US, usar la nueva plantilla moderna
        db_name = request.session.get('empresa_db_name')
        rfc_empresa = request.session.get('empresa_rfc')
        empresa_nombre = request.session.get('empresa_nombre')

        # Datos básicos que se pasan a la plantilla (el resto se cargará vía AJAX)
        context = {
            'user_type': user_type,
            'empresa_nombre': empresa_nombre,
            'rfc_empresa': rfc_empresa,
        }
        return render(request, 'core/dashboard_moderno.html', context)

@usuario_required
def usuario_metrics_data(request):
    """
    Endpoint que devuelve métricas para el dashboard moderno.
    Parámetros GET:
        view: 'general', 'clientes', 'proveedores'
    Retorna JSON con:
        total, pendientes, listas, outerData, pendData, listData, labels (según corresponda)
    """
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    view = request.GET.get('view', 'general')

    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:

        # ------------------------------------------------------------
        # 1. Obtener listados de RFCs por tipo de entidad (según vista)
        # ------------------------------------------------------------
        rfc_clientes = set()
        rfc_proveedores = set()
        rfc_todos = set()

        if view in ('general', 'clientes'):
            # Clientes con CFDI
            cursor.execute("SELECT RFC FROM clientes WHERE rfc_identy = %s", [rfc_empresa])
            for row in cursor.fetchall():
                rfc_clientes.add(row[0])
                rfc_todos.add(row[0])
            # Clientes sin CFDI
            cursor.execute("SELECT RFC FROM clientes_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
            for row in cursor.fetchall():
                rfc_clientes.add(row[0])
                rfc_todos.add(row[0])

        if view in ('general', 'proveedores'):
            # Proveedores con CFDI
            cursor.execute("SELECT RFC FROM proveedores WHERE rfc_identy = %s", [rfc_empresa])
            for row in cursor.fetchall():
                rfc_proveedores.add(row[0])
                rfc_todos.add(row[0])
            # Proveedores sin CFDI
            cursor.execute("SELECT RFC FROM proveedores_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
            for row in cursor.fetchall():
                rfc_proveedores.add(row[0])
                rfc_todos.add(row[0])

        # ------------------------------------------------------------
        # 2. Para cada RFC, obtener estado de opinión y constancia
        #    (consultar en las cuatro tablas según el tipo real)
        # ------------------------------------------------------------
        # Creamos diccionarios: para clientes y proveedores por separado
        opinion_ok = set()      # RFC que ya tienen opinion = 1
        constancia_ok = set()   # RFC que ya tienen constancia = 1

        # Función auxiliar para actualizar según tabla
        def actualizar_estados(tabla, tipo_rfc_set):
            cursor.execute(f"SELECT RFC, opinion, constancia FROM {tabla} WHERE rfc_identy = %s", [rfc_empresa])
            for rfc, opinion, constancia in cursor.fetchall():
                if opinion == 1:
                    opinion_ok.add(rfc)
                if constancia == 1:
                    constancia_ok.add(rfc)

        actualizar_estados('clientes', rfc_clientes)
        actualizar_estados('clientes_sin_cfdi', rfc_clientes)
        actualizar_estados('proveedores', rfc_proveedores)
        actualizar_estados('proveedores_sin_cfdi', rfc_proveedores)

        # ------------------------------------------------------------
        # 3. Contar pendientes (sin opinión, sin constancia, sin ambos)
        # ------------------------------------------------------------
        sin_opinion = 0
        sin_constancia = 0
        sin_ambos = 0
        for rfc in rfc_todos:
            tiene_opinion = rfc in opinion_ok
            tiene_constancia = rfc in constancia_ok
            if not tiene_opinion and not tiene_constancia:
                sin_ambos += 1
            elif not tiene_opinion:
                sin_opinion += 1
            elif not tiene_constancia:
                sin_constancia += 1

        total_pendientes = len(rfc_todos) - (len(opinion_ok | constancia_ok))

        # ------------------------------------------------------------
        # 4. Contar entidades en listas negras (Artículos 69, 69-B, 69-Bis)
        # ------------------------------------------------------------
        listas_data = {'69': 0, '69-B': 0, '69-Bis': 0}
        # Obtener todos los RFC en cada lista
        for tabla, clave in [('articulo69', '69'), ('articulo69b', '69-B'), ('articulo69bis', '69-Bis')]:
            cursor.execute(f"SELECT rfc FROM {tabla}")
            for row in cursor.fetchall():
                if row[0] in rfc_todos:
                    listas_data[clave] += 1
        total_listas = sum(listas_data.values())

        # ------------------------------------------------------------
        # 5. Construir respuesta según la vista
        # ------------------------------------------------------------
        if view == 'general':
            total_clientes = len(rfc_clientes)
            total_proveedores = len(rfc_proveedores)
            total_entidades = total_clientes + total_proveedores

            # Desglose pendData: [sin_constancia, sin_opinion, sin_ambos]
            pend_data = [sin_constancia, sin_opinion, sin_ambos]
            # Desglose listData: [art69, art69b, art69bis]
            list_data = [listas_data['69'], listas_data['69-B'], listas_data['69-Bis']]

            return JsonResponse({
                'total': total_entidades,
                'pendientes': total_pendientes,
                'listas': total_listas,
                'outerData': [total_clientes, total_proveedores],
                'pendData': pend_data,
                'listData': list_data,
                'labels': ['Clientes', 'Proveedores', 'Pendientes', 'Listas Negras']
            })

        elif view == 'clientes':
            total_entidades = len(rfc_clientes)
            # Para vista específica, además necesitamos 'sanos' = total - pendientes - listas
            sanos = total_entidades - total_pendientes - total_listas

            return JsonResponse({
                'total': total_entidades,
                'pendientes': total_pendientes,
                'listas': total_listas,
                'sanos': sanos,
                'pendData': [sin_constancia, sin_opinion, sin_ambos],
                'listData': [listas_data['69'], listas_data['69-B'], listas_data['69-Bis']]
            })

        elif view == 'proveedores':
            total_entidades = len(rfc_proveedores)
            sanos = total_entidades - total_pendientes - total_listas

            return JsonResponse({
                'total': total_entidades,
                'pendientes': total_pendientes,
                'listas': total_listas,
                'sanos': sanos,
                'pendData': [sin_constancia, sin_opinion, sin_ambos],
                'listData': [listas_data['69'], listas_data['69-B'], listas_data['69-Bis']]
            })

        else:
            return JsonResponse({'error': 'Vista no válida'}, status=400) 

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


def validar_rfc(rfc):
    # RFC: 12 o 13 caracteres alfanuméricos (letras y números, sin espacios ni caracteres especiales)
    patron = r'^[A-Z0-9]{12,13}$'
    return re.match(patron, rfc) is not None

@superadmin_required
def empresa_crear(request):
    grupos = Grupo.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        rfc = request.POST.get('rfc').upper().strip()
        grupo_id = request.POST.get('grupo')
        activo = request.POST.get('activo') == 'on'

        # Validaciones
        if not nombre:
            messages.error(request, 'El nombre de la empresa es obligatorio.')
            return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})
        if not rfc:
            messages.error(request, 'El RFC es obligatorio.')
            return render(request, 'core/catalogos/empresa_form.html', {'grupos': grupos})
        if not validar_rfc(rfc):
            messages.error(request, 'El RFC no es válido. Debe tener 12 o 13 caracteres alfanuméricos (mayúsculas, sin espacios).')
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
        # Grupo opcional
        grupo = None
        if grupo_id:
            grupo = Grupo.objects.using('default').filter(pk=grupo_id).first()

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

        if not nombre:
            messages.error(request, 'El nombre es obligatorio.')
            return render(request, 'core/catalogos/empresa_form.html', {'empresa': empresa, 'grupos': grupos})

        if rfc != empresa.rfc:
            messages.error(request, 'No está permitido cambiar el RFC de una empresa existente.')
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
        empresa.grupo_id = grupo_id if grupo_id else None  # permitir nulo
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
def admin_crear_2(request):
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
def admin_crear(request):
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email').strip().lower()
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        empresa_id = request.POST.get('empresa')
        activo = request.POST.get('activo') == 'on'

        # Validaciones
        if not nombre or not email or not password or not empresa_id:
            messages.error(request, 'Nombre, email, contraseña y empresa son obligatorios.')
            return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})
        if password != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})
        
        # Verificar email en todo el sistema
        if email_existe_en_sistema(email):
            messages.error(request, 'Este correo electrónico ya está registrado como SuperAdministrador, Administrador o Usuario. No se puede duplicar.')
            return render(request, 'core/usuarios/admin_form.html', {'empresas': empresas})
        
        # Obtener empresa y su grupo (puede ser None)
        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        grupo_id = empresa.grupo_id

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

        # Dentro de admin_editar, antes de guardar:
        if email_existe_en_sistema(email, exclude_id=admin.id, exclude_model=Admin):
            messages.error(request, 'El email ya está en uso por otro administrador o usuario.')
            return render(request, 'core/usuarios/admin_form.html', {'admin': admin, 'empresas': empresas})

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
def usuario_crear_2(request):
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
def usuario_crear(request):
    empresas = Empresa.objects.using('default').filter(activo=True)
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email').strip().lower()
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
        
        # Verificar email en todo el sistema
        if email_existe_en_sistema(email):
            messages.error(request, 'Este correo electrónico ya está registrado como SuperAdministrador, Administrador o Usuario. No se puede duplicar.')
            return render(request, 'core/usuarios/usuario_form.html', {'empresas': empresas})
        
        empresa = Empresa.objects.using('default').get(pk=empresa_id)
        grupo_id = empresa.grupo_id

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


        # Verificar email en todo el sistema
        if email_existe_en_sistema(email):
            messages.error(request, 'Este correo electrónico ya está registrado como SuperAdministrador, Administrador o Usuario. No se puede duplicar.')
            return render(request, 'core/usuarios/usuario_form.html', {'empresas': empresas})

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
def admin_correo_crear_2(request):
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
def admin_correo_editar_2(request, pk):
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
def admin_correo_crear_3(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        messages.error(request, 'No se ha identificado la base de datos de la empresa.')
        return redirect('dashboard')

    # Obtener configuración de envío actual (si existe) - para mostrarla en el formulario
    config_envio = None
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT * FROM configuracion_envio_correo LIMIT 1")
        config_envio = cursor.fetchone()

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        titulo = request.POST.get('titulo')
        cuerpo = request.POST.get('cuerpo')
        if not tipo or not titulo or not cuerpo:
            messages.error(request, 'Todos los campos de la plantilla son obligatorios.')
            return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})

        # Guardar plantilla
        with connections[db_name].cursor() as cursor:
            # Verificar si ya existe configuración para ese tipo
            cursor.execute("SELECT COUNT(*) FROM configuracion_correos WHERE tipo = %s", [tipo])
            if cursor.fetchone()[0] > 0:
                messages.error(request, f'Ya existe una configuración para el tipo "{tipo}".')
                return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})
            cursor.execute(
                "INSERT INTO configuracion_correos (tipo, titulo, cuerpo) VALUES (%s, %s, %s)",
                [tipo, titulo, cuerpo]
            )

        # Guardar configuración de envío (si se enviaron datos)
        proveedor = request.POST.get('proveedor')
        if proveedor:
            host = request.POST.get('host')
            puerto = request.POST.get('puerto')
            usuario = request.POST.get('usuario')
            password = request.POST.get('password')
            use_tls = 1 if request.POST.get('use_tls') else 0
            use_ssl = 1 if request.POST.get('use_ssl') else 0
            api_key = request.POST.get('api_key')
            logo_path = None
            if 'logo' in request.FILES:
                logo = request.FILES['logo']
                ext = logo.name.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                    messages.error(request, 'El logo debe ser una imagen (JPG, PNG, WEBP).')
                    return render(request, 'core/correos/admin_correo_form.html', {'correo': correo if 'correo' in locals() else None, 'config_envio': config_envio})
                
                rfc_empresa = request.session.get('empresa_rfc', 'empresa')
                nombre_archivo = f"logo_{rfc_empresa}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                ruta = os.path.join('logos_empresa', nombre_archivo)
                logo_path = default_storage.save(ruta, ContentFile(logo.read()))
                
                # Si ya existía un logo en la configuración anterior, lo borramos
                if config_envio and config_envio.get('logo'):
                    old_logo = config_envio['logo']
                    if default_storage.exists(old_logo):
                        default_storage.delete(old_logo)


            with connections[db_name].cursor() as cursor:
                if config_envio:
                    cursor.execute("""
                        UPDATE configuracion_envio_correo SET proveedor=%s, host=%s, puerto=%s, usuario=%s, password=%s,
                        use_tls=%s, use_ssl=%s, api_key=%s, logo=%s WHERE id=%s
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path, config_envio[0]])
                else:
                    cursor.execute("""
                        INSERT INTO configuracion_envio_correo (proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path])
                messages.success(request, 'Configuración de envío guardada.')

        messages.success(request, 'Configuración de correo creada correctamente.')
        return redirect('admin_correos_lista')

    return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})


@admin_required
def admin_correo_crear(request):
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        messages.error(request, 'No se ha identificado la base de datos de la empresa.')
        return redirect('dashboard')

    # Obtener configuración de envío actual (si existe) como diccionario
    config_envio = None
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT * FROM configuracion_envio_correo LIMIT 1")
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            config_envio = dict(zip(columns, row))

    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        titulo = request.POST.get('titulo')
        cuerpo = request.POST.get('cuerpo')
        if not tipo or not titulo or not cuerpo:
            messages.error(request, 'Todos los campos de la plantilla son obligatorios.')
            return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})

        # Guardar plantilla
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM configuracion_correos WHERE tipo = %s", [tipo])
            if cursor.fetchone()[0] > 0:
                messages.error(request, f'Ya existe una configuración para el tipo "{tipo}".')
                return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})
            cursor.execute(
                "INSERT INTO configuracion_correos (tipo, titulo, cuerpo) VALUES (%s, %s, %s)",
                [tipo, titulo, cuerpo]
            )
        messages.success(request, 'Plantilla de correo guardada correctamente.')

        # Guardar / actualizar configuración de envío (si se enviaron datos)
        proveedor = request.POST.get('proveedor')
        if proveedor:
            host = request.POST.get('host')
            puerto = request.POST.get('puerto')
            usuario = request.POST.get('usuario')
            password = request.POST.get('password')
            use_tls = 1 if request.POST.get('use_tls') else 0
            use_ssl = 1 if request.POST.get('use_ssl') else 0
            api_key = request.POST.get('api_key')
            logo_path = None

            # Procesar logo si se envió
            if 'logo' in request.FILES:
                logo = request.FILES['logo']
                ext = logo.name.split('.')[-1].lower()
                if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                    messages.error(request, 'El logo debe ser una imagen (JPG, PNG, WEBP).')
                    return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})
                
                rfc_empresa = request.session.get('empresa_rfc', 'empresa')
                nombre_archivo = f"logo_{rfc_empresa}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                ruta = os.path.join('logos_empresa', nombre_archivo)
                logo_path = default_storage.save(ruta, ContentFile(logo.read()))
                
                # Eliminar logo anterior si existe
                if config_envio and config_envio.get('logo'):
                    old_logo = config_envio['logo']
                    if default_storage.exists(old_logo):
                        default_storage.delete(old_logo)
            else:
                # Si no se subió nuevo logo, conservar el existente (si lo hay)
                if config_envio and config_envio.get('logo'):
                    logo_path = config_envio['logo']

            with connections[db_name].cursor() as cursor:
                if config_envio:
                    cursor.execute("""
                        UPDATE configuracion_envio_correo
                        SET proveedor=%s, host=%s, puerto=%s, usuario=%s, password=%s,
                            use_tls=%s, use_ssl=%s, api_key=%s, logo=%s
                        WHERE id=%s
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path, config_envio['id']])
                else:
                    cursor.execute("""
                        INSERT INTO configuracion_envio_correo
                        (proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path])
            messages.success(request, 'Configuración de envío guardada correctamente.')

        messages.success(request, 'Configuración general de correo completada.')
        return redirect('admin_correos_lista')

    return render(request, 'core/correos/admin_correo_form.html', {'config_envio': config_envio})


@admin_required
def admin_correo_editar_3(request, pk):
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
        correo = {'id': row[0], 'tipo': row[1], 'titulo': row[2], 'cuerpo': row[3]}

        # Obtener configuración de envío actual
        cursor.execute("SELECT * FROM configuracion_envio_correo LIMIT 1")
        config_envio = cursor.fetchone()

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        cuerpo = request.POST.get('cuerpo')
        if not titulo or not cuerpo:
            messages.error(request, 'Título y cuerpo son obligatorios.')
            return render(request, 'core/correos/admin_correo_form.html', {'correo': correo, 'config_envio': config_envio})

        with connections[db_name].cursor() as cursor:
            cursor.execute(
                "UPDATE configuracion_correos SET titulo = %s, cuerpo = %s WHERE id = %s",
                [titulo, cuerpo, pk]
            )

            # Guardar configuración de envío si enviaron datos
            proveedor = request.POST.get('proveedor')
            if proveedor:
                host = request.POST.get('host')
                puerto = request.POST.get('puerto')
                usuario = request.POST.get('usuario')
                password = request.POST.get('password')
                use_tls = 1 if request.POST.get('use_tls') else 0
                use_ssl = 1 if request.POST.get('use_ssl') else 0
                api_key = request.POST.get('api_key')
                logo_path = None
                if 'logo' in request.FILES:
                    logo = request.FILES['logo']
                    ext = logo.name.split('.')[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        messages.error(request, 'El logo debe ser una imagen (JPG, PNG, WEBP).')
                        return render(request, 'core/correos/admin_correo_form.html', {'correo': correo if 'correo' in locals() else None, 'config_envio': config_envio})
                    
                    rfc_empresa = request.session.get('empresa_rfc', 'empresa')
                    nombre_archivo = f"logo_{rfc_empresa}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                    ruta = os.path.join('logos_empresa', nombre_archivo)
                    logo_path = default_storage.save(ruta, ContentFile(logo.read()))
                    
                    # Si ya existía un logo en la configuración anterior, lo borramos
                    if config_envio and config_envio.get('logo'):
                        old_logo = config_envio['logo']
                        if default_storage.exists(old_logo):
                            default_storage.delete(old_logo)




                if config_envio:
                    cursor.execute("""
                        UPDATE configuracion_envio_correo SET proveedor=%s, host=%s, puerto=%s, usuario=%s, password=%s,
                        use_tls=%s, use_ssl=%s, api_key=%s, logo=%s WHERE id=%s
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path, config_envio[0]])
                else:
                    cursor.execute("""
                        INSERT INTO configuracion_envio_correo (proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo, activo)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                        """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path])
                    messages.success(request, 'Configuración de envío guardada.')

        messages.success(request, 'Configuración actualizada correctamente.')
        return redirect('admin_correos_lista')

    return render(request, 'core/correos/admin_correo_form.html', {'correo': correo, 'config_envio': config_envio})


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
        correo = {'id': row[0], 'tipo': row[1], 'titulo': row[2], 'cuerpo': row[3]}

        # Obtener configuración de envío actual como diccionario
        cursor.execute("SELECT * FROM configuracion_envio_correo LIMIT 1")
        row_envio = cursor.fetchone()
        if row_envio:
            columns = [col[0] for col in cursor.description]
            config_envio = dict(zip(columns, row_envio))
        else:
            config_envio = None

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        cuerpo = request.POST.get('cuerpo')
        if not titulo or not cuerpo:
            messages.error(request, 'Título y cuerpo son obligatorios.')
            return render(request, 'core/correos/admin_correo_form.html', {'correo': correo, 'config_envio': config_envio})

        with connections[db_name].cursor() as cursor:
            cursor.execute(
                "UPDATE configuracion_correos SET titulo = %s, cuerpo = %s WHERE id = %s",
                [titulo, cuerpo, pk]
            )

            # Guardar configuración de envío si enviaron datos
            proveedor = request.POST.get('proveedor')
            if proveedor:
                host = request.POST.get('host')
                puerto = request.POST.get('puerto')
                usuario = request.POST.get('usuario')
                password = request.POST.get('password')
                use_tls = 1 if request.POST.get('use_tls') else 0
                use_ssl = 1 if request.POST.get('use_ssl') else 0
                api_key = request.POST.get('api_key')
                
                # Manejo del logo
                logo_path = None
                if 'logo' in request.FILES:
                    from django.core.files.storage import default_storage
                    from django.core.files.base import ContentFile
                    import os
                    from datetime import datetime
                    logo = request.FILES['logo']
                    ext = logo.name.split('.')[-1].lower()
                    if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                        messages.error(request, 'El logo debe ser una imagen (JPG, PNG, WEBP).')
                        return render(request, 'core/correos/admin_correo_form.html', {'correo': correo, 'config_envio': config_envio})
                    rfc_empresa = request.session.get('empresa_rfc', 'empresa')
                    nombre_archivo = f"logo_{rfc_empresa}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
                    ruta = os.path.join('logos_empresa', nombre_archivo)
                    logo_path = default_storage.save(ruta, ContentFile(logo.read()))
                    # Eliminar logo anterior si existe
                    if config_envio and config_envio.get('logo'):
                        old_logo = config_envio['logo']
                        if default_storage.exists(old_logo):
                            default_storage.delete(old_logo)
                else:
                    # Si no se sube nuevo logo, conservar el anterior
                    logo_path = config_envio.get('logo') if config_envio else None

                if config_envio:
                    cursor.execute("""
                        UPDATE configuracion_envio_correo 
                        SET proveedor=%s, host=%s, puerto=%s, usuario=%s, password=%s,
                            use_tls=%s, use_ssl=%s, api_key=%s, logo=%s
                        WHERE id=%s
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path, config_envio['id']])
                else:
                    cursor.execute("""
                        INSERT INTO configuracion_envio_correo 
                        (proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo, activo)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
                    """, [proveedor, host, puerto, usuario, password, use_tls, use_ssl, api_key, logo_path])

                messages.success(request, 'Configuración de envío guardada.')
            else:
                # Si no se seleccionó proveedor, no se modifica la configuración de envío
                pass

        messages.success(request, 'Configuración actualizada correctamente.')
        return redirect('admin_correos_lista')

    return render(request, 'core/correos/admin_correo_form.html', {'correo': correo, 'config_envio': config_envio})

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
def usuario_revisar_peticiones_2(request):
    # ========== Funciones auxiliares (definidas primero) ==========
    def extraer_datos_factura_2(xml_path, rfc_receptor):
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

    def procesar_factura_normal_2(root, ns, rfc_receptor):
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

    def procesar_complemento_pago_2(root, ns, rfc_receptor):
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

    def insertar_cfdi_2(db_name, datos, logs):
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

    def registrar_proveedor_2(db_name, rfc_prov, nombre, rfc_cliente, logs):
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


import json
import threading
import uuid
import os
import tempfile
import zipfile
import glob
import base64
import xml.etree.ElementTree as ET
import shutil
from datetime import datetime, date
from django.db import connections
from django.http import JsonResponse
from django.conf import settings
from django.core.signing import loads
from django.views.decorators.csrf import csrf_exempt
from .decorators import usuario_required

# ========== DICCIONARIOS AUXILIARES ==========
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

# ========== FUNCIONES AUXILIARES (extraídas fuera de la vista) ==========

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
    except Exception as e:
        logs.append(f"    Error registrando proveedor: {str(e)}")

# ========== FUNCIONES PARA MANEJO DE TAREAS EN BD ==========

def crear_tarea(task_id, tipo, db_name, rfc_empresa, empresa_nombre,logs=None):
    """Inserta una nueva tarea en la base de datos central."""
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            INSERT INTO tareas_asincronas (task_id, tipo, empresa_db_name, rfc_empresa, empresa_nombre, logs)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [task_id, tipo, db_name, rfc_empresa, empresa_nombre, json.dumps([])])

def actualizar_tarea(task_id, logs=None, estado=None, success=None, error=None):
    """Actualiza logs, estado y resultado de una tarea."""
    with connections['default'].cursor() as cursor:
        if logs is not None:
            cursor.execute("UPDATE tareas_asincronas SET logs = %s WHERE task_id = %s", [json.dumps(logs), task_id])
        if estado is not None:
            cursor.execute("UPDATE tareas_asincronas SET estado = %s WHERE task_id = %s", [estado, task_id])
        if success is not None:
            cursor.execute("UPDATE tareas_asincronas SET success = %s WHERE task_id = %s", [success, task_id])
        if error is not None:
            cursor.execute("UPDATE tareas_asincronas SET error = %s WHERE task_id = %s", [error, task_id])
        cursor.execute("UPDATE tareas_asincronas SET fecha_actualizacion = NOW() WHERE task_id = %s", [task_id])

def obtener_tarea(task_id):
    """Recupera una tarea por su ID."""
    with connections['default'].cursor() as cursor:
        cursor.execute("SELECT logs, estado, success, error FROM tareas_asincronas WHERE task_id = %s", [task_id])
        row = cursor.fetchone()
        if not row:
            return None
        logs = json.loads(row[0]) if row[0] else []
        estado = row[1]
        success = bool(row[2])
        error = row[3]
        finished = estado != 'en_proceso'
        return {
            'finished': finished,
            'logs': logs,
            'success': success,
            'error': error
        }

# ========== TAREAS ASÍNCRONAS (RECIBIDAS) ==========

def run_revisar_peticiones_task(task_id, db_name, rfc_empresa, empresa_nombre):
    logs = []
    try:
        from empresas.models import EFirma
        from satcfdi.models import Signer
        from satcfdi.pacs.sat import SAT, EstadoSolicitud

        actualizar_tarea(task_id, logs=logs, estado='en_proceso')

        efirma = EFirma.objects.using('default').get(empresa=empresa_nombre, estatus='validado')

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

        total_descargas = 0
        total_procesados = 0

        # 1. Descarga
        for id_peticion, fechainicio in peticiones_descarga:
            logs.append(f"Verificando petición {id_peticion}...")
            actualizar_tarea(task_id, logs=logs)
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
            actualizar_tarea(task_id, logs=logs)

        # 2. Procesamiento XML
        for id_peticion, fechainicio in peticiones_procesar:
            logs.append(f"Procesando XML de petición {id_peticion}...")
            actualizar_tarea(task_id, logs=logs)
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
                    actualizar_tarea(task_id, logs=logs)
                if zips:
                    with connections[db_name].cursor() as cursor_upd:
                        cursor_upd.execute("UPDATE peticiones_sat SET cargadoxml = 1 WHERE idpeticion = %s", [id_peticion])
                    logs.append("  Petición marcada como procesada (XML cargados).")
                    total_procesados += 1
            except Exception as e:
                logs.append(f"  Error procesando petición {id_peticion}: {str(e)}")
            actualizar_tarea(task_id, logs=logs)

        if total_descargas == 0 and total_procesados == 0:
            logs.append("No se encontraron peticiones pendientes o no se pudo descargar ningún paquete.")
        else:
            logs.append(f"Proceso completado. Descargas: {total_descargas}, XML procesados: {total_procesados}.")

        actualizar_tarea(task_id, logs=logs, estado='completado', success=True)
    except Exception as e:
        error_msg = str(e)
        logs.append(f"❌ Error general: {error_msg}")
        actualizar_tarea(task_id, logs=logs, estado='error', success=False, error=error_msg)

# ========== VISTAS ASÍNCRONAS (MODIFICADAS) ==========

@usuario_required
@csrf_exempt
def usuario_revisar_peticiones_async(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    empresa_nombre = request.session.get('empresa_nombre')
    if not db_name or not rfc_empresa or not empresa_nombre:
        return JsonResponse({'status': 'error', 'message': 'No se ha identificado la empresa.'}, status=400)

    task_id = str(uuid.uuid4())
    crear_tarea(task_id, 'recibidas', db_name, rfc_empresa, empresa_nombre)
    thread = threading.Thread(target=run_revisar_peticiones_task, args=(task_id, db_name, rfc_empresa, empresa_nombre))
    thread.daemon = True
    thread.start()
    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_revisar_peticiones_status(request, task_id):
    tarea = obtener_tarea(task_id)
    if not tarea:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse(tarea)






# ========== FUNCIONES AUXILIARES PARA EMITIDAS (fuera de cualquier vista) ==========



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
    }
    timbre = root.find('cfdi:Complemento//tfd:TimbreFiscalDigital', ns)
    if timbre is not None:
        datos['uuid'] = timbre.get('UUID')
        datos['fecha_timbrado'] = timbre.get('FechaTimbrado')[:10] if timbre.get('FechaTimbrado') else None
    return datos

def procesar_complemento_pago_emitida(root, ns, rfc_emisor):
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
    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM clientes WHERE RFC = %s AND rfc_identy = %s", [rfc_cliente, rfc_empresa])
            if cursor.fetchone()[0] > 0:
                return
            cursor.execute("""
                INSERT INTO clientes (RFC, RazonSocial, Estatus, tipoProveedor, Correo, rfc_identy)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [rfc_cliente, nombre, 'SinRespuesta', 'Otro', 'generico@generico.com', rfc_empresa])
        logs.append(f"    Cliente registrado: {rfc_cliente} - {nombre}")
    except Exception as e:
        logs.append(f"    Error registrando cliente: {str(e)}")

# ========== TAREA ASÍNCRONA PARA EMITIDAS ==========

def run_revisar_peticiones_emitidas_task(task_id, db_name, rfc_empresa, empresa_nombre):
    logs = []
    try:
        from empresas.models import EFirma
        from satcfdi.models import Signer
        from satcfdi.pacs.sat import SAT, EstadoSolicitud

        actualizar_tarea(task_id, logs=logs, estado='en_proceso')

        efirma = EFirma.objects.using('default').get(empresa=empresa_nombre, estatus='validado')

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

        total_descargas = 0
        total_procesados = 0

        # 1. Descarga
        for id_peticion, fechainicio in peticiones_descarga:
            logs.append(f"Verificando petición emitida {id_peticion}...")
            actualizar_tarea(task_id, logs=logs)
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
            actualizar_tarea(task_id, logs=logs)

        # 2. Procesamiento XML
        for id_peticion, fechainicio in peticiones_procesar:
            logs.append(f"Procesando XML de petición emitida {id_peticion}...")
            actualizar_tarea(task_id, logs=logs)
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
                    actualizar_tarea(task_id, logs=logs)
                if zips:
                    with connections[db_name].cursor() as cursor_upd:
                        cursor_upd.execute("UPDATE peticiones_sat SET cargadoxml = 1 WHERE idpeticion = %s", [id_peticion])
                    logs.append("  Petición emitida marcada como procesada (XML cargados).")
                    total_procesados += 1
            except Exception as e:
                logs.append(f"  Error procesando petición {id_peticion}: {str(e)}")
            actualizar_tarea(task_id, logs=logs)

        if total_descargas == 0 and total_procesados == 0:
            logs.append("No se encontraron peticiones emitidas pendientes o no se pudo descargar ningún paquete.")
        else:
            logs.append(f"Proceso completado. Descargas: {total_descargas}, XML procesados: {total_procesados}.")

        actualizar_tarea(task_id, logs=logs, estado='completado', success=True)
    except Exception as e:
        error_msg = str(e)
        logs.append(f"❌ Error general: {error_msg}")
        actualizar_tarea(task_id, logs=logs, estado='error', success=False, error=error_msg)

# ========== VISTAS ASÍNCRONAS PARA EMITIDAS ==========

@usuario_required
@csrf_exempt
def usuario_revisar_peticiones_emitidas_async(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    empresa_nombre = request.session.get('empresa_nombre')
    if not db_name or not rfc_empresa or not empresa_nombre:
        return JsonResponse({'status': 'error', 'message': 'No se ha identificado la empresa.'}, status=400)

    task_id = str(uuid.uuid4())
    crear_tarea(task_id, 'emitidas', db_name, rfc_empresa, empresa_nombre)
    thread = threading.Thread(target=run_revisar_peticiones_emitidas_task, args=(task_id, db_name, rfc_empresa, empresa_nombre))
    thread.daemon = True
    thread.start()
    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_revisar_peticiones_emitidas_status(request, task_id):
    tarea = obtener_tarea(task_id)
    if not tarea:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse(tarea)






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
def usuario_opiniones_data_2(request):
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
        # Obtener estatus crudo
        estatus_raw = row[2] if row[2] is not None else ''
        fecha_opinion = row[3]  # puede ser None o un objeto date
        # Mapear 'SinRespuesta' según condición
        if estatus_raw == 'SinRespuesta':
            if fecha_opinion:
                estatus_display = 'Opinion No Publica'
            else:
                estatus_display = '-'
        else:
            estatus_display = estatus_raw

        data.append({
            'rfc': row[0] or '',
            'razon_social': row[1] or '',
            'estatus': estatus_display,
            'fecha_opinion': row[3].strftime('%Y-%m-%d') if row[3] else '',
            'opinion': row[4] or 0,
            'tipo': row[5],
        })
    return JsonResponse(data, safe=False)


@usuario_required
def usuario_opiniones_data(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'proveedor' as tipo
            FROM proveedores WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows = list(cursor.fetchall())

        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'proveedor_sin_cfdi' as tipo
            FROM proveedores_sin_cfdi WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'cliente' as tipo
            FROM clientes WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

        cursor.execute("""
            SELECT RFC, RazonSocial, Estatus, fecha_opinion, opinion, 'cliente_sin_cfdi' as tipo
            FROM clientes_sin_cfdi WHERE rfc_identy = %s
        """, [rfc_empresa])
        rows.extend(cursor.fetchall())

    data = []
    for row in rows:
        rfc = row[0] or ''
        razon_social = row[1] or ''
        estatus_raw = row[2] if row[2] is not None else ''
        fecha_opinion = row[3]
        opinion = row[4] or 0
        tipo_interno = row[5]

        # Mapear estatus
        if estatus_raw == 'SinRespuesta':
            estatus_display = 'Opinion No Publica' if fecha_opinion else '-'
        else:
            estatus_display = estatus_raw

        # Mapear tipo a nombre amigable
        if tipo_interno == 'proveedor':
            tipo_nombre = 'Proveedor'
        elif tipo_interno == 'proveedor_sin_cfdi':
            tipo_nombre = 'Proveedor Prospecto'
        elif tipo_interno == 'cliente':
            tipo_nombre = 'Cliente'
        elif tipo_interno == 'cliente_sin_cfdi':
            tipo_nombre = 'Cliente Prospecto'
        else:
            tipo_nombre = tipo_interno

        data.append({
            'rfc': rfc,
            'razon_social': razon_social,
            'tipo_nombre': tipo_nombre,
            'estatus': estatus_display,
            'fecha_opinion': fecha_opinion.strftime('%Y-%m-%d') if fecha_opinion else '',
            'opinion': opinion,
            'tipo': tipo_interno,   # para uso interno
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

def obtener_opinion_sat______(rfc, download_dir, logs):
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
    
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--user-data-dir=/tmp/chrome-user-data")  # Evita conflictos de perfiles
    options.add_argument("--disk-cache-dir=/tmp/chrome-cache")
    options.add_argument("--log-level=3")  # Reduce logs
    options.add_argument("--silent")

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
from PyPDF2 import PdfReader

def obtener_opinion_sat(rfc, download_dir, logs):
    """
    Consulta la opinión de cumplimiento del SAT usando Selenium Chrome.
    Retorna:
      - {'pdf_path': path, 'fecha': date, 'resultado': str} si hay PDF
      - {'status': str, 'fecha': date} si solo hay estatus
      - None si falla
    """
    options = Options()
    # Argumentos esenciales para entornos headless y restringidos
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-data-dir=/tmp/chrome-user-data")
    options.add_argument("--disk-cache-dir=/tmp/chrome-cache")
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option('prefs', {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    })
    
    # Variables de entorno adicionales
    os.environ['TMPDIR'] = '/tmp'
    
    # Asegurar que el directorio de descarga existe
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # Descargar/actualizar ChromeDriver automáticamente
        service = Service(ChromeDriverManager().install())
        #driver = webdriver.Chrome(service=service, options=options)
        driver = webdriver.Chrome(options=options)

        logs.append("✅ Navegador iniciado correctamente")
    except Exception as e:
        logs.append(f"❌ Error al iniciar Chrome: {str(e)}")
        return None

    try:
        url = 'https://ptsc32d.clouda.sat.gob.mx/ConsultaPublico'
        driver.get(url)
        logs.append("🌐 Página del SAT cargada")
        
        # Configurar descarga automática (ya está en prefs, pero repetimos por si acaso)
        driver.execute_cdp_cmd('Page.setDownloadBehavior', {
            'behavior': 'allow',
            'downloadPath': download_dir
        })
        
        # Ingresar RFC letra por letra (más realista)
        rfc_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "txtRfc"))
        )
        rfc_input.clear()
        for c in rfc:
            rfc_input.send_keys(c)
            time.sleep(0.1)
        logs.append(f"🔑 RFC {rfc} ingresado")
        
        # Hacer clic en buscar
        driver.find_element(By.ID, "buqueda").click()
        logs.append("🔍 Buscando...")
        
        # Esperar un momento para que cargue la respuesta
        time.sleep(5)
        
        # Obtener texto de la página
        body = driver.find_element(By.TAG_NAME, "body")
        texto_pagina = body.text
        
        # Patrones para identificar el resultado
        patron_negativo = r"El RFC o CURP, no cumple con los requisitos para hacer pública su opinión positiva"
        patron_sin_respuesta = r"El RFC o CURP consultado no se encuentra autorizado para hacerse público"
        patron_positivo = r"Opinión Positiva.* Información a la fecha de la consulta"
        
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
        
        # Localizar iframe (puede cambiar con el tiempo, pero la ruta es común)
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

        # Hacer clic en el botón de descarga del PDF
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
        
        # Esperar a que se descargue el archivo (máximo 15 segundos)
        time.sleep(10)
        archivos = [f for f in os.listdir(download_dir) if f.endswith('.pdf')]
        if not archivos:
            logs.append("❌ No se detectó ningún PDF descargado")
            driver.quit()
            return None
        
        # Ordenar por fecha de modificación descendente
        archivos.sort(key=lambda x: os.path.getmtime(os.path.join(download_dir, x)), reverse=True)
        pdf_path = os.path.join(download_dir, archivos[0])
        logs.append(f"✅ PDF descargado: {os.path.basename(pdf_path)}")
        
        # Extraer datos del PDF
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            texto_pdf = ""
            for page in reader.pages:
                texto_pdf += page.extract_text()
        
        # Extraer fecha
        patron_fecha = r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s+a\s+las\s+(\d{1,2}:\d{2})\s+horas'
        match_fecha = re.search(patron_fecha, texto_pdf)
        if not match_fecha:
            logs.append("❌ No se encontró la fecha en el PDF")
            driver.quit()
            return None
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
        match_res = re.search(patron_resultado, texto_pdf)
        resultado = 'Positivo' if match_res and match_res.group(1) == 'P' else 'Negativo' if match_res and match_res.group(1) == 'N' else 'SinRespuesta'
        logs.append(f"📊 Datos extraídos: fecha={fecha_opinion}, resultado={resultado}")
        
        driver.quit()
        return {'pdf_path': pdf_path, 'fecha': fecha_opinion, 'resultado': resultado}
        
    except Exception as e:
        logs.append(f"❌ Error general: {str(e)}")
        try:
            driver.quit()
        except:
            pass
        return None
    


# ========== TAREA ASÍNCRONA PARA OPINIONES (con BD) ==========

def run_opinion_task(task_id, rfc, tipo_entidad, db_name, rfc_empresa, empresa_nombre):
    """
    Ejecuta la obtención de opinión del SAT en segundo plano.
    """
    logs = []
    try:
        from empresas.models import EFirma
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        import time, re, shutil, os, base64
        from datetime import datetime
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage
        from django.conf import settings

        actualizar_tarea(task_id, logs=logs, estado='en_proceso')
        logs.append("🚀 Iniciando proceso de obtención de opinión del SAT...")
        actualizar_tarea(task_id, logs=logs)

        # Crear directorio temporal
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_opinions', rfc)
        os.makedirs(temp_dir, exist_ok=True)
        logs.append("📁 Directorio temporal creado")
        actualizar_tarea(task_id, logs=logs)

        # Llamar a la función que obtiene la opinión (puedes usar la que ya tienes)
        # Asumo que existe la función obtener_opinion_sat que retorna un dict con 'pdf_path', 'fecha', 'resultado' o 'status'
        # Si tu función se llama diferente, ajústala.
        from .views import obtener_opinion_sat  # o la ruta donde esté
        resultado = obtener_opinion_sat(rfc, temp_dir, logs)  # le pasamos logs para que los vaya llenando

        if resultado is None:
            raise Exception("No se pudo completar la operación")

        tabla_map = {
            'proveedor': 'proveedores',
            'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
            'cliente': 'clientes',
            'cliente_sin_cfdi': 'clientes_sin_cfdi'
        }
        tabla = tabla_map.get(tipo_entidad)
        if not tabla:
            raise Exception(f"Tipo de entidad inválido: {tipo_entidad}")

        with connections[db_name].cursor() as cursor:
            if 'pdf_path' in resultado:
                # Guardar PDF
                año = resultado['fecha'].year
                mes = resultado['fecha'].month
                ruta_destino = os.path.join('opinion', rfc, str(año), f"{mes:02d}")
                nombre_archivo = f"{rfc}_{resultado['fecha'].strftime('%Y%m%d')}.pdf"
                destino = default_storage.save(
                    os.path.join(ruta_destino, nombre_archivo),
                    ContentFile(open(resultado['pdf_path'], 'rb').read())
                )
                logs.append(f"📁 PDF guardado en: {destino}")
                actualizar_tarea(task_id, logs=logs)

                # Insertar historial
                cursor.execute("""
                    INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, tipo_entidad, destino, resultado['resultado'], resultado['fecha']])

                # Actualizar tabla principal
                sql = f"""
                    UPDATE {tabla}
                    SET Estatus = %s, fecha_opinion = %s, opinion = 1
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [resultado['resultado'], resultado['fecha'], rfc, rfc_empresa])
                logs.append(f"✅ Registro actualizado con PDF (resultado: {resultado['resultado']})")
                actualizar_tarea(task_id, logs=logs)

                # Eliminar archivo temporal
                os.remove(resultado['pdf_path'])
            else:
                # Sin PDF (solo estatus)
                fecha_actual = resultado['fecha']
                sql = f"""
                    UPDATE {tabla}
                    SET Estatus = %s, fecha_opinion = %s, opinion = 0
                    WHERE RFC = %s AND rfc_identy = %s
                """
                cursor.execute(sql, [resultado['status'], fecha_actual, rfc, rfc_empresa])
                logs.append(f"✅ Registro actualizado sin PDF (estatus: {resultado['status']})")
                actualizar_tarea(task_id, logs=logs)

                cursor.execute("""
                    INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                    VALUES (%s, %s, %s, %s, %s)
                """, [rfc, tipo_entidad, '', resultado['status'], fecha_actual])

        actualizar_tarea(task_id, logs=logs, estado='completado', success=True)
        logs.append("🎉 Proceso terminado correctamente")
        actualizar_tarea(task_id, logs=logs)

    except Exception as e:
        error_msg = str(e)
        logs.append(f"❌ Error: {error_msg}")
        actualizar_tarea(task_id, logs=logs, estado='error', success=False, error=error_msg)
        # Opcional: puedes imprimir el traceback en los logs del servidor
        import traceback
        traceback.print_exc()

@usuario_required
@csrf_exempt
def usuario_opiniones_obtener_sat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    rfc = request.POST.get('rfc')
    tipo_entidad = request.POST.get('tipo')
    if not rfc or not tipo_entidad:
        return JsonResponse({'error': 'Faltan datos (RFC o tipo)'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    empresa_nombre = request.session.get('empresa_nombre')
    if not db_name or not rfc_empresa or not empresa_nombre:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    task_id = str(uuid.uuid4())
    logs_inicial = [f"🚀 Iniciando obtención de opinión para RFC {rfc}"]
    crear_tarea(task_id, 'opinion', db_name, rfc_empresa, empresa_nombre, logs_inicial)

    thread = threading.Thread(target=run_opinion_task, args=(task_id, rfc, tipo_entidad, db_name, rfc_empresa, empresa_nombre))
    thread.daemon = True
    thread.start()

    return JsonResponse({'task_id': task_id})

@usuario_required
def usuario_opiniones_obtener_sat_status(request, task_id):
    tarea = obtener_tarea(task_id)
    if not tarea:
        return JsonResponse({'error': 'Tarea no encontrada'}, status=404)
    return JsonResponse({
        'finished': tarea['finished'],
        'logs': tarea['logs'],
        'success': tarea['success'],
        'error': tarea['error']
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

    # Mapeo de tipo interno a nombre amigable
    tipo_nombres = {
        'proveedor': 'Proveedor',
        'proveedor_sin_cfdi': 'Proveedor Prospecto',
        'cliente': 'Cliente',
        'cliente_sin_cfdi': 'Cliente Prospecto'
    }

    data = []
    for row in rows:

        constancia_flag = row[4] or 0
        estatus_display = 'Cargada' if constancia_flag == 1 else 'Sin Cargar'
        tipo = row[5]
        tipo_nombre = tipo_nombres.get(tipo, tipo)

        data.append({
            'rfc': row[0] or '',
            'razon_social': row[1] or '',
            'estatus': estatus_display,
            'fecha_constancia': row[3].strftime('%Y-%m-%d') if row[3] else '',
            'constancia': row[4] or 0,
            'tipo': row[5],
            'tipo_nombre': tipo_nombre,

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




import pdfplumber
import re

def normalizar_texto(texto):
    # Inserta saltos de línea antes de cada etiqueta conocida
    etiquetas = [
        "CódigoPostal:", "TipodeVialidad:", "NombredeVialidad:", "NúmeroExterior:",
        "NúmeroInterior:", "NombredelaColonia:", "NombredelaLocalidad:",
        "NombredelMunicipiooDemarcaciónTerritorial:", "NombredelaEntidadFederativa:",
        "EntreCalle:", "YCalle:"
    ]
    for etiqueta in etiquetas:
        texto = texto.replace(etiqueta, "\n" + etiqueta)
    return texto



def extraer_datos_constancia(archivo_pdf):
    texto = ""
    with pdfplumber.open(archivo_pdf) as pdf:
        for page in pdf.pages:
            texto += page.extract_text()


    texto = normalizar_texto(texto)

    print('TEXTO')
    print(texto)


    datos = {}

    # RFC
    rfc_match = re.search(r"RFC:\s*([A-Z0-9]+)", texto)
    if not rfc_match:
        raise ValueError("No se encontró RFC en el PDF")
    datos['rfc'] = rfc_match.group(1)

    # Fecha constancia
    fecha_match = re.search(r"(\d{1,2} DE [A-Z]+ DE \d{4})", texto)
    if fecha_match:
        try:
            datos['fecha_constancia'] = datetime.strptime(fecha_match.group(1), "%d DE %B DE %Y")
        except Exception:
            datos['fecha_constancia'] = datetime.today()
    else:
        datos['fecha_constancia'] = datetime.today()

    # Datos de ubicación
    cp = re.search(r"CódigoPostal: *(\d+)", texto)
    print('CP')
    print(cp)
    calle = re.search(r"NombredeVialidad: *([A-Z\s]+)", texto)
    no_ext = re.search(r"NúmeroExterior: *(\d+)", texto)
    no_int = re.search(r"NúmeroInterior:\s*([A-Z0-9]*)", texto)
    colonia = re.search(r"NombredelaColonia: *(.+)", texto)
    localidad = re.search(r"NombredelaLocalidad: *(.+)", texto)
    municipio = re.search(r"NombredelMunicipiooDemarcaciónTerritorial: *(.+)", texto)
    estado = re.search(r"NombredelaEntidadFederativa: *(.+)", texto)

    datos['codigoPostal'] = cp.group(1) if cp else ""
    datos['calle'] = calle.group(1).strip() if calle else ""
    datos['noExt'] = no_ext.group(1) if no_ext else ""
    datos['noInt'] = no_int.group(1).strip() if no_int else ""
    datos['colonia'] = colonia.group(1).strip() if colonia else ""
    datos['ciudad'] = localidad.group(1).strip() if localidad else ""
    datos['municipio'] = municipio.group(1).strip() if municipio else ""
    datos['estado'] = estado.group(1).strip() if estado else ""

    return datos




@usuario_required
@csrf_exempt
def usuario_constancias_subir____(request):
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
                'CodigoPostal': datos['codigoPostal'],
                'Calle': datos['calle'],
                'NoInt': datos['noInt'],
                'NoExt': datos['noExt'],
                'Colonia': datos['colonia'],
                'Estado': datos['estado'],
                'Municipio': datos['municipio'],
                'Ciudad': datos['ciudad'],
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
    archivo.seek(0)
    path = default_storage.save(os.path.join(ruta, nombre_archivo), ContentFile(archivo.read()))

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
            cursor.execute("""
                INSERT INTO constancias_historial 
                (rfc, tipo, archivo_pdf, fecha_constancia, codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                rfc_seleccionado, tipo, path, datos['fecha_constancia'],
                datos['codigoPostal'], datos['calle'], datos['noInt'], datos['noExt'],
                datos['colonia'], datos['estado'], datos['municipio'], datos['ciudad']
            ])

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

    tipo_nombres = {
        'proveedor': 'Proveedor',
        'proveedor_sin_cfdi': 'Proveedor sin CFDI',
        'cliente': 'Cliente',
        'cliente_sin_cfdi': 'Cliente sin CFDI'
    }

    data = []
    with connections[db_name].cursor() as cursor:
        # Proveedores
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal,
                   municipio, estado, ciudad,
                   'proveedor' as tipo_interno,
                   COALESCE(domicilio_validado, 'Pendiente') as estado_validacion
            FROM proveedores
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['rfc'] = item.pop('RFC')  # Renombra la clave 'RFC' a 'rfc' si es necesario

            item['tipo_nombre'] = tipo_nombres.get(item['tipo_interno'], item['tipo_interno'])
            data.append(item)

        # Proveedores sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal,
                   municipio, estado, ciudad,
                   'proveedor_sin_cfdi' as tipo_interno,
                   COALESCE(domicilio_validado, 'Pendiente') as estado_validacion
            FROM proveedores_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['rfc'] = item.pop('RFC')  # Renombra la clave 'RFC' a 'rfc' si es necesario

            item['tipo_nombre'] = tipo_nombres.get(item['tipo_interno'], item['tipo_interno'])
            data.append(item)

        # Clientes
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal,
                   municipio, estado, ciudad,
                   'cliente' as tipo_interno,
                   COALESCE(domicilio_validado, 'Pendiente') as estado_validacion
            FROM clientes
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['rfc'] = item.pop('RFC')  # Renombra la clave 'RFC' a 'rfc' si es necesario

            item['tipo_nombre'] = tipo_nombres.get(item['tipo_interno'], item['tipo_interno'])
            data.append(item)

        # Clientes sin CFDI
        cursor.execute("""
            SELECT RFC, RazonSocial, calle, noExt, noInt, colonia, codigoPostal,
                   municipio, estado, ciudad,
                   'cliente_sin_cfdi' as tipo_interno,
                   COALESCE(domicilio_validado, 'Pendiente') as estado_validacion
            FROM clientes_sin_cfdi
            WHERE rfc_identy = %s
        """, [rfc_empresa])
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            item = dict(zip(columns, row))
            item['rfc'] = item.pop('RFC')  # Renombra la clave 'RFC' a 'rfc' si es necesario

            item['tipo_nombre'] = tipo_nombres.get(item['tipo_interno'], item['tipo_interno'])
            data.append(item)

    return JsonResponse(data, safe=False)


import requests
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import usuario_required

logger = logging.getLogger(__name__)

@usuario_required
@csrf_exempt
def validar_domicilio(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    
    rfc = data.get('rfc')
    tipo = data.get('tipo')          # "proveedor", "cliente", etc.
    local_data = data.get('datos')
    if not rfc or not tipo or not local_data:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
    
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)
    
    # Mapeo tipo -> tabla
    tabla_map = {
        'proveedor': 'proveedores',
        'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
        'cliente': 'clientes',
        'cliente_sin_cfdi': 'clientes_sin_cfdi'
    }
    tabla = tabla_map.get(tipo)
    if not tabla:
        return JsonResponse({'error': 'Tipo de entidad inválido'}, status=400)
    
    # Llamada a la API externa (como antes)
    api_url = 'https://ep-plataforma-cumplimiento-727717516813.us-central1.run.app'
    headers = {'API-KEY': 'PRUEBA_PLTF_CMPL_2026_SECRET'}
    params = {'limite': 2000}
    try:
        response = requests.get(api_url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        resultados = response.json()
        # Normalizar respuesta (como en la versión anterior)
        if isinstance(resultados, dict):
            registros = resultados.get('data') or resultados.get('results') or resultados.get('items') or [resultados]
        else:
            registros = resultados
        api_record = None
        for item in registros:
            if isinstance(item, dict) and item.get('rfc') == rfc:
                api_record = item
                break
        if not api_record:
            return JsonResponse({'error': f'RFC {rfc} no encontrado en el servicio externo'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error consultando API: {str(e)}'}, status=500)
    
    # Comparar campos (igual que antes)
    diferencias = []
    mapeo = {
        'calle': 'calle',
        'noExt': 'num_exterior',
        'noInt': 'num_interior',
        'colonia': 'colonia',
        'codigoPostal': 'cp',
        'municipio': 'delegacion',
        'estado': 'estado',
        'ciudad': 'ciudad'
    }
    for campo_local, campo_api in mapeo.items():
        valor_local = (local_data.get(campo_local) or '').strip().upper()
        valor_api = (api_record.get(campo_api) or '').strip().upper()
        if valor_local != valor_api:
            diferencias.append(f"{campo_local}: local='{valor_local}', API='{valor_api}'")
    
    estado = 'Incorrecto' if diferencias else 'Correcto'
    mensaje = '; '.join(diferencias) if diferencias else 'Todos los campos coinciden'
    
    # Guardar el estado en la base de datos
    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(f"""
                UPDATE {tabla}
                SET domicilio_validado = %s
                WHERE RFC = %s AND rfc_identy = %s
            """, [estado, rfc, rfc_empresa])
    except Exception as e:
        # Si la columna no existe, registra el error pero no impide la respuesta
        logger.exception(f"Error guardando validación: {e}")
    
    return JsonResponse({
        'status': estado,
        'message': mensaje,
        'diferencias': diferencias,
        'api_data': api_record
    })


import threading
import uuid
from datetime import datetime
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import usuario_required
from .utils import obtener_fecha_publicacion_sat, descargar_csv, obtener_rfcs_existentes,descargar_csv_por_indice,extraer_fecha_desde_csv


tasks_status = {}  # Diccionario para almacenar estado de tareas

def run_articulo69_task___2(task_id, db_name):
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


def run_articulo69_task(task_id, db_name):
    logs = []
    tasks_status[task_id] = {'logs': logs, 'finished': False, 'success': False, 'error': None}
    try:
        logs.append("🚀 Iniciando actualización de Artículo 69...")
        
        urls = [
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Exigibles.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/Firmes.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Documents_AGR/No_localizados.csv',
            'https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/AGR/03_02_26/Sentencias.csv'
        ]
        
        # Obtener fecha de publicación desde el primer CSV
        fecha_publicacion = None
        if urls:
            logs.append(f"📥 Obteniendo fecha de publicación desde {urls[0]}...")
            try:
                import requests
                response = requests.get(urls[0], timeout=30)
                response.raise_for_status()
                csv_content = response.content.decode('utf-8', errors='replace')
                fecha_publicacion = extraer_fecha_desde_csv(csv_content)
                print(fecha_publicacion)
                if fecha_publicacion:
                    logs.append(f"📅 Fecha publicación extraída: {fecha_publicacion}")
                else:
                    logs.append("⚠️ No se pudo extraer fecha, usando fecha actual")
                    fecha_publicacion = datetime.now().date()
            except Exception as e:
                logs.append(f"❌ Error obteniendo fecha: {str(e)}")
                fecha_publicacion = datetime.now().date()
        
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

        # Obtener fecha de publicación desde el primer CSV
        fecha_publicacion = None
        if urls:
            logs.append(f"📥 Obteniendo fecha de publicación desde {urls[0]}...")
            try:
                import requests
                response = requests.get(urls[0], timeout=30)
                response.raise_for_status()
                csv_content = response.content.decode('utf-8', errors='replace')
                fecha_publicacion = extraer_fecha_desde_csv(csv_content)
                print(fecha_publicacion)
                if fecha_publicacion:
                    logs.append(f"📅 Fecha publicación extraída: {fecha_publicacion}")
                else:
                    logs.append("⚠️ No se pudo extraer fecha, usando fecha actual")
                    fecha_publicacion = datetime.now().date()
            except Exception as e:
                logs.append(f"❌ Error obteniendo fecha: {str(e)}")
                fecha_publicacion = datetime.now().date()



        rfcs_validos = obtener_rfcs_existentes(db_name)
        logs.append(f"🔍 RFCs válidos en la empresa: {len(rfcs_validos)}")
        all_records = {}
        for url in urls:
            logs.append(f"📥 Descargando {url}...")
            rows = descargar_csv_por_indice(url)
            logs.append(f"   {len(rows)} registros.")

            # Las columnas según estructura del CSV:
            # Índice 1: RFC
            # Índice 2: Nombre del Contribuyente
            # Índice 3: Situación del contribuyente
            for row in rows:
                if len(row) < 4:
                    continue
                rfc = row[1].strip().upper()
                if rfc and rfc in rfcs_validos:
                    nombre = row[2].strip()[:255] if len(row) > 2 else ''
                    situacion = row[3].strip()[:255] if len(row) > 3 else ''
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



def run_articulo69bis_task_(task_id, db_name):
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
        print(rfcs_validos)
        logs.append(f"🔍 RFCs válidos en la empresa: {len(rfcs_validos)}")
        all_records = {}
        for url in urls:
            logs.append(f"📥 Descargando {url}...")
            data = descargar_csv_por_indice(url)
            print(data)
            logs.append(f"   {len(data)} registros.")
            for row in data:
                rfc = row.get('RFC', '').strip()
                print(rfc)
                if rfc and rfc in rfcs_validos:
                    print(rfc)
                    nombre = row.get('Nombre del Contribuyente', '').strip()
                    situacion = row.get('Situación del contribuyente', '').strip()
                    nombre = nombre[:255]
                    situacion = situacion[:255]
                    if rfc not in all_records:
                        all_records[rfc] = {'nombre': nombre, 'situacion': situacion}
        logs.append(f"📊 RFCs a insertar: {len(all_records)}")
        print(all_records)
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

        # Obtener fecha de publicación desde el primer CSV
        fecha_publicacion = None
        if urls:
            logs.append(f"📥 Obteniendo fecha de publicación desde {urls[0]}...")
            try:
                import requests
                response = requests.get(urls[0], timeout=30)
                response.raise_for_status()
                csv_content = response.content.decode('utf-8', errors='replace')
                fecha_publicacion = extraer_fecha_desde_csv(csv_content)
                print('entro')
                print(fecha_publicacion)
                if fecha_publicacion:
                    logs.append(f"📅 Fecha publicación extraída: {fecha_publicacion}")
                else:
                    logs.append("⚠️ No se pudo extraer fecha, usando fecha actual")
                    fecha_publicacion = datetime.now().date()
            except Exception as e:
                print('error')
                logs.append(f"❌ Error obteniendo fecha: {str(e)}")
                fecha_publicacion = datetime.now().date()
        
        # Obtener RFCs válidos de la empresa
        rfcs_validos = obtener_rfcs_existentes(db_name)
        logs.append(f"🔍 RFCs válidos en la empresa: {len(rfcs_validos)}")
        
        all_records = {}
        for url in urls:
            logs.append(f"📥 Descargando {url}...")
            rows = descargar_csv_por_indice(url)
            logs.append(f"   {len(rows)} registros.")
            
            # Las columnas según estructura del CSV:
            # Índice 1: RFC
            # Índice 2: Nombre del Contribuyente
            # Índice 3: Situación del contribuyente
            for row in rows:
                if len(row) < 4:
                    continue
                rfc = row[1].strip().upper()
                if rfc and rfc in rfcs_validos:
                    nombre = row[2].strip()[:255] if len(row) > 2 else ''
                    situacion = row[3].strip()[:255] if len(row) > 3 else ''
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


# ========== REPSE ==========
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os

TIPOS_REPSE = [
    ('AR', 'Autorización REPSE'),
    ('CPI', 'Comprobantes Pago IMSS'),
    ('CL', 'Contratos Laborales'),
    ('CDCM', 'Cédulas Cuotas / Mensual'),
    ('CDCB', 'Cédulas Cuotas / Bimestral'),
    ('CN', 'CFDI\'s Nómina'),
    ('DPS', 'Declaración y Pagos SAT'),
]

@usuario_required
def repse_lista(request):
    return render(request, 'core/usuario/repse_lista.html')

@usuario_required
def repse_data(request):
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # Obtener todos los RFCs de las cuatro tablas
    entidades = {}
    with connections[db_name].cursor() as cursor:
        for tabla in ['proveedores', 'proveedores_sin_cfdi', 'clientes', 'clientes_sin_cfdi']:
            cursor.execute(f"SELECT RFC, RazonSocial FROM {tabla} WHERE rfc_identy = %s", [rfc_empresa])
            for row in cursor.fetchall():
                rfc = row[0].strip() if row[0] else ''
                razon = row[1].strip() if row[1] else ''
                if rfc and rfc not in entidades:
                    entidades[rfc] = razon

    # Obtener documentos cargados
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT rfc, tipo_documento FROM repse_documentos")
        docs = cursor.fetchall()
    cargados = {}
    for rfc, tipo in docs:
        cargados.setdefault(rfc, set()).add(tipo)

    # Construir JSON
    data = []
    tipos = [t[0] for t in TIPOS_REPSE]
    for rfc, razon in entidades.items():
        fila = {'rfc': rfc, 'razon_social': razon}
        for t in tipos:
            fila[t] = 1 if t in cargados.get(rfc, set()) else 0
        data.append(fila)
    return JsonResponse(data, safe=False)

@usuario_required
@csrf_exempt
def repse_subir(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    rfc = request.POST.get('rfc')
    tipo = request.POST.get('tipo')
    if not rfc or not tipo:
        return JsonResponse({'error': 'Faltan RFC o tipo'}, status=400)

    if 'zip_file' not in request.FILES:
        return JsonResponse({'error': 'No se envió archivo'}, status=400)

    archivo = request.FILES['zip_file']
    if not archivo.name.endswith('.zip'):
        return JsonResponse({'error': 'Solo se aceptan archivos ZIP'}, status=400)

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # Validar que el RFC pertenezca a la empresa
    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM (
                SELECT RFC FROM proveedores WHERE rfc_identy = %s AND RFC = %s
                UNION
                SELECT RFC FROM proveedores_sin_cfdi WHERE rfc_identy = %s AND RFC = %s
                UNION
                SELECT RFC FROM clientes WHERE rfc_identy = %s AND RFC = %s
                UNION
                SELECT RFC FROM clientes_sin_cfdi WHERE rfc_identy = %s AND RFC = %s
            ) AS t
        """, [rfc_empresa, rfc] * 4)
        if cursor.fetchone()[0] == 0:
            return JsonResponse({'error': 'RFC no pertenece a esta empresa'}, status=400)

    # Guardar archivo
    ruta = os.path.join('repse', rfc, tipo)
    nombre_archivo = f"{rfc}_{tipo}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    path = default_storage.save(os.path.join(ruta, nombre_archivo), ContentFile(archivo.read()))

    # Insertar o actualizar en la tabla
    usuario = request.session.get('user_nombre', '')
    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            INSERT INTO repse_documentos (rfc, tipo_documento, archivo_zip, usuario)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                archivo_zip = VALUES(archivo_zip),
                fecha_carga = CURRENT_TIMESTAMP,
                usuario = VALUES(usuario)
        """, [rfc, tipo, path, usuario])

    # Insertar en historial
    usuario = request.session.get('user_nombre', request.session.get('user_email', 'Anónimo'))
    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            INSERT INTO repse_documentos_historial (rfc, tipo_documento, archivo_zip, usuario)
            VALUES (%s, %s, %s, %s)
        """, [rfc, tipo, path, usuario])

    return JsonResponse({'success': True})


from django.http import FileResponse, Http404

def repse_descargar_ultimo(request, rfc, tipo):
    """Descarga el último ZIP subido para un RFC y tipo de documento."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        raise Http404("No se ha identificado la empresa")

    with connections[db_name].cursor() as cursor:
        cursor.execute(
            "SELECT archivo_zip FROM repse_documentos WHERE rfc = %s AND tipo_documento = %s",
            [rfc, tipo]
        )
        row = cursor.fetchone()
        if not row:
            raise Http404("No se encontró el documento solicitado")
        file_path = row[0]

    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    if not os.path.exists(full_path):
        raise Http404("El archivo ya no existe en el servidor")
    return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))


def repse_historial_json(request, rfc, tipo):
    """Retorna JSON con el historial de cargas para un RFC y tipo."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    with connections[db_name].cursor() as cursor:
        cursor.execute("""
            SELECT id, archivo_zip, usuario, fecha_carga
            FROM repse_documentos_historial
            WHERE rfc = %s AND tipo_documento = %s
            ORDER BY fecha_carga DESC
        """, [rfc, tipo])
        rows = cursor.fetchall()

    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'archivo_zip': row[1],
            'usuario': row[2],
            'fecha_carga': row[3].strftime('%d/%m/%Y %H:%M:%S') if row[3] else ''
        })
    return JsonResponse(data, safe=False)


def repse_descargar_historial(request, id_historial):
    """Descarga un archivo específico del historial."""
    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        raise Http404("No se ha identificado la empresa")

    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT archivo_zip FROM repse_documentos_historial WHERE id = %s", [id_historial])
        row = cursor.fetchone()
        if not row:
            raise Http404("Registro no encontrado")
        file_path = row[0]

    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    if not os.path.exists(full_path):
        raise Http404("El archivo ya no existe en el servidor")
    return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))


from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, get_object_or_404
from django.db import connections
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
import hashlib

def validar_token(request, token):
    db_name = request.session.get('empresa_db_name')  # pero el público no tiene sesión
    # Mejor: identificar la empresa a partir del token? 
    # Para simplificar, el token debe contener la empresa o debemos buscarla en todas las BD.
    # Como estamos en multiempresa, el token debe incluir el nombre de la BD o almacenar en relación.
    # Opción más segura: el token tiene un prefijo con el nombre de la BD o el RFC de la empresa.
    # Para este ejemplo, asumiremos que el token se pasa y que la vista buscará la empresa correspondiente.
    return render(request, 'public/opinion_form.html', {'token': token})


def formulario_opinion_publico(request, token):
    # Buscar el token en la tabla central
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            SELECT db_name, rfc_empresa, rfc_contribuyente, tipo
            FROM opinion_tokens_global
            WHERE token = %s AND usado = 0
              AND (fecha_expiracion > NOW() OR fecha_expiracion IS NULL)
        """, [token])
        row = cursor.fetchone()
        if not row:
            return HttpResponseForbidden("Token inválido o expirado")
        db_name, rfc_empresa, rfc_contribuyente, tipo = row

    # Obtener la empresa (necesaria para logo y contexto)
    from apps.empresas.models import Empresa
    empresa = Empresa.objects.using('default').get(rfc=rfc_empresa)

    # Guardar datos en sesión (opcional, para reutilizar funciones existentes)
    request.session['empresa_db_name'] = db_name
    request.session['empresa_rfc'] = rfc_empresa
    request.session['empresa_nombre'] = empresa.nombre

    tabla_map = {
        'proveedor': 'proveedores',
        'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
        'cliente': 'clientes',
        'cliente_sin_cfdi': 'clientes_sin_cfdi'
    }
    tabla = tabla_map.get(tipo)
    if not tabla:
        return HttpResponseForbidden("Tipo de entidad inválido")

    if request.method == 'POST' and request.FILES.get('pdf'):
        archivo = request.FILES['pdf']
        # Validar archivo (extension .pdf)
        if not archivo.name.lower().endswith('.pdf'):
            return JsonResponse({'error': 'Solo se aceptan archivos PDF'}, status=400)
        # Extraer datos del PDF (fecha, resultado) - función ya existente
        from .views import extraer_datos_pdf  # o copia la función extraer_datos_pdf aquí
        try:
            fecha_opinion, resultado = extraer_datos_pdf(archivo)
        except Exception as e:
            return JsonResponse({'error': f'Error al procesar PDF: {str(e)}'}, status=400)

        # Guardar archivo PDF en media/opinion/...
        año = fecha_opinion.year
        mes = fecha_opinion.month
        ruta = os.path.join('opinion', rfc_contribuyente, str(año), f"{mes:02d}")
        nombre_archivo = f"{rfc_contribuyente}_{fecha_opinion.strftime('%Y%m%d')}.pdf"
        archivo.seek(0)
        pdf_path = default_storage.save(os.path.join(ruta, nombre_archivo), ContentFile(archivo.read()))

        with connections[db_name].cursor() as cursor:
            # Insertar en historial
            cursor.execute("""
                INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                VALUES (%s, %s, %s, %s, %s)
            """, [rfc_contribuyente, tipo, pdf_path, resultado, fecha_opinion])
            # Actualizar tabla principal (Estatus, fecha_opinion, opinion=1)
            cursor.execute(f"""
                UPDATE {tabla}
                SET Estatus = %s, fecha_opinion = %s, opinion = 1
                WHERE RFC = %s AND rfc_identy = %s
            """, [resultado, fecha_opinion, rfc_contribuyente, rfc_empresa])
        # Marcar token como usado
        with connections['default'].cursor() as cursor:
            cursor.execute("UPDATE opinion_tokens_global SET usado = 1 WHERE token = %s", [token])
        return JsonResponse({'success': True, 'message': 'Opinión subida correctamente'})

    # GET: mostrar formulario
    return render(request, 'core/public/opinion_form.html', {
        'token': token,
        'rfc': rfc_contribuyente,
        'empresa_nombre': empresa.nombre
    })



from django.shortcuts import render, get_object_or_404
from django.db import connections
from django.http import HttpResponseForbidden, JsonResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from datetime import datetime
import PyPDF2
import re

def formulario_constancia_publico(request, token):
    # Buscar token en tabla central
    with connections['default'].cursor() as cursor:
        cursor.execute("""
            SELECT db_name, rfc_empresa, rfc_contribuyente, tipo
            FROM constancia_tokens_global
            WHERE token = %s AND usado = 0
              AND (fecha_expiracion > NOW() OR fecha_expiracion IS NULL)
        """, [token])
        row = cursor.fetchone()
        if not row:
            return HttpResponseForbidden("Token inválido o expirado")
        db_name, rfc_empresa, rfc_contribuyente, tipo = row

    from apps.empresas.models import Empresa
    empresa = Empresa.objects.using('default').get(rfc=rfc_empresa)

    request.session['empresa_db_name'] = db_name
    request.session['empresa_rfc'] = rfc_empresa
    request.session['empresa_nombre'] = empresa.nombre

    tabla_map = {
        'proveedor': 'proveedores',
        'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
        'cliente': 'clientes',
        'cliente_sin_cfdi': 'clientes_sin_cfdi'
    }
    tabla = tabla_map.get(tipo)
    if not tabla:
        return HttpResponseForbidden("Tipo de entidad inválido")

    if request.method == 'POST' and request.FILES.get('pdf'):
        archivo = request.FILES['pdf']
        # Validar archivo
        if not archivo.name.lower().endswith('.pdf'):
            return JsonResponse({'error': 'Solo se aceptan archivos PDF'}, status=400)
        # Extraer datos de la constancia (rfc y domicilio) - reutilizamos la función existente
        from .views import extraer_datos_constancia  # asegúrate de tenerla
        try:
            datos = extraer_datos_constancia(archivo)
        except Exception as e:
            return JsonResponse({'error': f'Error al procesar PDF: {str(e)}'}, status=400)

        # Guardar PDF
        año = datos['fecha_constancia'].year
        mes = datos['fecha_constancia'].month
        ruta = os.path.join('constancia', rfc_contribuyente, str(año), f"{mes:02d}")
        nombre_archivo = f"{rfc_contribuyente}_{datos['fecha_constancia'].strftime('%Y%m%d')}.pdf"
        archivo.seek(0)
        pdf_path = default_storage.save(os.path.join(ruta, nombre_archivo), ContentFile(archivo.read()))

        # Insertar en historial y actualizar tabla principal
        with connections[db_name].cursor() as cursor:
            cursor.execute("""
                INSERT INTO constancias_historial
                (rfc, tipo, archivo_pdf, fecha_constancia, codigoPostal, calle, noInt, noExt, colonia, estado, municipio, ciudad)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                rfc_contribuyente, tipo, pdf_path, datos['fecha_constancia'],
                datos.get('codigoPostal', ''), datos.get('calle', ''), datos.get('noInt', ''),
                datos.get('noExt', ''), datos.get('colonia', ''), datos.get('estado', ''),
                datos.get('municipio', ''), datos.get('ciudad', '')
            ])
            cursor.execute(f"""
                UPDATE {tabla}
                SET constancia = 1, fecha_constancia = %s,
                    codigoPostal = %s, calle = %s, noInt = %s, noExt = %s,
                    colonia = %s, estado = %s, municipio = %s, ciudad = %s
                WHERE RFC = %s AND rfc_identy = %s
            """, [
                datos['fecha_constancia'], datos.get('codigoPostal', ''), datos.get('calle', ''),
                datos.get('noInt', ''), datos.get('noExt', ''), datos.get('colonia', ''),
                datos.get('estado', ''), datos.get('municipio', ''), datos.get('ciudad', ''),
                rfc_contribuyente, rfc_empresa
            ])

        # Marcar token como usado
        with connections['default'].cursor() as cursor:
            cursor.execute("UPDATE constancia_tokens_global SET usado = 1 WHERE token = %s", [token])

        return JsonResponse({'success': True, 'message': 'Constancia subida correctamente'})

    return render(request, 'core/public/constancia_form.html', {
        'token': token,
        'rfc': rfc_contribuyente,
        'empresa_nombre': empresa.nombre
    })
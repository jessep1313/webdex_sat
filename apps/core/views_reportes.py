import json
from datetime import datetime, date
from django.db import connections
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .decorators import usuario_required

# Mapeo de nombres técnicos a nombres amigables para el usuario
NOMBRES_AMIGABLES = {
    'proveedores': '📄 Proveedores con CFDI',
    'proveedores_sin_cfdi': '📄 Proveedores sin CFDI',
    'clientes': '👥 Clientes con CFDI',
    'clientes_sin_cfdi': '👥 Clientes sin CFDI',
    'cfdi_recibido': '📥 CFDI Recibidos',
    'cfdi_emitidos': '📤 CFDI Emitidos',
    'opiniones_historial': '📋 Historial de Opiniones',
    'constancias_historial': '📋 Historial de Constancias',
    'articulo69': '⚠️ Artículo 69',
    'articulo69b': '⚠️ Artículo 69-B',
    'articulo69bis': '⚠️ Artículo 69-Bis',
    'peticiones_sat': '🔄 Peticiones al SAT',
    'repse_documentos': '📁 Documentos REPSE',
    'repse_documentos_historial': '📁 Historial REPSE',
    'configuracion_correos': '✉️ Configuración de Correos',
    'log_correos': '📧 Log de Correos',
}

@usuario_required
def reporte_adhoc(request):
    """Vista que muestra la interfaz del generador de reportes ad-hoc"""
    return render(request, 'core/usuario/reporte_adhoc.html')

@usuario_required
def reporte_metadata(request):
    """Devuelve tablas y columnas disponibles para la empresa actual (JSON)"""
    db_name = request.session.get('empresa_db_name')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    try:
        with connections[db_name].cursor() as cursor:
            # Obtener tablas (excluyendo tablas del sistema)
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name NOT LIKE 'django_%'
                AND table_name NOT LIKE 'auth_%'
                AND table_name NOT LIKE 'socialaccount_%'
                ORDER BY table_name
            """)
            tables = [row[0] for row in cursor.fetchall()]

            result = {}
            for table_name in tables:
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE() AND table_name = %s
                    ORDER BY ordinal_position
                """, [table_name])
                columns = [
                    {'name': col[0], 'type': col[1], 'nullable': col[2]}
                    for col in cursor.fetchall()
                ]
                # Usar nombre amigable si existe
                nombre_mostrar = NOMBRES_AMIGABLES.get(table_name, table_name)
                result[table_name] = {
                    'comment': nombre_mostrar,
                    'columns': columns
                }
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@usuario_required
@csrf_exempt
def reporte_ejecutar(request):
    """Ejecuta un reporte personalizado basado en la configuración enviada"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    tabla = data.get('tabla')
    campos = data.get('campos', [])
    filtros = data.get('filtros', [])
    group_by = data.get('group_by', [])
    agregaciones = data.get('agregaciones', [])
    orden = data.get('orden', [])
    limite = data.get('limite', 100)
    tipo_grafico = data.get('tipo_grafico', 'table')

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    # Validar que la tabla existe
    columnas_validas = obtener_columnas_tabla(db_name, tabla)
    if columnas_validas is None:
        return JsonResponse({'error': f'La tabla "{tabla}" no existe o no es accesible'}, status=400)

    # Construir SELECT
    select_parts = []
    for campo in campos:
        if campo in columnas_validas:
            select_parts.append(f"`{campo}`")
        else:
            return JsonResponse({'error': f'Campo inválido: {campo}'}, status=400)
    for agg in agregaciones:
        if agg['col'] in columnas_validas and agg['func'].upper() in ('SUM', 'AVG', 'COUNT', 'MIN', 'MAX'):
            select_parts.append(f"{agg['func'].upper()}(`{agg['col']}`) AS `{agg['func']}_{agg['col']}`")
    
    if not select_parts:
        select_parts = ['*']
    
    # Construir WHERE
    where_clauses = []
    params = []
    # Filtro por empresa si la tabla tiene columna rfc_identy
    if 'rfc_identy' in columnas_validas and rfc_empresa:
        where_clauses.append("`rfc_identy` = %s")
        params.append(rfc_empresa)
    
    for f in filtros:
        col = f.get('col')
        op = f.get('op')
        val = f.get('val')
        if not col or not op or val is None:
            continue
        if col not in columnas_validas:
            continue
        if op == 'eq':
            where_clauses.append(f"`{col}` = %s")
            params.append(val)
        elif op == 'neq':
            where_clauses.append(f"`{col}` != %s")
            params.append(val)
        elif op == 'contains':
            where_clauses.append(f"`{col}` LIKE %s")
            params.append(f"%{val}%")
        elif op == 'startswith':
            where_clauses.append(f"`{col}` LIKE %s")
            params.append(f"{val}%")
        elif op == 'gt':
            where_clauses.append(f"`{col}` > %s")
            params.append(val)
        elif op == 'lt':
            where_clauses.append(f"`{col}` < %s")
            params.append(val)
        elif op == 'between':
            if isinstance(val, list) and len(val) == 2:
                where_clauses.append(f"`{col}` BETWEEN %s AND %s")
                params.extend([val[0], val[1]])
    
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    # GROUP BY
    group_sql = ""
    if group_by:
        group_cols = [f"`{g}`" for g in group_by if g in columnas_validas]
        if group_cols:
            group_sql = "GROUP BY " + ", ".join(group_cols)
    
    # ORDER BY
    order_sql = ""
    if orden:
        order_parts = []
        for o in orden:
            if 'col' in o and o['col'] in columnas_validas:
                direction = o.get('dir', 'ASC').upper()
                order_parts.append(f"`{o['col']}` {direction}")
        if order_parts:
            order_sql = "ORDER BY " + ", ".join(order_parts)
    
    # Consulta final
    query = f"""
        SELECT {', '.join(select_parts)}
        FROM `{tabla}`
        WHERE {where_sql}
        {group_sql}
        {order_sql}
        LIMIT %s
    """
    params.append(limite)
    
    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
        return JsonResponse({
            'success': True,
            'columns': col_names,
            'data': [list(row) for row in rows],
            'grafico': tipo_grafico
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def obtener_columnas_tabla(db_name, tabla):
    """Retorna un set de nombres de columnas válidas para la tabla, o None si no existe"""
    try:
        with connections[db_name].cursor() as cursor:
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE() AND table_name = %s
            """, [tabla])
            columns = {row[0] for row in cursor.fetchall()}
            return columns if columns else None
    except Exception:
        return None



from django.db import connections
from django.http import JsonResponse
from .decorators import usuario_required
import json
from datetime import date

@usuario_required
def reportes_data(request):
    """Devuelve datos para los reportes predefinidos (CFDI mensual, top proveedores, etc.)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        reporte = data.get('reporte')
        filtros = data.get('filtros', {})
    else:
        reporte = request.GET.get('reporte')
        filtros = {
            'fecha_inicio': request.GET.get('fecha_inicio'),
            'fecha_fin': request.GET.get('fecha_fin'),
            'rfc': request.GET.get('rfc'),
        }

    db_name = request.session.get('empresa_db_name')
    rfc_empresa = request.session.get('empresa_rfc')
    if not db_name or not rfc_empresa:
        return JsonResponse({'error': 'No se ha identificado la empresa'}, status=400)

    if reporte == 'cfdi_mensual':
        return _reporte_cfdi_mensual(db_name, rfc_empresa, filtros)
    elif reporte == 'top_proveedores':
        return _reporte_top_proveedores(db_name, rfc_empresa, filtros)
    elif reporte == 'opiniones_status':
        return _reporte_opiniones_status(db_name, rfc_empresa, filtros)
    elif reporte == 'proveedores_listas_negras':
        return _reporte_proveedores_listas_negras(db_name, rfc_empresa, filtros)
    elif reporte == 'constancias_domicilio':
        return _reporte_constancias_domicilio(db_name, rfc_empresa, filtros)
    else:
        return JsonResponse({'error': 'Tipo de reporte no válido'}, status=400)

def _reporte_cfdi_mensual(db_name, rfc_empresa, filtros):
    fecha_inicio = filtros.get('fecha_inicio')
    fecha_fin = filtros.get('fecha_fin')
    params = [rfc_empresa]
    where = ""
    if fecha_inicio:
        where += " AND fecha_comprobante >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        where += " AND fecha_comprobante <= %s"
        params.append(fecha_fin)

    with connections[db_name].cursor() as cursor:
        cursor.execute(f"""
            SELECT DATE_FORMAT(fecha_comprobante, '%%Y-%%m') as mes,
                   COUNT(*) as cant_rec,
                   SUM(CAST(total AS DECIMAL(18,2))) as monto_rec
            FROM cfdi_recibido
            WHERE rfc_receptor = %s {where}
            GROUP BY mes ORDER BY mes
        """, params)
        recibidos = {row[0]: {'cantidad': row[1], 'monto': float(row[2])} for row in cursor.fetchall()}
        cursor.execute(f"""
            SELECT DATE_FORMAT(fecha_comprobante, '%%Y-%%m') as mes,
                   COUNT(*) as cant_emi,
                   SUM(CAST(total AS DECIMAL(18,2))) as monto_emi
            FROM cfdi_emitidos
            WHERE rfc_emisor = %s {where}
            GROUP BY mes ORDER BY mes
        """, params)
        emitidos = {row[0]: {'cantidad': row[1], 'monto': float(row[2])} for row in cursor.fetchall()}

    meses = sorted(set(recibidos.keys()) | set(emitidos.keys()))
    data = []
    for mes in meses:
        data.append({
            'mes': mes,
            'recibidos_cantidad': recibidos.get(mes, {}).get('cantidad', 0),
            'recibidos_monto': recibidos.get(mes, {}).get('monto', 0),
            'emitidos_cantidad': emitidos.get(mes, {}).get('cantidad', 0),
            'emitidos_monto': emitidos.get(mes, {}).get('monto', 0),
        })
    return JsonResponse({'data': data})

def _reporte_top_proveedores(db_name, rfc_empresa, filtros):
    fecha_inicio = filtros.get('fecha_inicio')
    fecha_fin = filtros.get('fecha_fin')
    params = [rfc_empresa]
    where = ""
    if fecha_inicio:
        where += " AND fecha_comprobante >= %s"
        params.append(fecha_inicio)
    if fecha_fin:
        where += " AND fecha_comprobante <= %s"
        params.append(fecha_fin)

    with connections[db_name].cursor() as cursor:
        # Consulta principal: agrupar por RFC emisor
        cursor.execute(f"""
            SELECT rfc_emisor,
                   COUNT(*) as total_facturas,
                   SUM(CAST(total AS DECIMAL(18,2))) as monto_total
            FROM cfdi_recibido
            WHERE rfc_receptor = %s {where}
            GROUP BY rfc_emisor
            ORDER BY monto_total DESC
            LIMIT 10
        """, params)
        rows = cursor.fetchall()

    data = []
    for r in rows:
        rfc = r[0]
        # Intentar obtener el nombre comercial desde la tabla proveedores
        nombre = rfc  # fallback: mostrar el RFC
        try:
            cursor.execute("""
                SELECT RazonSocial FROM proveedores
                WHERE RFC = %s AND rfc_identy = %s
            """, [rfc, rfc_empresa])
            row_nombre = cursor.fetchone()
            if row_nombre and row_nombre[0]:
                nombre = row_nombre[0]
        except:
            pass
        data.append({
            'rfc': rfc,
            'nombre': nombre,
            'total_facturas': r[1],
            'monto_total': float(r[2])
        })
    return JsonResponse({'data': data})

def _reporte_opiniones_status(db_name, rfc_empresa, filtros):
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT Estatus, COUNT(*) FROM proveedores WHERE rfc_identy = %s GROUP BY Estatus", [rfc_empresa])
        prov = dict(cursor.fetchall())
        cursor.execute("SELECT Estatus, COUNT(*) FROM proveedores_sin_cfdi WHERE rfc_identy = %s GROUP BY Estatus", [rfc_empresa])
        prov_sin = dict(cursor.fetchall())
        cursor.execute("SELECT Estatus, COUNT(*) FROM clientes WHERE rfc_identy = %s GROUP BY Estatus", [rfc_empresa])
        cli = dict(cursor.fetchall())
        cursor.execute("SELECT Estatus, COUNT(*) FROM clientes_sin_cfdi WHERE rfc_identy = %s GROUP BY Estatus", [rfc_empresa])
        cli_sin = dict(cursor.fetchall())
    categorias = ['Positivo', 'Negativo', 'SinRespuesta']
    data = []
    for cat in categorias:
        data.append({
            'estatus': cat,
            'proveedores': prov.get(cat, 0),
            'proveedores_sin_cfdi': prov_sin.get(cat, 0),
            'clientes': cli.get(cat, 0),
            'clientes_sin_cfdi': cli_sin.get(cat, 0),
            'total': prov.get(cat,0)+prov_sin.get(cat,0)+cli.get(cat,0)+cli_sin.get(cat,0)
        })
    return JsonResponse({'data': data})

def _reporte_proveedores_listas_negras(db_name, rfc_empresa, filtros):
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT RFC, RazonSocial FROM proveedores WHERE rfc_identy = %s", [rfc_empresa])
        proveedores = {r[0]: r[1] for r in cursor.fetchall()}
        cursor.execute("SELECT RFC, RazonSocial FROM proveedores_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
        for r in cursor.fetchall():
            proveedores[r[0]] = r[1]

        cursor.execute("SELECT rfc, tipo_supuesto FROM articulo69")
        a69 = dict(cursor.fetchall())
        cursor.execute("SELECT rfc, tipo_supuesto FROM articulo69b")
        a69b = dict(cursor.fetchall())
        cursor.execute("SELECT rfc, tipo_supuesto FROM articulo69bis")
        a69bis = dict(cursor.fetchall())

    data = []
    for rfc, nombre in proveedores.items():
        tipos = []
        if rfc in a69:
            tipos.append(f"69: {a69[rfc]}")
        if rfc in a69b:
            tipos.append(f"69-B: {a69b[rfc]}")
        if rfc in a69bis:
            tipos.append(f"69-Bis: {a69bis[rfc]}")
        if tipos:
            data.append({'rfc': rfc, 'nombre': nombre, 'tipo': ', '.join(tipos)})
    return JsonResponse({'data': data})

def _reporte_constancias_domicilio(db_name, rfc_empresa, filtros):
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT RFC, RazonSocial, constancia, CASE WHEN calle IS NOT NULL AND calle != '' THEN 1 ELSE 0 END as dom FROM proveedores WHERE rfc_identy = %s", [rfc_empresa])
        rows = [{'rfc': r[0], 'nombre': r[1], 'tipo': 'Proveedor', 'constancia': r[2], 'domicilio': r[3]} for r in cursor.fetchall()]
        cursor.execute("SELECT RFC, RazonSocial, constancia, CASE WHEN calle IS NOT NULL AND calle != '' THEN 1 ELSE 0 END FROM proveedores_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
        rows += [{'rfc': r[0], 'nombre': r[1], 'tipo': 'Proveedor sin CFDI', 'constancia': r[2], 'domicilio': r[3]} for r in cursor.fetchall()]
        cursor.execute("SELECT RFC, RazonSocial, constancia, CASE WHEN calle IS NOT NULL AND calle != '' THEN 1 ELSE 0 END FROM clientes WHERE rfc_identy = %s", [rfc_empresa])
        rows += [{'rfc': r[0], 'nombre': r[1], 'tipo': 'Cliente', 'constancia': r[2], 'domicilio': r[3]} for r in cursor.fetchall()]
        cursor.execute("SELECT RFC, RazonSocial, constancia, CASE WHEN calle IS NOT NULL AND calle != '' THEN 1 ELSE 0 END FROM clientes_sin_cfdi WHERE rfc_identy = %s", [rfc_empresa])
        rows += [{'rfc': r[0], 'nombre': r[1], 'tipo': 'Cliente sin CFDI', 'constancia': r[2], 'domicilio': r[3]} for r in cursor.fetchall()]
    return JsonResponse({'data': rows})
import os
import tempfile
import zipfile
import glob
import base64
import xml.etree.ElementTree as ET
import shutil
from datetime import datetime, date

from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
from django.core.signing import loads
from django.apps import apps

from satcfdi.models import Signer
from satcfdi.pacs.sat import SAT, EstadoSolicitud

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

# ========== Funciones auxiliares (sin cambios) ==========
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
        'uso_cfdi': (receptor.get('UsoCFDI', '') if (receptor := root.find('cfdi:Receptor', ns)) else ''),
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

# ========== Lógica principal para una empresa ==========
def procesar_peticiones_empresa(empresa_nombre, db_name, rfc_empresa):
    EFirma = apps.get_model('empresas', 'EFirma')
    logs = []
    total_descargas = 0
    total_procesados = 0

    try:
        efirma = EFirma.objects.using('default').get(empresa=empresa_nombre, estatus='validado')
    except EFirma.DoesNotExist:
        logs.append(f"❌ Empresa {empresa_nombre} no tiene FIEL válida")
        return {'logs': logs, 'descargas': 0, 'procesados': 0}

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

    # 1. Descarga
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

    # 2. Procesamiento XML
    for id_peticion, fechainicio in peticiones_procesar:
        logs.append(f"Procesando XML de petición {id_peticion}...")
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
            if zips:
                with connections[db_name].cursor() as cursor_upd:
                    cursor_upd.execute("UPDATE peticiones_sat SET cargadoxml = 1 WHERE idpeticion = %s", [id_peticion])
                logs.append("  Petición marcada como procesada (XML cargados).")
                total_procesados += 1
        except Exception as e:
            logs.append(f"  Error procesando petición {id_peticion}: {str(e)}")

    return {'logs': logs, 'descargas': total_descargas, 'procesados': total_procesados}

class Command(BaseCommand):
    help = 'Automatiza la descarga y procesamiento de CFDI recibidos para empresas activas'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', type=str, help='Procesar solo una empresa (nombre exacto)')

    def handle(self, *args, **options):
        Empresa = apps.get_model('empresas', 'Empresa')
        empresa_filter = options.get('empresa')
        empresas = Empresa.objects.using('default').filter(activo=True)
        if empresa_filter:
            empresas = empresas.filter(nombre=empresa_filter)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("No se encontraron empresas activas."))
            return

        for empresa in empresas:
            self.stdout.write(f"\n--- Procesando empresa: {empresa.nombre} (RFC: {empresa.rfc}) ---")
            resultado = procesar_peticiones_empresa(empresa.nombre, empresa.db_name, empresa.rfc)
            for log in resultado['logs']:
                self.stdout.write(log)
            self.stdout.write(f"Descargas: {resultado['descargas']}, XML procesados: {resultado['procesados']}")

        self.stdout.write(self.style.SUCCESS("Proceso completado"))
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import connections
from django.conf import settings
from django.apps import apps
import uuid

# Misma función obtener_opinion_sat, pero adaptada para no depender de request
def obtener_opinion_sat(rfc, download_dir, logs):
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

class Command(BaseCommand):
    help = 'Obtiene opiniones de cumplimiento del SAT para todos los RFC de clientes/proveedores de cada empresa, con pausa entre RFCs.'

    def add_arguments(self, parser):
        parser.add_argument('--empresa', type=str, help='Procesar solo una empresa (nombre exacto)')
        parser.add_argument('--pausa', type=int, default=10, help='Segundos de espera entre cada RFC (default 10)')
        parser.add_argument('--tipo', type=str, choices=['proveedor', 'cliente', 'todos'], default='todos',
                            help='Tipo de entidades a procesar: proveedor, cliente, todos')

    def handle(self, *args, **options):
        Empresa = apps.get_model('empresas', 'Empresa')
        pausa = options['pausa']
        tipo_filtro = options['tipo']
        empresa_nombre = options.get('empresa')

        empresas = Empresa.objects.using('default').filter(activo=True)
        if empresa_nombre:
            empresas = empresas.filter(nombre=empresa_nombre)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("No se encontraron empresas activas."))
            return

        for empresa in empresas:
            self.stdout.write(f"\n--- Procesando empresa: {empresa.nombre} (RFC: {empresa.rfc}, DB: {empresa.db_name}) ---")
            db_name = empresa.db_name
            rfc_empresa = empresa.rfc

            # Obtener lista de RFCs de las cuatro tablas según tipo_filtro
            rfc_list = []  # cada elemento: (rfc, razon_social, tipo_entidad, tabla)
            tablas = []
            if tipo_filtro in ['proveedor', 'todos']:
                tablas.append(('proveedores', 'proveedor'))
                tablas.append(('proveedores_sin_cfdi', 'proveedor_sin_cfdi'))
            if tipo_filtro in ['cliente', 'todos']:
                tablas.append(('clientes', 'cliente'))
                tablas.append(('clientes_sin_cfdi', 'cliente_sin_cfdi'))

            for tabla, tipo_entidad in tablas:
                try:
                    with connections[db_name].cursor() as cursor:
                        cursor.execute(f"SELECT RFC, RazonSocial FROM {tabla} WHERE rfc_identy = %s", [rfc_empresa])
                        for row in cursor.fetchall():
                            rfc = row[0].strip()
                            razon = row[1].strip() if row[1] else ''
                            if rfc:
                                rfc_list.append((rfc, razon, tipo_entidad, tabla))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error consultando {tabla}: {str(e)}"))

            self.stdout.write(f"Total RFCs a procesar: {len(rfc_list)}")
            total_procesados = 0
            exitos = 0
            fallos = 0

            for idx, (rfc, razon_social, tipo_entidad, tabla) in enumerate(rfc_list, 1):
                self.stdout.write(f"\n[{idx}/{len(rfc_list)}] Procesando {tipo_entidad}: {rfc} - {razon_social}")
                logs = []
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_opinions', rfc)
                os.makedirs(temp_dir, exist_ok=True)

                resultado = obtener_opinion_sat(rfc, temp_dir, logs)
                for log in logs:
                    self.stdout.write(f"  {log}")

                if resultado is None:
                    self.stdout.write(self.style.ERROR(f"  ❌ Falló la consulta para {rfc}"))
                    fallos += 1
                    # Registrar en historial como error? Podríamos, pero mejor no.
                    # Limpiar directorio temporal
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    # Pausa antes del siguiente
                    if idx < len(rfc_list):
                        self.stdout.write(f"  Esperando {pausa} segundos...")
                        time.sleep(pausa)
                    continue

                # Guardar resultado en la base de datos de la empresa
                try:
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
                            self.stdout.write(f"  📁 PDF guardado en: {destino}")

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
                            exitos += 1
                            self.stdout.write(self.style.SUCCESS(f"  ✅ {rfc} actualizado con PDF ({resultado['resultado']})"))
                            # Eliminar archivo temporal
                            os.remove(resultado['pdf_path'])
                        else:
                            fecha_actual = resultado['fecha']
                            sql = f"""
                                UPDATE {tabla}
                                SET Estatus = %s, fecha_opinion = %s, opinion = 0
                                WHERE RFC = %s AND rfc_identy = %s
                            """
                            cursor.execute(sql, [resultado['status'], fecha_actual, rfc, rfc_empresa])
                            cursor.execute("""
                                INSERT INTO opiniones_historial (rfc, tipo, archivo_pdf, resultado, fecha_opinion)
                                VALUES (%s, %s, %s, %s, %s)
                            """, [rfc, tipo_entidad, '', resultado['status'], fecha_actual])
                            exitos += 1
                            self.stdout.write(self.style.SUCCESS(f"  ✅ {rfc} actualizado sin PDF (estatus: {resultado['status']})"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Error al guardar en BD: {str(e)}"))
                    fallos += 1
                finally:
                    # Limpiar directorio temporal
                    shutil.rmtree(temp_dir, ignore_errors=True)

                total_procesados += 1
                # Pausa entre RFCs excepto después del último
                if idx < len(rfc_list):
                    self.stdout.write(f"  Esperando {pausa} segundos antes del siguiente RFC...")
                    time.sleep(pausa)

            self.stdout.write(f"\n--- Resumen para {empresa.nombre}: {total_procesados} procesados, {exitos} exitosos, {fallos} fallos ---")

        self.stdout.write(self.style.SUCCESS("\n🎉 Proceso completado para todas las empresas."))
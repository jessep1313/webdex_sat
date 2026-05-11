import os
import smtplib
import secrets
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections
from django.apps import apps
from django.core.files.storage import default_storage

class Command(BaseCommand):
    help = "Envía correos masivos para solicitar opiniones de cumplimiento"

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=str,
            help='Enviar solo para una empresa específica (nombre exacto)'
        )
        parser.add_argument(
            '--tipo',
            type=str,
            choices=['proveedor', 'proveedor_sin_cfdi', 'cliente', 'cliente_sin_cfdi', 'todos'],
            default='todos',
            help='Tipo de entidad a procesar'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular envío sin enviar realmente los correos'
        )

    def handle(self, *args, **options):
        empresa_nombre = options.get('empresa')
        tipo_filtro = options.get('tipo')
        dry_run = options.get('dry_run')

        # Obtener modelo Empresa
        Empresa = apps.get_model('empresas', 'Empresa')
        empresas = Empresa.objects.using('default').filter(activo=True)
        if empresa_nombre:
            empresas = empresas.filter(nombre=empresa_nombre)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("No se encontraron empresas activas."))
            return

        for empresa in empresas:
            self.stdout.write(f"Procesando empresa: {empresa.nombre} (RFC: {empresa.rfc})")
            db_name = empresa.db_name
            if not db_name:
                self.stdout.write(self.style.WARNING(f"  Empresa sin db_name, omitiendo."))
                continue

            config = self.obtener_config_envio(db_name)
            if not config:
                self.stdout.write(self.style.WARNING(f"  No hay configuración de envío de correo para {empresa.nombre}. Omitiendo."))
                continue

            plantillas = self.obtener_plantillas(db_name)
            if not plantillas:
                self.stdout.write(self.style.WARNING(f"  No hay plantillas de correo configuradas para {empresa.nombre}."))
                continue

            tipos_entidad = ['proveedor', 'proveedor_sin_cfdi', 'cliente', 'cliente_sin_cfdi']
            if tipo_filtro != 'todos':
                if tipo_filtro not in tipos_entidad:
                    self.stdout.write(self.style.ERROR(f"Tipo inválido: {tipo_filtro}"))
                    return
                tipos_entidad = [tipo_filtro]

            total_enviados = 0
            total_fallos = 0

            for tipo in tipos_entidad:
                self.stdout.write(f"  Procesando tipo: {tipo}")
                destinatarios = self.obtener_destinatarios(db_name, empresa.rfc, tipo)
                if not destinatarios:
                    self.stdout.write(f"    No hay destinatarios para {tipo}.")
                    continue

                plantilla = plantillas.get(tipo)
                if not plantilla:
                    self.stdout.write(self.style.WARNING(f"    No hay plantilla para tipo {tipo}. Se usará plantilla genérica."))
                    plantilla = {
                        'titulo': 'Solicitud de opinión de cumplimiento',
                        'cuerpo': """Estimado(a) {{ nombre }} (RFC: {{ rfc }}):

Le informamos que su opinión de cumplimiento se encuentra disponible en nuestro sistema.

Para cargarla, haga clic en el siguiente enlace (válido por 30 días):
{{ link }}

Atentamente,
Su equipo de atención."""
                    }

                for dest in destinatarios:
                    token = secrets.token_hex(32)
                    ok = self.guardar_token_central(token, db_name, empresa.rfc, dest['rfc'], tipo)
                    if not ok:
                        self.stdout.write(self.style.ERROR(f"    Error al guardar token para {dest['rfc']}. Omitiendo."))
                        total_fallos += 1
                        continue

                    # Construir enlace absoluto
                    dominio = getattr(settings, 'DOMAIN', '127.0.0.1:8000')
                    link = f"http://{dominio}/opinion/{token}/" if '127.0.0.1' in dominio else f"https://{dominio}/opinion/{token}/"
                    cuerpo_html = self.render_plantilla(plantilla['cuerpo'], dest, link)
                    titulo = plantilla['titulo']

                    if dry_run:
                        self.stdout.write(f"    [DRY RUN] Enviando a {dest['email']} (RFC: {dest['rfc']})")
                        total_enviados += 1
                    else:
                        exito = self.enviar_correo(config, dest['email'], titulo, cuerpo_html, dest['nombre'], db_name, empresa.rfc)
                        if exito:
                            total_enviados += 1
                            self.stdout.write(f"    Correo enviado a {dest['email']}")
                        else:
                            total_fallos += 1
                            self.stdout.write(self.style.ERROR(f"    Falló envío a {dest['email']}"))

            self.stdout.write(self.style.SUCCESS(f"  Resumen empresa {empresa.nombre}: enviados={total_enviados}, fallos={total_fallos}"))

    # ------------------------- Métodos auxiliares -------------------------
    def obtener_config_envio(self, db_name):
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT * FROM configuracion_envio_correo LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            columns = [col[0] for col in cursor.description]
            return dict(zip(columns, row))

    def obtener_plantillas(self, db_name):
        plantillas = {}
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT tipo, titulo, cuerpo FROM configuracion_correos")
            for row in cursor.fetchall():
                plantillas[row[0]] = {'titulo': row[1], 'cuerpo': row[2]}
        return plantillas

    def obtener_destinatarios(self, db_name, rfc_empresa, tipo):
        tabla_map = {
            'proveedor': 'proveedores',
            'proveedor_sin_cfdi': 'proveedores_sin_cfdi',
            'cliente': 'clientes',
            'cliente_sin_cfdi': 'clientes_sin_cfdi'
        }
        tabla = tabla_map[tipo]
        query = f"""
            SELECT RFC, RazonSocial, Correo
            FROM {tabla}
            WHERE rfc_identy = %s
              AND Correo IS NOT NULL AND Correo != ''
              AND (opinion = 0 OR opinion IS NULL)
        """
        with connections[db_name].cursor() as cursor:
            cursor.execute(query, [rfc_empresa])
            rows = cursor.fetchall()
        return [{'rfc': r[0], 'nombre': r[1], 'email': r[2]} for r in rows]

    def guardar_token_central(self, token, db_name, rfc_empresa, rfc_contribuyente, tipo):
        expiracion = datetime.now() + timedelta(days=30)
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    INSERT INTO opinion_tokens_global
                    (token, db_name, rfc_empresa, rfc_contribuyente, tipo, usado, fecha_creacion, fecha_expiracion)
                    VALUES (%s, %s, %s, %s, %s, 0, NOW(), %s)
                """, [token, db_name, rfc_empresa, rfc_contribuyente, tipo, expiracion])
            return True
        except Exception as e:
            self.stderr.write(f"Error guardando token: {e}")
            return False

    def render_plantilla(self, plantilla, dest, link):
        cuerpo = plantilla.replace('{{ nombre }}', dest['nombre'])
        cuerpo = cuerpo.replace('{{ rfc }}', dest['rfc'])
        cuerpo = cuerpo.replace('{{ link }}', link)
        return cuerpo.replace('\n', '<br>')

    def enviar_correo(self, config, to_email, subject, body_html, nombre_destino, db_name, rfc_empresa):
        proveedor = config.get('proveedor')
        logo_path = config.get('logo')
        logo_full_path = None
        if logo_path:
            logo_full_path = os.path.join(settings.MEDIA_ROOT, logo_path) if settings.MEDIA_ROOT else None

        html_full = f"""<html>
<head><meta charset="UTF-8"></head>
<body>
    {f'<img src="cid:logo" alt="Logo empresa" style="max-width:200px;"><br>' if logo_full_path and os.path.exists(logo_full_path) else ''}
    {body_html}
</body>
</html>"""

        if proveedor in ('smtp', 'gmail'):
            return self.enviar_via_smtp(config, to_email, subject, html_full, logo_full_path)
        elif proveedor == 'sendgrid':
            return self.enviar_via_sendgrid(config, to_email, subject, html_full, logo_path)
        else:
            self.stderr.write(f"Proveedor no soportado: {proveedor}")
            return False

    def enviar_via_smtp(self, config, to_email, subject, html_content, logo_path):
        host = config.get('host')
        port = config.get('puerto')
        username = config.get('usuario')
        password = config.get('password')
        use_tls = config.get('use_tls', False)
        use_ssl = config.get('use_ssl', False)
        from_email = username

        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)
            if use_tls:
                server.starttls()
            server.login(username, password)
        except Exception as e:
            self.stderr.write(f"Error conectando SMTP: {e}")
            return False

        msg = MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg.attach(MIMEText(html_content, 'html'))

        if logo_path and os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                img = MIMEImage(f.read())
                img.add_header('Content-ID', '<logo>')
                img.add_header('Content-Disposition', 'inline', filename='logo.png')
                msg.attach(img)

        try:
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()
            return True
        except Exception as e:
            self.stderr.write(f"Error enviando mensaje: {e}")
            return False

    def enviar_via_sendgrid(self, config, to_email, subject, html_content, logo_url):
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail, Email, To, Content
        except ImportError:
            self.stderr.write("SendGrid no instalado. Ejecute: pip install sendgrid")
            return False

        api_key = config.get('api_key')
        if not api_key:
            self.stderr.write("Falta API Key de SendGrid")
            return False

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        from_email = Email("no-reply@tudominio.com")  # Cambiar por un remitente verificado
        to_email_obj = To(to_email)
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email_obj, subject, content)
        try:
            response = sg.send(mail)
            return response.status_code in (200, 202)
        except Exception as e:
            self.stderr.write(f"Error SendGrid: {e}")
            return False
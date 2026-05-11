import os
import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connections
from django.core.files.storage import default_storage

class Command(BaseCommand):
    help = "Envía correos masivos para solicitar opiniones de cumplimiento"

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa',
            type=str,
            help='Procesar solo una empresa (nombre exacto)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular envío sin enviar realmente los correos'
        )
        parser.add_argument(
            '--limite',
            type=int,
            default=0,
            help='Número máximo de correos a enviar por empresa (0 = sin límite)'
        )

    def handle(self, *args, **options):
        empresa_nombre = options.get('empresa')
        dry_run = options.get('dry_run')
        limite = options.get('limite', 0)

        # Obtener empresas activas desde la base central usando get_model
        from django.apps import apps
        Empresa = apps.get_model('empresas', 'Empresa')
        empresas = Empresa.objects.using('default').filter(activo=True)
        if empresa_nombre:
            empresas = empresas.filter(nombre=empresa_nombre)

        if not empresas.exists():
            self.stdout.write(self.style.WARNING("No se encontraron empresas activas."))
            return

        for empresa in empresas:
            self.stdout.write(f"\n--- Procesando empresa: {empresa.nombre} (RFC: {empresa.rfc}) ---")
            db_name = empresa.db_name
            if not db_name:
                self.stdout.write(self.style.WARNING("  Empresa sin db_name, omitiendo."))
                continue

            # 1. Obtener configuración de envío de correo
            config_envio = self.obtener_config_envio(db_name)
            if not config_envio:
                self.stdout.write(self.style.WARNING("  No hay configuración de envío de correo. Omitiendo."))
                continue

            # 2. Obtener plantilla de correo para opinión
            plantilla = self.obtener_plantilla_opinion(db_name)
            if not plantilla:
                self.stdout.write(self.style.WARNING("  No hay plantilla de correo para 'opinión de cumplimiento'. Omitiendo."))
                continue

            # 3. Obtener destinatarios (proveedores y clientes que aún no han dado opinión)
            destinatarios = self.obtener_destinatarios(db_name, empresa.rfc)
            if not destinatarios:
                self.stdout.write("  No hay destinatarios pendientes de opinión.")
                continue

            if limite > 0:
                destinatarios = destinatarios[:limite]

            total_enviados = 0
            total_fallos = 0

            for idx, dest in enumerate(destinatarios, 1):
                self.stdout.write(f"  [{idx}/{len(destinatarios)}] Procesando {dest['email']} (RFC: {dest['rfc']})")
                # Generar token único
                token = secrets.token_hex(32)
                # Guardar token en tabla central
                if not self.guardar_token_central(token, db_name, empresa.rfc, dest['rfc'], dest['tipo_entidad']):
                    self.stdout.write(self.style.ERROR("    Error al guardar token, omitiendo"))
                    total_fallos += 1
                    continue

                # Construir enlace
                dominio = getattr(settings, 'DOMAIN', 'localhost:8000')
                link = f"http://{dominio}/opinion/{token}/"
                # Reemplazar variables en el cuerpo
                cuerpo_html = self.renderizar_cuerpo(plantilla['cuerpo'], dest['nombre'], dest['rfc'], link)

                if dry_run:
                    self.stdout.write(f"    [DRY RUN] Enviando a {dest['email']}")
                    total_enviados += 1
                else:
                    exito = self.enviar_correo(config_envio, dest['email'], plantilla['titulo'], cuerpo_html, dest['nombre'], db_name)
                    if exito:
                        total_enviados += 1
                        self.stdout.write(f"    ✓ Correo enviado")
                    else:
                        total_fallos += 1
                        self.stdout.write(self.style.ERROR(f"    ✗ Falló envío"))

            self.stdout.write(self.style.SUCCESS(f"  Resumen: enviados={total_enviados}, fallos={total_fallos}"))

    # ========== MÉTODOS AUXILIARES ==========

    def obtener_config_envio(self, db_name):
        """Retorna dict con la configuración de envío (proveedor, credenciales, logo). None si no existe."""
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT * FROM configuracion_envio_correo LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            columns = [col[0] for col in cursor.description]
            config = dict(zip(columns, row))
            return config

    def obtener_plantilla_opinion(self, db_name):
        """Retorna dict con titulo y cuerpo de la plantilla de opinión, o None si no existe."""
        with connections[db_name].cursor() as cursor:
            cursor.execute("SELECT titulo, cuerpo FROM configuracion_correos WHERE tipo = 'opinion'")
            row = cursor.fetchone()
            if not row:
                return None
            return {'titulo': row[0], 'cuerpo': row[1]}

    def obtener_destinatarios(self, db_name, rfc_empresa):
        """
        Retorna lista de dicts con rfc, nombre, email y tipo_entidad
        para aquellos que tengan Correo no vacío y opinion = 0 (o NULL).
        """
        tablas = [
            ('proveedores', 'proveedor'),
            ('proveedores_sin_cfdi', 'proveedor_sin_cfdi'),
            ('clientes', 'cliente'),
            ('clientes_sin_cfdi', 'cliente_sin_cfdi')
        ]
        destinatarios = []
        with connections[db_name].cursor() as cursor:
            for tabla, tipo in tablas:
                cursor.execute(f"""
                    SELECT RFC, RazonSocial, Correo
                    FROM {tabla}
                    WHERE rfc_identy = %s
                      AND Correo IS NOT NULL AND Correo != ''
                      AND (opinion = 0 OR opinion IS NULL)
                """, [rfc_empresa])
                for row in cursor.fetchall():
                    destinatarios.append({
                        'rfc': row[0],
                        'nombre': row[1],
                        'email': row[2],
                        'tipo_entidad': tipo
                    })
        return destinatarios

    def guardar_token_central(self, token, db_name, rfc_empresa, rfc_contribuyente, tipo_entidad):
        """Inserta token en la tabla central opinion_tokens_global."""
        expiracion = datetime.now() + timedelta(days=30)
        try:
            with connections['default'].cursor() as cursor:
                cursor.execute("""
                    INSERT INTO opinion_tokens_global
                    (token, db_name, rfc_empresa, rfc_contribuyente, tipo, usado, fecha_creacion, fecha_expiracion)
                    VALUES (%s, %s, %s, %s, %s, 0, NOW(), %s)
                """, [token, db_name, rfc_empresa, rfc_contribuyente, tipo_entidad, expiracion])
            return True
        except Exception as e:
            self.stderr.write(f"Error DB: {e}")
            return False

    def renderizar_cuerpo(self, plantilla_cuerpo, nombre, rfc, link):
        """Reemplaza {{ nombre }}, {{ rfc }}, {{ link }} en el cuerpo."""
        cuerpo = plantilla_cuerpo.replace('{{ nombre }}', nombre)
        cuerpo = cuerpo.replace('{{ rfc }}', rfc)
        cuerpo = cuerpo.replace('{{ link }}', link)
        # Convertir saltos de línea a <br> para HTML
        return cuerpo.replace('\n', '<br>')

    def enviar_correo(self, config, to_email, subject, body_html, nombre_destino, db_name):
        """Envía correo según el proveedor configurado."""
        proveedor = config.get('proveedor')
        logo_path = config.get('logo')
        logo_full_path = None
        if logo_path:
            logo_full_path = os.path.join(settings.MEDIA_ROOT, logo_path)

        # Construir HTML completo con logo embebido (para SMTP) o con URL (SendGrid)
        html_with_logo = body_html
        if logo_full_path and os.path.exists(logo_full_path):
            if proveedor == 'sendgrid':
                # Para SendGrid usamos URL pública
                logo_url = f"{settings.MEDIA_URL}{logo_path}" if settings.MEDIA_URL else f"/media/{logo_path}"
                html_with_logo = f'<img src="{logo_url}" alt="Logo" style="max-width:200px;"><br>' + body_html
            else:
                # Para SMTP usaremos adjunto con cid
                html_with_logo = f'<img src="cid:logo" alt="Logo" style="max-width:200px;"><br>' + body_html

        if proveedor in ('smtp', 'gmail'):
            return self.enviar_via_smtp(config, to_email, subject, html_with_logo, logo_full_path)
        elif proveedor == 'sendgrid':
            return self.enviar_via_sendgrid(config, to_email, subject, html_with_logo)
        else:
            self.stderr.write(f"Proveedor no soportado: {proveedor}")
            return False

    def enviar_via_smtp(self, config, to_email, subject, html_content, logo_path=None):
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

        # Adjuntar parte HTML
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Adjuntar logo como imagen embebida si existe
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

    def enviar_via_sendgrid(self, config, to_email, subject, html_content):
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
        from_email = Email("no-reply@tudominio.com")  # Debe estar verificado en SendGrid
        to_email_obj = To(to_email)
        content = Content("text/html", html_content)
        mail = Mail(from_email, to_email_obj, subject, content)

        try:
            response = sg.send(mail)
            return response.status_code in (200, 202)
        except Exception as e:
            self.stderr.write(f"Error SendGrid: {e}")
            return False
from django.db import connections

def crear_tablas_empresa(db_name):
    """
    Crea todas las tablas operativas en la base de datos de una empresa.
    """
    sql_tables = """
-- Tabla proveedores
CREATE TABLE IF NOT EXISTS proveedores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipoProveedor VARCHAR(255) NULL,
    Contacto VARCHAR(255) NULL,
    Planta VARCHAR(255) NULL,
    Correo VARCHAR(255) NULL,
    Correo2 VARCHAR(255) NULL,
    Correo3 VARCHAR(255) NULL,
    RFC VARCHAR(255) NULL,
    RazonSocial VARCHAR(255) NULL,
    nombre VARCHAR(255) NULL,
    apellidoPaterno VARCHAR(255) NULL,
    apellidoMaterno VARCHAR(255) NULL,
    Nombrecomercial VARCHAR(255) NULL,
    tipoPersona VARCHAR(255) NULL,
    codigoPostal VARCHAR(255) NULL,
    calle VARCHAR(255) NULL,
    noInt VARCHAR(255) NULL,
    noExt VARCHAR(255) NULL,
    colonia VARCHAR(255) NULL,
    estado VARCHAR(255) NULL,
    municipio VARCHAR(255) NULL,
    ciudad VARCHAR(255) NULL,
    telefono VARCHAR(255) NULL,
    opinion INT DEFAULT 0,
    fecha_opinion DATE NULL,
    constancia INT DEFAULT 0,
    fecha_constancia DATE NULL,
    rfc_identy VARCHAR(255) NULL,
    Estatus VARCHAR(255) NULL

);

-- Tabla cfdi_recibido
CREATE TABLE IF NOT EXISTS cfdi_recibido (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rfc_emisor VARCHAR(255) NOT NULL,
    rfc_receptor VARCHAR(255) NOT NULL,
    folio VARCHAR(255) NULL,
    uuid VARCHAR(255) NOT NULL,
    fecha_comprobante DATE NOT NULL,
    total VARCHAR(255) NOT NULL,
    iva VARCHAR(255) NULL,
    suma VARCHAR(255) NULL,
    status_sat VARCHAR(255) NOT NULL,
    moneda VARCHAR(100) NULL,
    situacion_interna_externa VARCHAR(100) NULL,
    complemento_pago VARCHAR(100) NULL,
    forma_pago VARCHAR(100) NULL,
    metodo_pago VARCHAR(100) NULL,
    fecha_cancelacion VARCHAR(100) NULL,
    tipo_cambio VARCHAR(100) NULL,
    fecha_timbrado VARCHAR(100) NULL,
    estado_factura VARCHAR(100) NULL,
    saldo_pendiente VARCHAR(100) NULL
);

-- Tabla proveedores_historico
CREATE TABLE IF NOT EXISTS proveedores_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipoProveedor VARCHAR(255) NULL,
    Contacto VARCHAR(255) NULL,
    Planta VARCHAR(255) NULL,
    Correo VARCHAR(255) NULL,
    Correo2 VARCHAR(255) NULL,
    Correo3 VARCHAR(255) NULL,
    RFC VARCHAR(255) NULL,
    RazonSocial VARCHAR(255) NULL,
    nombre VARCHAR(255) NULL,
    apellidoPaterno VARCHAR(255) NULL,
    apellidoMaterno VARCHAR(255) NULL,
    Nombrecomercial VARCHAR(255) NULL,
    tipoPersona VARCHAR(255) NULL,
    codigoPostal VARCHAR(255) NULL,
    calle VARCHAR(255) NULL,
    noInt VARCHAR(255) NULL,
    noExt VARCHAR(255) NULL,
    colonia VARCHAR(255) NULL,
    estado VARCHAR(255) NULL,
    municipio VARCHAR(255) NULL,
    ciudad VARCHAR(255) NULL,
    telefono VARCHAR(255) NULL,
    opinion INT DEFAULT 0,
    fecha_opinion DATE NULL,
    constancia INT DEFAULT 0,
    fecha_constancia DATE NULL,
    rfc_identy VARCHAR(255) NULL,
    Estatus VARCHAR(255) NULL

);

-- Tabla proveedores_sin_cfdi
CREATE TABLE IF NOT EXISTS proveedores_sin_cfdi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipoProveedor VARCHAR(255) NULL,
    Contacto VARCHAR(255) NULL,
    Planta VARCHAR(255) NULL,
    Correo VARCHAR(255) NULL,
    Correo2 VARCHAR(255) NULL,
    Correo3 VARCHAR(255) NULL,
    RFC VARCHAR(255) NULL,
    RazonSocial VARCHAR(255) NULL,
    nombre VARCHAR(255) NULL,
    apellidoPaterno VARCHAR(255) NULL,
    apellidoMaterno VARCHAR(255) NULL,
    Nombrecomercial VARCHAR(255) NULL,
    tipoPersona VARCHAR(255) NULL,
    codigoPostal VARCHAR(255) NULL,
    calle VARCHAR(255) NULL,
    noInt VARCHAR(255) NULL,
    noExt VARCHAR(255) NULL,
    colonia VARCHAR(255) NULL,
    estado VARCHAR(255) NULL,
    municipio VARCHAR(255) NULL,
    ciudad VARCHAR(255) NULL,
    telefono VARCHAR(255) NULL,
    opinion INT DEFAULT 0,
    fecha_opinion DATE NULL,
    constancia INT DEFAULT 0,
    fecha_constancia DATE NULL,
    rfc_identy VARCHAR(255) NULL,
    Estatus VARCHAR(255) NULL
);


-- Tabla clientes_sin_cfdi
CREATE TABLE IF NOT EXISTS clientes_sin_cfdi (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipoProveedor VARCHAR(255) NULL,
    Contacto VARCHAR(255) NULL,
    Planta VARCHAR(255) NULL,
    Correo VARCHAR(255) NULL,
    Correo2 VARCHAR(255) NULL,
    Correo3 VARCHAR(255) NULL,
    RFC VARCHAR(255) NULL,
    RazonSocial VARCHAR(255) NULL,
    nombre VARCHAR(255) NULL,
    apellidoPaterno VARCHAR(255) NULL,
    apellidoMaterno VARCHAR(255) NULL,
    Nombrecomercial VARCHAR(255) NULL,
    tipoPersona VARCHAR(255) NULL,
    codigoPostal VARCHAR(255) NULL,
    calle VARCHAR(255) NULL,
    noInt VARCHAR(255) NULL,
    noExt VARCHAR(255) NULL,
    colonia VARCHAR(255) NULL,
    estado VARCHAR(255) NULL,
    municipio VARCHAR(255) NULL,
    ciudad VARCHAR(255) NULL,
    telefono VARCHAR(255) NULL,
    opinion INT DEFAULT 0,
    fecha_opinion DATE NULL,
    constancia INT DEFAULT 0,
    fecha_constancia DATE NULL,
    rfc_identy VARCHAR(255) NULL,
    Estatus VARCHAR(255) NULL
);

-- Tabla configuracion_correos
CREATE TABLE IF NOT EXISTS configuracion_correos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipo VARCHAR(100) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    cuerpo TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla peticiones_sat
CREATE TABLE IF NOT EXISTS peticiones_sat (
    id INT AUTO_INCREMENT PRIMARY KEY,
    idpeticion VARCHAR(255) NULL,
    estatuspeticion INT NOT NULL,
    fechainicio DATE NOT NULL,
    fechafinal DATE NOT NULL,
    rfc VARCHAR(100) NOT NULL,
    CodEstatus VARCHAR(100) NULL,
    Mensaje VARCHAR(255) NULL,
    RfcSolicitante VARCHAR(100) NOT NULL,
    cargadoxml INT NOT NULL DEFAULT 0,
    tipo VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    idusuario_central INT NULL
);

-- Tabla clientes
CREATE TABLE IF NOT EXISTS clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tipoProveedor VARCHAR(255) NULL,
    Contacto VARCHAR(255) NULL,
    Planta VARCHAR(255) NULL,
    Correo VARCHAR(255) NULL,
    Correo2 VARCHAR(255) NULL,
    Correo3 VARCHAR(255) NULL,
    RFC VARCHAR(255) NULL,
    RazonSocial VARCHAR(255) NULL,
    nombre VARCHAR(255) NULL,
    apellidoPaterno VARCHAR(255) NULL,
    apellidoMaterno VARCHAR(255) NULL,
    Nombrecomercial VARCHAR(255) NULL,
    tipoPersona VARCHAR(255) NULL,
    codigoPostal VARCHAR(255) NULL,
    calle VARCHAR(255) NULL,
    noInt VARCHAR(255) NULL,
    noExt VARCHAR(255) NULL,
    colonia VARCHAR(255) NULL,
    estado VARCHAR(255) NULL,
    municipio VARCHAR(255) NULL,
    ciudad VARCHAR(255) NULL,
    telefono VARCHAR(255) NULL,
    opinion INT DEFAULT 0,
    fecha_opinion DATE NULL,
    constancia INT DEFAULT 0,
    fecha_constancia DATE NULL,
    rfc_identy VARCHAR(255) NULL,
    Estatus VARCHAR(255) NULL
);

-- Tabla cfdi_emitidos
CREATE TABLE IF NOT EXISTS cfdi_emitidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rfc_emisor VARCHAR(255) NOT NULL,
    rfc_receptor VARCHAR(255) NOT NULL,
    folio VARCHAR(255) NULL,
    uuid VARCHAR(255) NOT NULL,
    fecha_comprobante DATE NOT NULL,
    total VARCHAR(255) NOT NULL,
    iva VARCHAR(255) NULL,
    suma VARCHAR(255) NULL,
    status_sat VARCHAR(255) NOT NULL,
    moneda VARCHAR(100) NULL,
    situacion_interna_externa VARCHAR(100) NULL,
    complemento_pago VARCHAR(100) NULL,
    forma_pago VARCHAR(100) NULL,
    metodo_pago VARCHAR(100) NULL,
    fecha_cancelacion VARCHAR(100) NULL,
    tipo_cambio VARCHAR(100) NULL,
    fecha_timbrado VARCHAR(100) NULL,
    estado_factura VARCHAR(100) NULL,
    saldo_pendiente VARCHAR(100) NULL
);

-- Tabla articulo69
CREATE TABLE IF NOT EXISTS articulo69 (
    rfc VARCHAR(255) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo_supuesto VARCHAR(100) NOT NULL,
    fecha_validacion DATE NOT NULL,
    fecha_publicacion DATE NOT NULL
);

-- Tabla articulo69b
CREATE TABLE IF NOT EXISTS articulo69b (
    rfc VARCHAR(255) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo_supuesto VARCHAR(100) NOT NULL,
    fecha_validacion DATE NOT NULL,
    fecha_publicacion DATE NOT NULL
);

-- Tabla articulo69bis
CREATE TABLE IF NOT EXISTS articulo69bis (
    rfc VARCHAR(255) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo_supuesto VARCHAR(100) NOT NULL,
    fecha_validacion DATE NOT NULL,
    fecha_publicacion DATE NOT NULL
);

-- Tabla log_correos
CREATE TABLE IF NOT EXISTS log_correos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    correo VARCHAR(100) NOT NULL,
    fecha DATE NOT NULL,
    documento VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS opiniones_historial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rfc VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,  -- 'proveedor', 'cliente', 'proveedor_sin_cfdi', 'cliente_sin_cfdi'
    archivo_pdf VARCHAR(500) NOT NULL,
    resultado VARCHAR(20) NOT NULL,  -- 'Positivo', 'Negativo'
    fecha_opinion DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Tabla constancias_historial
CREATE TABLE IF NOT EXISTS constancias_historial (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rfc VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    archivo_pdf VARCHAR(500) NOT NULL,
    fecha_constancia DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    codigoPostal VARCHAR(255),
    calle VARCHAR(255),
    noInt VARCHAR(255),
    noExt VARCHAR(255),
    colonia VARCHAR(255),
    estado VARCHAR(255),
    municipio VARCHAR(255),
    ciudad VARCHAR(255)
);

"""
    with connections[db_name].cursor() as cursor:
        for statement in sql_tables.split(';'):
            if statement.strip():
                cursor.execute(statement)



import requests
import csv
import re
from datetime import datetime
from io import StringIO
from bs4 import BeautifulSoup

import requests
import csv
import re
from datetime import datetime
from io import StringIO
from bs4 import BeautifulSoup

def obtener_fecha_publicacion_sat(indice):
    """
    Obtiene la fecha de publicación desde la página del SAT.
    indice: 1 para Artículo 69, 2 para 69-B, 3 para 69-Bis.
    """
    url = 'https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html'
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        texto = soup.get_text()
        patron = r'Información actualizada al (\d{1,2}) de (\w+) de (\d{4})'
        matches = re.findall(patron, texto)
        if matches:
            idx = indice - 1 if indice <= len(matches) else 0
            dia, mes_str, anio = matches[idx]
            meses = {
                'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
                'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
            }
            mes = meses.get(mes_str.lower(), 1)
            return datetime(int(anio), mes, int(dia)).date()
    except Exception as e:
        print(f"Error obteniendo fecha: {e}")
    return datetime.now().date()

def descargar_csv(url):
    """Descarga un CSV y devuelve lista de diccionarios."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.content.decode('utf-8', errors='replace')
        reader = csv.DictReader(StringIO(content))
        return list(reader)
    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return []

def obtener_rfcs_existentes(db_name):
    """Devuelve un set con todos los RFCs que existen en las tablas de la empresa."""
    rfcs = set()
    with connections[db_name].cursor() as cursor:
        # Ajusta el nombre de la columna RFC si es diferente (ej. 'RFC')
        for tabla in ['proveedores', 'proveedores_sin_cfdi', 'clientes', 'clientes_sin_cfdi']:
            cursor.execute(f"SELECT RFC FROM {tabla} WHERE rfc_identy = %s", [db_name])
            for row in cursor.fetchall():
                rfcs.add(row[0])
    return rfcs
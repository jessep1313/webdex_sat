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
    rfc VARCHAR(100) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo_supuesto VARCHAR(100) NOT NULL,
    fecha_validacion DATE NOT NULL,
    fecha_publicacion DATE NOT NULL
);

-- Tabla articulo69b
CREATE TABLE IF NOT EXISTS articulo69b (
    rfc VARCHAR(100) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo_supuesto VARCHAR(100) NOT NULL,
    fecha_validacion DATE NOT NULL,
    fecha_publicacion DATE NOT NULL
);

-- Tabla articulo69bis
CREATE TABLE IF NOT EXISTS articulo69bis (
    rfc VARCHAR(100) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
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
"""
    with connections[db_name].cursor() as cursor:
        for statement in sql_tables.split(';'):
            if statement.strip():
                cursor.execute(statement)
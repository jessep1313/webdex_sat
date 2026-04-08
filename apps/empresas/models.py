from django.db import models

# =====================================================
# Tabla: superadmins
# =====================================================
class SuperAdmin(models.Model):
    nombre = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'superadmins'

    def __str__(self):
        return self.nombre

# =====================================================
# Tabla: grupos
# =====================================================
class Grupo(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'grupos'

    def __str__(self):
        return self.nombre

# =====================================================
# Tabla: empresas
# =====================================================
class Empresa(models.Model):
    nombre = models.CharField(max_length=255)
    rfc = models.CharField(max_length=13, unique=True)  # Debe ser único
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True, db_column='grupo_id')
    db_name = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'empresas'

# =====================================================
# Tabla: sucursales
# =====================================================
class Sucursal(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='empresa_id')
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'sucursales'

    def __str__(self):
        return f"{self.nombre} ({self.empresa.nombre})"

# =====================================================
# Tabla: admin (administradores de empresas)
# =====================================================
class Admin(models.Model):
    nombre = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True, db_column='grupo_id')
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, db_column='empresa_id')
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'admin'

    def __str__(self):
        return self.nombre

# =====================================================
# Tabla: usuarios (usuarios normales)
# =====================================================
class UsuarioCentral(models.Model):
    nombre = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    tipo = models.CharField(max_length=50)
    grupo = models.ForeignKey(Grupo, on_delete=models.SET_NULL, null=True, blank=True, db_column='grupo_id')
    empresa = models.ForeignKey(Empresa, on_delete=models.SET_NULL, null=True, blank=True, db_column='empresa_id')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True, blank=True, db_column='sucursal_id')
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'usuarios'

    def __str__(self):
        return self.nombre

# =====================================================
# Tabla: roles_permisos
# =====================================================
class RolPermiso(models.Model):
    rol = models.CharField(max_length=100)
    permiso = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles_permisos'

    def __str__(self):
        return f"{self.rol} - {self.permiso}"

# =====================================================
# Tabla: catalogos_globales
# =====================================================
class CatalogoGlobal(models.Model):
    tipo = models.CharField(max_length=100)
    clave = models.CharField(max_length=100)
    valor = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'catalogos_globales'

    def __str__(self):
        return f"{self.tipo}: {self.clave} = {self.valor}"

# =====================================================
# Tabla: efirmas
# =====================================================
class EFirma(models.Model):
    archivo_cer = models.CharField(max_length=100)
    archivo_key = models.CharField(max_length=100)
    password = models.CharField(max_length=255)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estatus = models.CharField(max_length=20, default='pendiente')
    grupo = models.CharField(max_length=100, blank=True, null=True)
    empresa = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'efirmas'

    def __str__(self):
        return f"EFirma {self.id} - {self.estatus}"

# =====================================================
# Tabla: efirmas_log
# =====================================================
class EFirmaLog(models.Model):
    efirma = models.ForeignKey(EFirma, on_delete=models.CASCADE, db_column='efirma_id')
    accion = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'efirmas_log'

    def __str__(self):
        return f"{self.efirma.id} - {self.accion} - {self.fecha}"

# =====================================================
# Tabla: metadata
# =====================================================
class Metadata(models.Model):
    clave = models.CharField(max_length=100)
    valor = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'metadata'

    def __str__(self):
        return f"{self.clave} = {self.valor}"

# =====================================================
# Tabla: servicios
# =====================================================
class Servicio(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'servicios'

    def __str__(self):
        return self.nombre
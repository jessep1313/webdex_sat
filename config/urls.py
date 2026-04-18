"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from apps.core import views
from apps.core import views as core_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.login_view, name='login'),
    path('dashboard/', core_views.dashboard, name='dashboard'),
    path('logout/', core_views.logout_view, name='logout'),

    # ... rutas existentes (login, dashboard, logout)
    path('grupos/', core_views.grupos_lista, name='grupos_lista'),
    path('grupos/crear/', core_views.grupo_crear, name='grupo_crear'),
    path('grupos/editar/<int:pk>/', core_views.grupo_editar, name='grupo_editar'),
    path('grupos/eliminar/<int:pk>/', core_views.grupo_eliminar, name='grupo_eliminar'),
    # ... otras rutas (empresas, sucursales, etc.)
    path('empresas/', core_views.empresas_lista, name='empresas_lista'),
    path('sucursales/', core_views.sucursales_lista, name='sucursales_lista'),
    path('sucursales/crear/', core_views.sucursal_crear, name='sucursal_crear'),
    path('sucursales/editar/<int:pk>/', core_views.sucursal_editar, name='sucursal_editar'),
    path('sucursales/eliminar/<int:pk>/', core_views.sucursal_eliminar, name='sucursal_eliminar'),
   # Usuarios - Administradores (cambiamos de 'admin/' a 'administradores/')
    path('administradores/', core_views.admin_lista, name='admin_lista'),
    path('administradores/crear/', core_views.admin_crear, name='admin_crear'),
    path('administradores/editar/<int:pk>/', core_views.admin_editar, name='admin_editar'),
    path('administradores/eliminar/<int:pk>/', core_views.admin_eliminar, name='admin_eliminar'),
    path('usuarios/', core_views.usuarios_lista, name='usuarios_lista'),
    path('efirma/', core_views.efirma_lista, name='efirma_lista'),
    # ... otras rutas (login, dashboard, logout, grupos...)
    path('empresas/', core_views.empresas_lista, name='empresas_lista'),
    path('empresas/crear/', core_views.empresa_crear, name='empresa_crear'),
    path('empresas/editar/<int:pk>/', core_views.empresa_editar, name='empresa_editar'),
    path('empresas/eliminar/<int:pk>/', core_views.empresa_eliminar, name='empresa_eliminar'),

    path('usuarios/', core_views.usuarios_lista, name='usuarios_lista'),
    path('usuarios/crear/', core_views.usuario_crear, name='usuario_crear'),
    path('usuarios/editar/<int:pk>/', core_views.usuario_editar, name='usuario_editar'),
    path('usuarios/eliminar/<int:pk>/', core_views.usuario_eliminar, name='usuario_eliminar'),

    path('api/sucursales/', core_views.api_sucursales, name='api_sucursales'),

    path('efirma/', core_views.efirma_lista, name='efirma_lista'),
    path('efirma/crear/', core_views.efirma_crear, name='efirma_crear'),
    path('efirma/validar/<int:pk>/', core_views.efirma_validar, name='efirma_validar'),
    path('efirma/eliminar/<int:pk>/', core_views.efirma_eliminar, name='efirma_eliminar'),

    path('efirma/actualizar-vigencia/<int:pk>/', core_views.efirma_actualizar_vigencia, name='efirma_actualizar_vigencia'),
    path('efirma/log/', core_views.efirma_log_lista, name='efirma_log_lista'),

    # Usuarios normales para administrador
    # ========== RUTAS PARA ADMINISTRADOR (con prefijo seguro) ==========
    path('panel-admin/usuarios/', core_views.admin_usuarios_lista, name='admin_usuarios_lista'),
    path('panel-admin/usuarios/crear/', core_views.admin_usuario_crear, name='admin_usuario_crear'),
    path('panel-admin/usuarios/editar/<int:pk>/', core_views.admin_usuario_editar, name='admin_usuario_editar'),
    path('panel-admin/usuarios/eliminar/<int:pk>/', core_views.admin_usuario_eliminar, name='admin_usuario_eliminar'),
    
    path('panel-admin/efirma/', core_views.admin_efirma_lista, name='admin_efirma_lista'),
    path('panel-admin/efirma/crear/', core_views.admin_efirma_crear, name='admin_efirma_crear'),
    path('panel-admin/efirma/validar/<int:pk>/', core_views.admin_efirma_validar, name='admin_efirma_validar'),
    path('panel-admin/efirma/actualizar-vigencia/<int:pk>/', core_views.admin_efirma_actualizar_vigencia, name='admin_efirma_actualizar_vigencia'),
    path('panel-admin/efirma/eliminar/<int:pk>/', core_views.admin_efirma_eliminar, name='admin_efirma_eliminar'),
    path('panel-admin/efirma/log/', core_views.admin_efirma_log_lista, name='admin_efirma_log_lista'),

    path('panel-admin/correos/', core_views.admin_correos_lista, name='admin_correos_lista'),
    path('panel-admin/correos/crear/', core_views.admin_correo_crear, name='admin_correo_crear'),
    path('panel-admin/correos/editar/<int:pk>/', core_views.admin_correo_editar, name='admin_correo_editar'),
    path('panel-admin/correos/eliminar/<int:pk>/', core_views.admin_correo_eliminar, name='admin_correo_eliminar'),

    # Usuario normal
    path('usuario/dashboard/', core_views.usuario_dashboard, name='usuario_dashboard'),
    path('usuario/peticiones-sat/', core_views.usuario_peticiones_sat, name='usuario_peticiones_sat'),
    path('usuario/recibidas/', core_views.usuario_recibidas, name='usuario_recibidas'),
    path('usuario/emitidas/', core_views.usuario_emitidas, name='usuario_emitidas'),
    path('usuario/revisar-peticiones-emitidas/', core_views.usuario_revisar_peticiones_emitidas, name='usuario_revisar_peticiones_emitidas'),

    # Proveedores (usuario normal)
    path('usuario/proveedores/', core_views.proveedores_lista, name='usuario_proveedores_lista'),
    path('usuario/proveedores/data/', core_views.proveedores_data, name='proveedores_data'),
    path('usuario/proveedores/detalle/<int:pk>/', core_views.proveedor_detalle, name='proveedor_detalle'),
    path('usuario/proveedores/actualizar/<int:pk>/', core_views.proveedor_actualizar, name='proveedor_actualizar'),
    path('usuario/proveedores/exportar/', core_views.proveedores_exportar_plantilla, name='proveedores_exportar'),
    path('usuario/proveedores/importar/', core_views.proveedores_importar, name='proveedores_importar'),

    # Proveedores sin CFDI
    path('usuario/proveedores-sin-cfdi/', core_views.proveedores_sin_cfdi_lista, name='usuario_proveedores_sin_cfdi'),
    path('usuario/proveedores-sin-cfdi/data/', core_views.proveedores_sin_cfdi_data, name='proveedores_sin_cfdi_data'),
    path('usuario/proveedores-sin-cfdi/detalle/<int:pk>/', core_views.proveedor_sin_cfdi_detalle, name='proveedor_sin_cfdi_detalle'),
    path('usuario/proveedores-sin-cfdi/actualizar/<int:pk>/', core_views.proveedor_sin_cfdi_actualizar, name='proveedor_sin_cfdi_actualizar'),
    path('usuario/proveedores-sin-cfdi/crear/', core_views.proveedor_sin_cfdi_crear, name='proveedor_sin_cfdi_crear'),
    path('usuario/proveedores-sin-cfdi/exportar/', core_views.proveedores_sin_cfdi_exportar, name='proveedores_sin_cfdi_exportar'),
    path('usuario/proveedores-sin-cfdi/importar/', core_views.proveedores_sin_cfdi_importar, name='proveedores_sin_cfdi_importar'),

    # Clientes
    path('usuario/clientes/', core_views.clientes_lista, name='usuario_clientes_lista'),
    path('usuario/clientes/data/', core_views.clientes_data, name='clientes_data'),
    path('usuario/clientes/detalle/<int:pk>/', core_views.cliente_detalle, name='cliente_detalle'),
    path('usuario/clientes/actualizar/<int:pk>/', core_views.cliente_actualizar, name='cliente_actualizar'),
    path('usuario/clientes/crear/', core_views.cliente_crear, name='cliente_crear'),
    path('usuario/clientes/exportar/', core_views.clientes_exportar, name='clientes_exportar'),
    path('usuario/clientes/importar/', core_views.clientes_importar, name='clientes_importar'),


    # Clientes sin CFDI
    path('usuario/clientes-sin-cfdi/', core_views.clientes_sin_cfdi_lista, name='usuario_clientes_sin_cfdi'),
    path('usuario/clientes-sin-cfdi/data/', core_views.clientes_sin_cfdi_data, name='clientes_sin_cfdi_data'),
    path('usuario/clientes-sin-cfdi/detalle/<int:pk>/', core_views.cliente_sin_cfdi_detalle, name='cliente_sin_cfdi_detalle'),
    path('usuario/clientes-sin-cfdi/actualizar/<int:pk>/', core_views.cliente_sin_cfdi_actualizar, name='cliente_sin_cfdi_actualizar'),
    path('usuario/clientes-sin-cfdi/crear/', core_views.cliente_sin_cfdi_crear, name='cliente_sin_cfdi_crear'),
    path('usuario/clientes-sin-cfdi/exportar/', core_views.clientes_sin_cfdi_exportar, name='clientes_sin_cfdi_exportar'),
    path('usuario/clientes-sin-cfdi/importar/', core_views.clientes_sin_cfdi_importar, name='clientes_sin_cfdi_importar'),


    # Opiniones de cumplimiento
    path('usuario/opiniones/', core_views.usuario_opiniones, name='usuario_opiniones'),
    path('usuario/opiniones/data/', core_views.usuario_opiniones_data, name='usuario_opiniones_data'),
    path('usuario/opiniones/subir/', core_views.usuario_opiniones_subir, name='usuario_opiniones_subir'),
    path('usuario/opiniones/historial/<str:rfc>/', core_views.usuario_opiniones_historial, name='usuario_opiniones_historial'),
    path('usuario/opiniones/descargar/<str:rfc>/', core_views.usuario_opiniones_descargar_pdf, name='usuario_opiniones_descargar_pdf'),
    path('usuario/opiniones/descargar-historial/<int:id_historial>/', core_views.usuario_opiniones_descargar_historial, name='usuario_opiniones_descargar_historial'),
    path('usuario/opiniones/obtener-sat/', core_views.usuario_opiniones_obtener_sat, name='usuario_opiniones_obtener_sat'),
    path('usuario/opiniones/obtener-sat/status/<str:task_id>/', core_views.usuario_opiniones_obtener_sat_status, name='usuario_opiniones_obtener_sat_status'),

    # Constancias
    path('usuario/constancias/', core_views.usuario_constancias, name='usuario_constancias'),
    path('usuario/constancias/data/', core_views.usuario_constancias_data, name='usuario_constancias_data'),
    path('usuario/constancias/subir/', core_views.usuario_constancias_subir, name='usuario_constancias_subir'),
    path('usuario/constancias/historial/<str:rfc>/', core_views.usuario_constancias_historial, name='usuario_constancias_historial'),
    path('usuario/constancias/descargar/<str:rfc>/', core_views.usuario_constancias_descargar_pdf, name='usuario_constancias_descargar_pdf'),
    path('usuario/constancias/descargar-historial/<int:id_historial>/', core_views.usuario_constancias_descargar_historial, name='usuario_constancias_descargar_historial'),

    # Validación de domicilio
    path('usuario/validacion-domicilio/', core_views.usuario_validacion_domicilio, name='usuario_validacion_domicilio'),
    path('usuario/validacion-domicilio/data/', core_views.usuario_validacion_domicilio_data, name='usuario_validacion_domicilio_data'),

    path('usuario/articulo69/', core_views.usuario_articulo69, name='usuario_articulo69'),
    path('usuario/articulo69b/', core_views.usuario_articulo69b, name='usuario_articulo69b'),
    path('usuario/articulo69bis/', core_views.usuario_articulo69bis, name='usuario_articulo69bis'),


    path('usuario/recibidas/', core_views.usuario_recibidas, name='usuario_recibidas'),
    path('usuario/revisar-peticiones/', core_views.usuario_revisar_peticiones, name='usuario_revisar_peticiones'),


    # Artículo 69
    path('usuario/articulo69/', core_views.usuario_articulo69, name='usuario_articulo69'),
    path('usuario/articulo69/data/', core_views.usuario_articulo69_data, name='usuario_articulo69_data'),
    path('usuario/articulo69/actualizar/', core_views.usuario_articulo69_actualizar, name='usuario_articulo69_actualizar'),
    path('usuario/articulo69/status/<str:task_id>/', core_views.usuario_articulo69_status, name='usuario_articulo69_status'),

    # Artículo 69-B
    path('usuario/articulo69b/', core_views.usuario_articulo69b, name='usuario_articulo69b'),
    path('usuario/articulo69b/data/', core_views.usuario_articulo69b_data, name='usuario_articulo69b_data'),
    path('usuario/articulo69b/actualizar/', core_views.usuario_articulo69b_actualizar, name='usuario_articulo69b_actualizar'),
    path('usuario/articulo69b/status/<str:task_id>/', core_views.usuario_articulo69b_status, name='usuario_articulo69b_status'),

    # Artículo 69-Bis
    path('usuario/articulo69bis/', core_views.usuario_articulo69bis, name='usuario_articulo69bis'),
    path('usuario/articulo69bis/data/', core_views.usuario_articulo69bis_data, name='usuario_articulo69bis_data'),
    path('usuario/articulo69bis/actualizar/', core_views.usuario_articulo69bis_actualizar, name='usuario_articulo69bis_actualizar'),
    path('usuario/articulo69bis/status/<str:task_id>/', core_views.usuario_articulo69bis_status, name='usuario_articulo69bis_status'),



    
    

]

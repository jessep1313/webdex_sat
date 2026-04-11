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


]

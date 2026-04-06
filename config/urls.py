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
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_superadmin, name='dashboard_superadmin'),
    path('logout/', views.logout_view, name='logout'),
    path('grupos/', core_views.grupos_lista, name='grupos_lista'),
    path('empresas/', core_views.empresas_lista, name='empresas_lista'),
    path('sucursales/', core_views.sucursales_lista, name='sucursales_lista'),
    path('admin/', core_views.admin_lista, name='admin_lista'),
    path('usuarios/', core_views.usuarios_lista, name='usuarios_lista'),
    path('efirma/', core_views.efirma_lista, name='efirma_lista'),
]

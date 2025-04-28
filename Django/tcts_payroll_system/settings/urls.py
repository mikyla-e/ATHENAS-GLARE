from .views import AdminEditView, PasswordsChangeView
from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as authentication_views

app_name = 'settings'

urlpatterns = [
    path('', views.settings_view , name='settings'),
    path('admin_edit_profile/', AdminEditView.as_view(), name='admin_edit_profile'),
    path('password/', PasswordsChangeView.as_view(template_name='settings/change_password.html')),
    path('about/', views.about, name='about'),
]
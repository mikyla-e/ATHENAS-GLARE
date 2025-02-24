from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as authentication_views

app_name = 'admin_user'

urlpatterns = [
    path('admin_login', authentication_views.LoginView.as_view(template_name='admin_user/admin_login.html'), name='admin_login'),
]
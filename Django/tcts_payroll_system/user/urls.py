from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as authentication_views

app_name = 'user'

urlpatterns = [
    path('time_in_out/', views.time_in_out, name='time_in_out'),
    path('admin_login/', authentication_views.LoginView.as_view(template_name='user/admin_login.html'), name='admin_login'),
]
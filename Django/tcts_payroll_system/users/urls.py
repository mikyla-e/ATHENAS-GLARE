from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as authentication_views

app_name = 'users'

urlpatterns = [
    path('time_in_out/', views.time_in_out, name='time_in_out'),
    path('admin_login/', authentication_views.LoginView.as_view(template_name='users/admin_login.html'), name='admin_login'),
    path('logout/', authentication_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
]
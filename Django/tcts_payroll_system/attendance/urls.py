from django.contrib import admin
from django.urls import path
from . import views
from django.contrib.auth import views as authentication_views

app_name = 'attendance'

urlpatterns = [
    path('', views.attendance , name='attendance')
]
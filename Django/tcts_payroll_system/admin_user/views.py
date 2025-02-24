from django.shortcuts import render
from .forms import AdminLogin

def admin_login(request):
    form = AdminLogin()
    return render(request, "admin_login.html",  {"form": form })

# Create your views here.

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import AdminEditProfileForm, PasswordChangingForm
from django.urls import reverse_lazy
from django.views import generic

# Create your views here.

@login_required
def settings_view(request):
    return render(request, 'settings/index.html')

@login_required
def about(request):
    return render(request, 'settings/about.html')

class AdminEditView(LoginRequiredMixin, generic.UpdateView):
    form_class = AdminEditProfileForm
    template_name = 'settings/admin_edit_profile.html'
    success_url = reverse_lazy('settings:index')

    def get_object(self):
        return self.request.user
    
class PasswordsChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = PasswordChangingForm
    success_url = reverse_lazy('settings:index')
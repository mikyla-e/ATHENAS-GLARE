from django import forms
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm
from django.contrib.auth.models import User

class AdminEditProfileForm(UserChangeForm):
    username = forms.CharField(max_length=100, label='username', widget=forms.TextInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter username'}))
    first_name = forms.CharField(max_length=100, label='first name', widget=forms.TextInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter First Name'}))
    last_name = forms.CharField(max_length=100, label='last name', widget=forms.TextInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter Last Name'}))
    email = forms.EmailField(label='email', widget=forms.EmailInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter Email'}))
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password')

class PasswordChangingForm(PasswordChangeForm):
    old_password = forms.CharField(max_length=100, label='old password', widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter Old Password'}))
    new_password1 = forms.CharField(max_length=100, label='new password', widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Enter New Password'}))
    new_password2 = forms.CharField(max_length=100, label='confirm password', widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-white px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Confirm New Password'}))
    
    class Meta:
        model = User
        fields = ('old_password', 'new_password1', 'new_password2', )
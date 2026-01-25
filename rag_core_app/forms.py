from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file']

class SignUpForm(UserCreationForm):
    # FIX: Added 'label' to prevent "None" appearing in placeholders
    first_name = forms.CharField(max_length=30, required=False, label="First Name")
    last_name = forms.CharField(max_length=30, required=False, label="Last Name")
    email = forms.EmailField(max_length=254, required=True, label="Email Address")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
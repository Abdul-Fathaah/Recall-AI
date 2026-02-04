from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Document

# --- Helper Mixin to Apply Glass Styles ---
class GlassStyleMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'glass-input'
            field.widget.attrs['placeholder'] = field.label

# --- Forms ---

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file']
    
    def clean_file(self):
        file = self.cleaned_data['file']
        ext = file.name.split('.')[-1].lower()
        if ext not in ['pdf', 'txt', 'docx', 'pptx', 'xlsx', 'csv', 'png', 'jpg', 'jpeg']:
            raise forms.ValidationError("Unsupported file type.")
        return file

class SignUpForm(GlassStyleMixin, UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, label="First Name")
    last_name = forms.CharField(max_length=30, required=False, label="Last Name")
    email = forms.EmailField(max_length=254, required=True, label="Email Address")

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

class UserLoginForm(GlassStyleMixin, AuthenticationForm):
    """Custom Login Form with Glass Styles"""
    pass

class UserUpdateForm(GlassStyleMixin, forms.ModelForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
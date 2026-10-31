from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class SignupForm(UserCreationForm):

    class Meta:
        model = User
        fields = [
            'name',
            'email',
            'phone',
            'company',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data['email'].strip()).lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email
class StaffCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'company']

    def clean_email(self):
        email = self.cleaned_data['email']

        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        user.role = 'staff'
        user.set_password(self.cleaned_data['password1'])

        if commit:
            user.save()

        return user


class ProductOwnerCreationForm(StaffCreationForm):
    class Meta(StaffCreationForm.Meta):
        fields = ['name', 'email', 'phone', 'company']

    def save(self, commit=True):
        user = super(StaffCreationForm, self).save(commit=False)
        user.role = 'product_owner'
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'company']

    def clean_email(self):
        email = self.cleaned_data['email']
        existing = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

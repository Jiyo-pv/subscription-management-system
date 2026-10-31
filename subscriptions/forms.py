from django import forms
from .models import Subscription


class SubscriptionCreateForm(forms.ModelForm):
    """Form for creating a new subscription (admin/staff)."""

    class Meta:
        model = Subscription
        fields = [
            'customer', 'plan', 'start_date', 'expiry_date',
            'payment_terms',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        from catalog.models import Plan
        self.fields['customer'].queryset = User.objects.filter(role='customer')
        self.fields['plan'].queryset = Plan.objects.filter(
            is_active=True,
            product__is_active=True,
            product__approval_status='approved',
        )

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        expiry_date = cleaned_data.get('expiry_date')
        plan = cleaned_data.get('plan')

        if start_date and expiry_date and expiry_date <= start_date:
            raise forms.ValidationError(
                "Expiry date must be after the start date."
            )

        if plan and not plan.is_available:
            raise forms.ValidationError(
                "The selected plan is not currently available."
            )

        return cleaned_data


class SubscriptionEditForm(forms.ModelForm):
    """Form for editing an existing subscription (admin/staff)."""

    class Meta:
        model = Subscription
        fields = [
            'plan', 'start_date', 'expiry_date',
            'payment_terms', 'next_billing_date',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'next_billing_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from catalog.models import Plan
        self.fields['plan'].queryset = Plan.objects.filter(
            is_active=True,
            product__is_active=True,
            product__approval_status='approved',
        )

from django import forms
from .models import Payment


class PaymentForm(forms.Form):
    method = forms.ChoiceField(choices=Payment.METHOD_CHOICES)
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    payment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))

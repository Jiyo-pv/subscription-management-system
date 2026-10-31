from django import forms
from django.utils import timezone


class InvoiceCreateForm(forms.Form):
    due_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=timezone.localdate)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional note shown on the invoice'}))

    def clean_due_date(self):
        due_date = self.cleaned_data['due_date']
        if due_date < timezone.localdate():
            raise forms.ValidationError('The due date cannot be in the past.')
        return due_date

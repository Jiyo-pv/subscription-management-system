from django import forms
from accounts.models import User
from .models import Product, Plan


class ProductForm(forms.ModelForm):
    """Form for creating and editing products."""

    class Meta:
        model = Product
        fields = [
            'name', 'product_type', 'sales_price',
            'cost_price', 'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Cloud Hosting Service'
            }),
            'sales_price': forms.NumberInput(attrs={
                'step': '0.01', 'min': '0', 'placeholder': '0.00'
            }),
            'cost_price': forms.NumberInput(attrs={
                'step': '0.01', 'min': '0', 'placeholder': '0.00'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Product notes or description…'
            }),
        }

    def clean_sales_price(self):
        price = self.cleaned_data.get('sales_price')
        if price is not None and price < 0:
            raise forms.ValidationError("Sales price cannot be negative.")
        return price

    def clean_cost_price(self):
        price = self.cleaned_data.get('cost_price')
        if price is not None and price < 0:
            raise forms.ValidationError("Cost price cannot be negative.")
        return price


class PlanForm(forms.ModelForm):
    """Form for creating and editing plans."""

    class Meta:
        model = Plan
        fields = [
            'name', 'product', 'price', 'billing_period',
            'min_quantity', 'start_date', 'end_date',
            'auto_close', 'is_closable', 'is_pausable',
            'is_renewable', 'is_active', 'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g. Pro Monthly Plan'
            }),
            'price': forms.NumberInput(attrs={
                'step': '0.01', 'min': '0', 'placeholder': '0.00'
            }),
            'min_quantity': forms.NumberInput(attrs={
                'min': '1'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Plan description or features…'
            }),
        }

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)
        products = Product.objects.filter(
            is_active=True,
            approval_status=Product.APPROVAL_APPROVED,
        )
        if owner is not None:
            products = products.filter(owner=owner)
        self.fields['product'].queryset = products
        self.fields['product'].required = True

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price < 0:
            raise forms.ValidationError("Plan price cannot be negative.")
        return price

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError(
                "End date must be after the start date."
            )

        return cleaned_data


class ProductReviewForm(forms.Form):
    owner = forms.ModelChoiceField(
        label='Product Owner',
        queryset=User.objects.filter(role='product_owner'),
        required=False,
        empty_label='Keep current owner',
    )
    feedback = forms.CharField(
        label='Feedback for the Product Owner',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Explain what needs attention.'}),
    )

    def clean(self):
        cleaned = super().clean()
        if self.data.get('action') in ('reject', 'request_changes') and not cleaned.get('feedback', '').strip():
            self.add_error('feedback', 'Feedback is required for rejection or requested changes.')
        return cleaned

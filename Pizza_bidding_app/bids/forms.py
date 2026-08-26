from decimal import Decimal

from django import forms
from django.contrib.auth import password_validation

from .models import Bid


class BidForm(forms.ModelForm):
    class Meta:
        model = Bid
        fields = [
            "subtotal",
            "delivery_fee",
            "tax",
            "discount",
            "notes",
        ]
        widgets = {
            "subtotal": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "delivery_fee": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "tax": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "discount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        subtotal = cleaned_data.get("subtotal") or Decimal("0.00")
        delivery_fee = cleaned_data.get("delivery_fee") or Decimal("0.00")
        tax = cleaned_data.get("tax") or Decimal("0.00")
        discount = cleaned_data.get("discount") or Decimal("0.00")

        total = (
            Decimal(subtotal)
            + Decimal(delivery_fee)
            + Decimal(tax)
            - Decimal(discount)
        )

        if total < Decimal("0.00"):
            raise forms.ValidationError(
                "The discount cannot be greater than the subtotal, "
                "delivery fee, and tax combined."
            )

        cleaned_data["calculated_total"] = total

        return cleaned_data

    def save(self, commit=True):
        obj = super().save(commit=False)

        obj.total = self.cleaned_data["calculated_total"]
        obj.status = "submitted"

        if commit:
            obj.save()

        return obj


class ProviderActivationForm(forms.Form):
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput,
        strip=False,
        help_text="Use a strong password you will not reuse elsewhere.",
    )

    password_confirm = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput,
        strip=False,
    )

    def clean_password(self):
        password = self.cleaned_data["password"]
        password_validation.validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()

        if cleaned.get("password") and cleaned.get("password_confirm"):
            if cleaned["password"] != cleaned["password_confirm"]:
                self.add_error(
                    "password_confirm",
                    "The passwords do not match.",
                )

        return cleaned

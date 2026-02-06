from django import forms


class OTPCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Authenticator code",
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "123456",
            }
        ),
    )


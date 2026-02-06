from django import forms
from django.db import models

from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.widgets import (
    UnfoldAdminEmailInputWidget,
    UnfoldAdminImageFieldWidget,
    UnfoldAdminRadioSelectWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminTextareaWidget,
    UnfoldBooleanSwitchWidget,
)

from .models import Member


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = "__all__"
        widgets = {
            "user": UnfoldAdminSelectWidget(),
            "first_name": UnfoldAdminTextInputWidget(),
            "last_name": UnfoldAdminTextInputWidget(),
            "middle_name": UnfoldAdminTextInputWidget(),
            "email": UnfoldAdminEmailInputWidget(),
            "phone_number": UnfoldAdminTextInputWidget(),
            "date_of_birth": UnfoldAdminTextInputWidget(attrs={"type": "date"}),
            "gender": UnfoldAdminSelectWidget(),
            "marital_status": UnfoldAdminSelectWidget(),
            "address": UnfoldAdminTextareaWidget(),
            "city": UnfoldAdminTextInputWidget(),
            "state": UnfoldAdminTextInputWidget(),
            "country": UnfoldAdminTextInputWidget(),
            "occupation": UnfoldAdminTextInputWidget(),
            "employer": UnfoldAdminTextInputWidget(),
            "membership_status": UnfoldAdminSelectWidget(),
            "membership_date": UnfoldAdminTextInputWidget(attrs={"type": "date"}),
            "baptism_date": UnfoldAdminTextInputWidget(attrs={"type": "date"}),
            "baptism_type": UnfoldAdminSelectWidget(),
            "is_leader": UnfoldBooleanSwitchWidget(),
            "leadership_position": UnfoldAdminTextInputWidget(),
            "emergency_contact_name": UnfoldAdminTextInputWidget(),
            "emergency_contact_phone": UnfoldAdminTextInputWidget(),
            "emergency_contact_relationship": UnfoldAdminTextInputWidget(),
            "photo": UnfoldAdminImageFieldWidget(),
            "notes": UnfoldAdminTextareaWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self._meta.model._meta.fields:
            if isinstance(field, models.TextField) and field.name in self.fields:
                self.fields[field.name].widget = WysiwygWidget()

        # Keep address as a structured postal input instead of rich-text.
        if "address" in self.fields:
            self.fields["address"].widget = UnfoldAdminTextareaWidget(
                attrs={
                    "rows": 3,
                    "placeholder": "Street and house number",
                    "autocomplete": "street-address",
                }
            )
            self.fields["address"].help_text = "Street, number, apartment/suite."

        if "city" in self.fields:
            self.fields["city"].widget = UnfoldAdminTextInputWidget(
                attrs={
                    "placeholder": "City",
                    "autocomplete": "address-level2",
                }
            )

        if "state" in self.fields:
            self.fields["state"].widget = UnfoldAdminTextInputWidget(
                attrs={
                    "placeholder": "State / Region",
                    "autocomplete": "address-level1",
                }
            )

        if "country" in self.fields:
            self.fields["country"].widget = UnfoldAdminTextInputWidget(
                attrs={
                    "placeholder": "Country",
                    "autocomplete": "country-name",
                }
            )

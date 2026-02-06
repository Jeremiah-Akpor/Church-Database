from django import forms
from django.db import models

from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.widgets import (
    UnfoldAdminFileFieldWidget,
    UnfoldAdminImageFieldWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminRadioSelectWidget,
    UnfoldAdminSelect2MultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminURLInputWidget,
    UnfoldBooleanSwitchWidget,
)

from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = "__all__"
        widgets = {
            "title": UnfoldAdminTextInputWidget(),
            "description": UnfoldAdminTextareaWidget(),
            "event_type": UnfoldAdminSelectWidget(),
            "start_date": UnfoldAdminTextInputWidget(attrs={"type": "date"}),
            "end_date": UnfoldAdminTextInputWidget(attrs={"type": "date"}),
            "start_time": UnfoldAdminTextInputWidget(attrs={"type": "time"}),
            "end_time": UnfoldAdminTextInputWidget(attrs={"type": "time"}),
            "location": UnfoldAdminTextInputWidget(),
            "address": UnfoldAdminTextareaWidget(),
            "is_online": UnfoldBooleanSwitchWidget(),
            "online_link": UnfoldAdminURLInputWidget(),
            "expected_attendees": UnfoldAdminIntegerFieldWidget(),
            "is_public": UnfoldBooleanSwitchWidget(),
            "requires_registration": UnfoldBooleanSwitchWidget(),
            "registration_deadline": UnfoldAdminTextInputWidget(
                attrs={"type": "datetime-local"}
            ),
            "is_recurring": UnfoldBooleanSwitchWidget(),
            "recurrence_pattern": UnfoldAdminSelectWidget(),
            "recurrence_weekday": UnfoldAdminSelectWidget(),
            "recurrence_until": UnfoldAdminTextInputWidget(attrs={"type": "date"}),
            "banner_image": UnfoldAdminImageFieldWidget(),
            "attachments": UnfoldAdminFileFieldWidget(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self._meta.model._meta.fields:
            if isinstance(field, models.TextField) and field.name in self.fields:
                self.fields[field.name].widget = WysiwygWidget()
        self.fields["registration_deadline"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ]

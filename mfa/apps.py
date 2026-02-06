from django.apps import AppConfig


class MfaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mfa"

    def ready(self):
        from . import signals  # noqa: F401


from django.conf import settings
from django.contrib.admin.views.decorators import user_passes_test
from django.shortcuts import render


def dashboard_callback(request, context):
    """Return Unfold admin dashboard context unchanged."""
    return context


@user_passes_test(lambda u: u.is_active and u.is_superuser)
def settings_page(request):
    """Read-only runtime settings page for administrators."""
    context = {
        "settings_items": [
            ("Environment", "Development" if settings.DEBUG else "Production"),
            ("Time zone", settings.TIME_ZONE),
            ("MFA issuer", getattr(settings, "MFA_ISSUER", "Church Management System")),
            ("Allowed hosts", ", ".join(settings.ALLOWED_HOSTS)),
            ("CSRF trusted origins", ", ".join(settings.CSRF_TRUSTED_ORIGINS)),
            ("Secure SSL redirect", str(settings.SECURE_SSL_REDIRECT)),
            ("Session cookie secure", str(settings.SESSION_COOKIE_SECURE)),
            ("CSRF cookie secure", str(settings.CSRF_COOKIE_SECURE)),
            ("HSTS seconds", str(settings.SECURE_HSTS_SECONDS)),
        ]
    }
    return render(request, "settings_page.html", context)

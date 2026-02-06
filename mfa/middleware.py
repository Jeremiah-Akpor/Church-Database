from urllib.parse import urlencode

from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .models import UserMFA


class MFAEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_exact_paths = {
            "/admin/password_change/",
        }
        self.exempt_prefixes = (
            "/admin/login/",
            "/admin/logout/",
            "/mfa/",
            "/static/",
            "/media/",
        )

    def __call__(self, request):
        path = request.path

        if request.user.is_authenticated and not any(
            path.startswith(prefix) for prefix in self.exempt_prefixes
        ) and path not in self.exempt_exact_paths:
            mfa_profile, _ = UserMFA.objects.get_or_create(user=request.user)
            next_candidate = request.get_full_path()
            if not url_has_allowed_host_and_scheme(
                url=next_candidate,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                next_candidate = "/admin/"
            query = urlencode({"next": next_candidate})

            # Enforce first-login password change (or any admin-forced reset).
            if mfa_profile.require_password_change:
                if (
                    mfa_profile.password_hash_snapshot
                    and request.user.password != mfa_profile.password_hash_snapshot
                ):
                    mfa_profile.require_password_change = False
                    mfa_profile.password_hash_snapshot = request.user.password
                    mfa_profile.save(
                        update_fields=[
                            "require_password_change",
                            "password_hash_snapshot",
                            "updated_at",
                        ]
                    )
                else:
                    return redirect(f"/admin/password_change/?{query}")

            if not mfa_profile.is_enrolled:
                return redirect(f"/mfa/enroll/?{query}")

            if not request.session.get("mfa_verified", False):
                return redirect(f"/mfa/verify/?{query}")

        return self.get_response(request)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.shortcuts import resolve_url
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
import base64
from io import BytesIO
from urllib.parse import urlencode

from .forms import OTPCodeForm
from .models import UserMFA


def _next_url(request: HttpRequest) -> str:
    candidate = request.GET.get("next") or request.POST.get("next") or "/admin/"
    if url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return resolve_url("/admin/")


def _generate_qr_data_uri(value: str) -> str:
    import qrcode

    img = qrcode.make(value)
    buf = BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


@login_required
def enroll_view(request):
    mfa_profile, _ = UserMFA.objects.get_or_create(user=request.user)
    session_key = "mfa_enroll_secret_user_id"
    if not mfa_profile.is_enrolled:
        if request.session.get(session_key) != request.user.id:
            mfa_profile.rotate_secret()
            request.session[session_key] = request.user.id
    else:
        mfa_profile.ensure_secret()
    next_url = _next_url(request)

    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["code"]
            if mfa_profile.verify_totp(token):
                if not mfa_profile.is_enrolled:
                    mfa_profile.is_enrolled = True
                    mfa_profile.enrolled_at = timezone.now()
                    mfa_profile.save(
                        update_fields=["is_enrolled", "enrolled_at", "updated_at"]
                    )
                request.session["mfa_verified"] = True
                request.session.pop(session_key, None)
                messages.success(request, "MFA enrolled successfully.")
                return redirect(next_url)
            messages.error(request, "Invalid code. Please try again.")
    else:
        form = OTPCodeForm()

    return render(
        request,
        "mfa/enroll.html",
        {
            "form": form,
            "profile": mfa_profile,
            "next": next_url,
            "provisioning_uri": mfa_profile.provisioning_uri(),
            "qr_code_url": _generate_qr_data_uri(mfa_profile.provisioning_uri()),
        },
    )


@login_required
def verify_view(request):
    mfa_profile, _ = UserMFA.objects.get_or_create(user=request.user)
    if not mfa_profile.is_enrolled:
        return redirect(f"/mfa/enroll/?{urlencode({'next': _next_url(request)})}")

    next_url = _next_url(request)
    if request.method == "POST":
        form = OTPCodeForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data["code"]
            if mfa_profile.verify_totp(token):
                request.session["mfa_verified"] = True
                messages.success(request, "MFA verification successful.")
                return redirect(next_url)
            messages.error(request, "Invalid code. Please try again.")
    else:
        form = OTPCodeForm()

    return render(
        request,
        "mfa/verify.html",
        {
            "form": form,
            "next": next_url,
        },
    )

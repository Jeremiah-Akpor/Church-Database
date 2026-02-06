from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserMFA


User = get_user_model()


@receiver(post_save, sender=User)
def bootstrap_user_security_profile(sender, instance, created, **kwargs):
    """Create/initialize security profile for newly created users."""
    if not created:
        return
    profile, _ = UserMFA.objects.get_or_create(user=instance)
    profile.require_password_change = True
    profile.password_hash_snapshot = instance.password or ""
    profile.save(update_fields=["require_password_change", "password_hash_snapshot", "updated_at"])


@receiver(user_logged_in)
def reset_mfa_session_on_login(sender, request, user, **kwargs):
    request.session["mfa_verified"] = False
    request.session.pop("mfa_enroll_secret_user_id", None)


@receiver(user_logged_out)
def clear_mfa_session_on_logout(sender, request, user, **kwargs):
    if request:
        request.session.pop("mfa_verified", None)
        request.session.pop("mfa_enroll_secret_user_id", None)

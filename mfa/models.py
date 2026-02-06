import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone


User = get_user_model()


def _generate_base32_secret(length: int = 20) -> str:
    raw = secrets.token_bytes(length)
    return base64.b32encode(raw).decode("utf-8").rstrip("=")


class UserMFA(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="mfa_profile",
    )
    secret = models.CharField(max_length=64, blank=True)
    is_enrolled = models.BooleanField(default=False)
    require_password_change = models.BooleanField(default=False)
    password_hash_snapshot = models.CharField(max_length=255, blank=True)
    enrolled_at = models.DateTimeField(null=True, blank=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "MFA Profile"
        verbose_name_plural = "MFA Profiles"

    def __str__(self) -> str:
        return f"MFA({self.user})"

    def ensure_secret(self) -> str:
        if not self.secret:
            self.secret = _generate_base32_secret()
            self.save(update_fields=["secret", "updated_at"])
        return self.secret

    def rotate_secret(self) -> str:
        self.secret = _generate_base32_secret()
        self.save(update_fields=["secret", "updated_at"])
        return self.secret

    def provisioning_uri(self) -> str:
        issuer = getattr(settings, "MFA_ISSUER", "Church Management")
        self.ensure_secret()
        label = quote(f"{issuer}:{self.user.username}")
        issuer_q = quote(issuer)
        return f"otpauth://totp/{label}?secret={self.secret}&issuer={issuer_q}"

    def _totp_code_for_counter(self, counter: int, digits: int = 6) -> str:
        key = base64.b32decode(self.secret + "=" * ((8 - len(self.secret) % 8) % 8))
        msg = struct.pack(">Q", counter)
        digest = hmac.new(key, msg, hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(binary % (10**digits)).zfill(digits)

    def verify_totp(self, token: str, valid_window: int = 1) -> bool:
        if not self.secret:
            return False
        token = (token or "").strip()
        if not token.isdigit() or len(token) != 6:
            return False

        interval = 30
        counter = int(time.time() // interval)
        for offset in range(-valid_window, valid_window + 1):
            if self._totp_code_for_counter(counter + offset) == token:
                self.last_verified_at = timezone.now()
                self.save(update_fields=["last_verified_at", "updated_at"])
                return True
        return False

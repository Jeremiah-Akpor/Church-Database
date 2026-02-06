from django.urls import path

from .views import enroll_view, verify_view


app_name = "mfa"

urlpatterns = [
    path("enroll/", enroll_view, name="enroll"),
    path("verify/", verify_view, name="verify"),
]


import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import user_passes_test
from django.core.management import call_command, CommandError
from django.db import connections
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render


def dashboard_callback(request, context):
    """Return Unfold admin dashboard context unchanged."""
    return context


@user_passes_test(lambda u: u.is_active and u.is_superuser)
def settings_page(request):
    """Runtime settings + database backup tools for administrators."""
    backup_dir = Path(settings.BASE_DIR) / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    db = settings.DATABASES["default"]
    engine = db.get("ENGINE", "")
    pg_supported = "postgresql" in engine or "postgis" in engine

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "export_dump":
            if not pg_supported:
                messages.error(request, "Full dump export supports PostgreSQL only.")
                return redirect("settings-page")
            custom_name = request.POST.get("dump_name", "").strip()
            if custom_name:
                filename = (
                    custom_name if custom_name.endswith(".dump") else f"{custom_name}.dump"
                )
            else:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"db_dump_{stamp}.dump"
            output_path = backup_dir / filename
            try:
                command = [
                    "pg_dump",
                    "-h",
                    str(db.get("HOST") or "localhost"),
                    "-p",
                    str(db.get("PORT") or "5432"),
                    "-U",
                    str(db.get("USER") or ""),
                    "-d",
                    str(db.get("NAME") or ""),
                    "-Fc",
                    "-f",
                    str(output_path),
                ]
                env = {**os.environ, "PGPASSWORD": str(db.get("PASSWORD") or "")}
                subprocess.run(command, env=env, check=True, capture_output=True, text=True)
                messages.success(request, f"Backup created: {filename}")
            except FileNotFoundError:
                messages.error(request, "pg_dump is not installed on this host.")
            except subprocess.CalledProcessError as exc:
                err = (exc.stderr or exc.stdout or "Unknown pg_dump error").strip()
                messages.error(request, f"Backup export failed: {err[:700]}")
            return redirect("settings-page")

        if action == "import_dump":
            if not pg_supported:
                messages.error(request, "Full dump import supports PostgreSQL only.")
                return redirect("settings-page")

            confirmed = request.POST.get("confirm_reset", "") == "yes"
            if not confirmed:
                messages.error(
                    request,
                    "You must confirm database reset before importing a dump.",
                )
                return redirect("settings-page")

            upload = request.FILES.get("dump_file")
            if not upload:
                messages.error(request, "Please select a dump file (.dump).")
                return redirect("settings-page")

            filename = Path(upload.name).name
            if not filename.endswith(".dump"):
                messages.error(request, "Only PostgreSQL dump files (.dump) are supported.")
                return redirect("settings-page")

            import_path = backup_dir / filename
            with import_path.open("wb") as fh:
                for chunk in upload.chunks():
                    fh.write(chunk)

            try:
                # Avoid reset_db in web request context: it tries to DROP DATABASE
                # and fails while the app itself still has active connections.
                connections.close_all()
                restore_command = [
                    "pg_restore",
                    "-h",
                    str(db.get("HOST") or "localhost"),
                    "-p",
                    str(db.get("PORT") or "5432"),
                    "-U",
                    str(db.get("USER") or ""),
                    "-d",
                    str(db.get("NAME") or ""),
                    "--clean",
                    "--if-exists",
                    "--no-owner",
                    "--no-privileges",
                    str(import_path),
                ]
                env = {**os.environ, "PGPASSWORD": str(db.get("PASSWORD") or "")}
                subprocess.run(
                    restore_command,
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                call_command("migrate")
                messages.success(
                    request,
                    f"Database reset and restored successfully from: {filename}",
                )
            except FileNotFoundError as exc:
                messages.error(request, f"Required PostgreSQL binary missing: {exc}")
            except (CommandError, subprocess.CalledProcessError) as exc:
                error_msg = (
                    (exc.stderr if hasattr(exc, "stderr") else "")
                    or (exc.stdout if hasattr(exc, "stdout") else "")
                    or str(exc)
                ).strip()
                messages.error(request, f"Import failed: {error_msg[:700]}")
            return redirect("settings-page")

    download_name = request.GET.get("download", "").strip()
    if download_name:
        safe_name = Path(download_name).name
        if safe_name != download_name or not safe_name.endswith(".dump"):
            raise Http404("Invalid backup filename.")
        file_path = backup_dir / safe_name
        if not file_path.exists():
            raise Http404("Backup file not found.")
        return FileResponse(file_path.open("rb"), as_attachment=True, filename=safe_name)

    backups = sorted(
        backup_dir.glob("*.dump"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

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
        ],
        "backup_files": [
            {
                "name": file.name,
                "size_kb": max(1, file.stat().st_size // 1024),
                "modified": datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
            for file in backups
        ],
        "pg_supported": pg_supported,
    }
    return render(request, "settings_page.html", context)

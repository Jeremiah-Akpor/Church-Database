import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a PostgreSQL backup dump in the backup/ folder."

    def add_arguments(self, parser):
        parser.add_argument(
            "--filename",
            default="",
            help="Optional output filename (.dump).",
        )
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Do not prompt for confirmation before dumping.",
        )

    def handle(self, *args, **options):
        db = settings.DATABASES["default"]
        engine = db.get("ENGINE", "")
        if "postgresql" not in engine and "postgis" not in engine:
            raise CommandError(
                "dumpbackup currently supports PostgreSQL databases only."
            )

        if not options["noinput"]:
            confirmed = input(
                "This will create a full PostgreSQL dump. "
                "Restoring this dump will reset current DB data. Continue? [y/N]: "
            ).strip().lower()
            if confirmed not in {"y", "yes"}:
                self.stdout.write(self.style.WARNING("Dump cancelled."))
                return

        backup_dir = Path(settings.BASE_DIR) / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)

        filename = options["filename"].strip()
        if filename:
            if not filename.endswith(".dump"):
                filename = f"{filename}.dump"
        else:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"db_dump_{stamp}.dump"

        output_path = backup_dir / filename

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
        env = os.environ.copy()
        env["PGPASSWORD"] = str(db.get("PASSWORD") or "")

        try:
            subprocess.run(
                command,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise CommandError(
                "pg_dump is not installed or not in PATH."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "Unknown pg_dump error").strip()
            raise CommandError(f"pg_dump failed: {detail}") from exc

        self.stdout.write(self.style.SUCCESS(f"Backup dump created: {output_path}"))

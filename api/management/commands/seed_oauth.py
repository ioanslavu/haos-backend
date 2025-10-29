import os
from typing import List

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

try:
    from allauth.socialaccount.models import SocialApp
except Exception:  # pragma: no cover
    SocialApp = None  # type: ignore


class Command(BaseCommand):
    help = "Seed Sites and Google SocialApp from environment variables. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--domains",
            type=str,
            default=os.environ.get(
                "OAUTH_DOMAINS",
                "haos.dev,haos.baby,api.haos.dev,api.haos.baby",
            ),
            help="Comma-separated list of domains to create Sites for (first is primary)",
        )
        parser.add_argument(
            "--client-id",
            type=str,
            default=(
                os.environ.get("GOOGLE_CLIENT_ID")
                or os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
            ),
            help="Google OAuth client ID (env GOOGLE_CLIENT_ID or GOOGLE_OAUTH_CLIENT_ID)",
        )
        parser.add_argument(
            "--client-secret",
            type=str,
            default=(
                os.environ.get("GOOGLE_CLIENT_SECRET")
                or os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")
            ),
            help="Google OAuth client secret (env GOOGLE_CLIENT_SECRET or GOOGLE_OAUTH_CLIENT_SECRET)",
        )

    def handle(self, *args, **options):
        domains_csv: str = options["domains"] or ""
        domains: List[str] = [d.strip() for d in domains_csv.split(",") if d.strip()]
        client_id: str = options["client_id"]
        client_secret: str = options["client_secret"]

        if not domains:
            self.stdout.write(self.style.WARNING("No domains provided; skipping Sites seeding."))
            return

        if SocialApp is None:
            self.stdout.write(self.style.ERROR("django-allauth not installed; cannot seed SocialApp."))
            return

        if not client_id or not client_secret:
            self.stdout.write(self.style.WARNING("GOOGLE_CLIENT_ID/SECRET not set; seeding Sites only."))

        # Ensure primary site is ID=1 and matches the first domain
        primary = domains[0]
        site1, _ = Site.objects.update_or_create(id=1, defaults={"domain": primary, "name": primary})
        created_sites = [site1]
        for d in domains[1:]:
            s, _ = Site.objects.get_or_create(domain=d, defaults={"name": d})
            created_sites.append(s)

        self.stdout.write(self.style.SUCCESS(f"Ensured Sites for: {', '.join([s.domain for s in created_sites])}"))

        if client_id and client_secret:
            app, _ = SocialApp.objects.get_or_create(provider="google", name="Google OAuth")
            app.client_id = client_id
            app.secret = client_secret
            app.save()
            app.sites.set(created_sites)
            self.stdout.write(self.style.SUCCESS("Google SocialApp configured and linked to Sites."))
        else:
            self.stdout.write(self.style.WARNING("Skipped SocialApp seeding (missing GOOGLE_CLIENT_ID/SECRET)."))


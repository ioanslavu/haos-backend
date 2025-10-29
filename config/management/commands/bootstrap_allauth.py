from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.db import transaction
from django.utils import timezone
import os


class Command(BaseCommand):
    help = (
        "Ensure Sites and Google SocialApp are configured. "
        "Uses SITE_PRIMARY_DOMAIN, SITE_ADDITIONAL_DOMAINS, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET."
    )

    def handle(self, *args, **options):
        primary = os.environ.get("SITE_PRIMARY_DOMAIN")
        additional = os.environ.get("SITE_ADDITIONAL_DOMAINS", "")
        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        domains = []
        if primary:
            domains.append(primary.strip())
        if additional:
            domains.extend([d.strip() for d in additional.split(",") if d.strip()])

        if not domains:
            self.stdout.write(self.style.WARNING(
                "No SITE_PRIMARY_DOMAIN/SITE_ADDITIONAL_DOMAINS provided; skipping Sites setup."
            ))
        else:
            self._ensure_sites(domains, primary)

        if not client_id or not client_secret:
            self.stdout.write(self.style.WARNING(
                "GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET not set; skipping SocialApp setup."
            ))
        else:
            self._ensure_social_app(client_id, client_secret, domains)

    @transaction.atomic
    def _ensure_sites(self, domains, primary):
        # Ensure SITE_ID=1 exists and matches primary if provided
        if primary:
            Site.objects.update_or_create(
                id=1, defaults={"domain": primary, "name": "HaOS API"}
            )
        for d in domains:
            Site.objects.get_or_create(domain=d, defaults={"name": "HaOS"})
        self.stdout.write(self.style.SUCCESS(f"Sites ensured for: {', '.join(domains)}"))

    @transaction.atomic
    def _ensure_social_app(self, client_id, client_secret, domains):
        try:
            from allauth.socialaccount.models import SocialApp
        except Exception:  # pragma: no cover
            self.stdout.write(self.style.ERROR("django-allauth not installed?"))
            return

        app, _created = SocialApp.objects.get_or_create(
            provider="google", defaults={"name": "Google OAuth", "client_id": client_id, "secret": client_secret}
        )
        # Update creds if changed
        changed = False
        if app.client_id != client_id:
            app.client_id = client_id
            changed = True
        if app.secret != client_secret:
            app.secret = client_secret
            changed = True
        if changed:
            app.save(update_fields=["client_id", "secret"])  # type: ignore

        # Link to sites
        site_qs = Site.objects.filter(domain__in=domains)
        if site_qs.exists():
            app.sites.set(list(site_qs))
        self.stdout.write(self.style.SUCCESS(
            f"Google SocialApp linked to sites: {', '.join(site_qs.values_list('domain', flat=True))}"
        ))


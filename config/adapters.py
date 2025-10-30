from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from uuid import uuid4
from allauth.exceptions import ImmediateHttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from decouple import config, Csv
import logging

logger = logging.getLogger(__name__)


def _is_localhost(request) -> bool:
    host = (request.get_host() or '').lower()
    # strip port if present
    host = host.split(':', 1)[0]
    return host in ('localhost', '127.0.0.1')


def _frontend_base_url(request) -> str:
    """Return the correct frontend base URL for redirects.

    - Local dev: use OAUTH_FRONTEND_URL (default http://localhost:5173)
    - Prod: same-origin scheme+host handled by nginx
    """
    if _is_localhost(request):
        return config('OAUTH_FRONTEND_URL', default='http://localhost:5173')
    return f"{request.scheme}://{request.get_host()}"


class RestrictedDomainAdapter(DefaultSocialAccountAdapter):
    """
    Adapter to restrict authentication to specific email domains.
    Only allows users with @hahahaproduction.com email addresses.
    """

    # Allowed domains are configured via env for flexibility.
    # Example: OAUTH_ALLOWED_DOMAINS=example.com,acme.org
    ALLOWED_DOMAINS = config('OAUTH_ALLOWED_DOMAINS', default='', cast=Csv()) or ['hahahaproduction.com']

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """
        Handle authentication errors and redirect to frontend with error message.
        """
        logger.error(f"OAuth authentication error: provider={provider_id}, error={error}, exception={exception}")

        # Compute correct base URL for current environment
        base_url = _frontend_base_url(request)

        error_message = "Authentication failed"
        if error:
            error_message = f"OAuth error: {error}"
        elif exception:
            error_message = f"Authentication error: {str(exception)}"

        error_url = f"{base_url}/auth/error?message={error_message}"
        raise ImmediateHttpResponse(redirect(error_url))

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed.
        """
        email = sociallogin.account.extra_data.get('email', '').lower()
        logger.info(f"Pre-social login: email={email}, provider={sociallogin.account.provider}")

        if not email:
            logger.warning("No email provided by OAuth provider")
            base_url = _frontend_base_url(request)
            error_url = f"{base_url}/auth/error?message=No email address provided"
            raise ImmediateHttpResponse(redirect(error_url))

        domain = email.split('@')[-1]

        if domain not in self.ALLOWED_DOMAINS:
            logger.warning(f"Domain not allowed: {domain}, email: {email}")
            error_message = f"Only @hahahaproduction.com emails allowed. You tried: {email}"
            base_url = _frontend_base_url(request)
            error_url = f"{base_url}/auth/error?message={error_message}"
            raise ImmediateHttpResponse(redirect(error_url))

        logger.info(f"Domain check passed for: {email}")

    # SocialAccountAdapter doesn't control login redirect; AccountAdapter does.
    # Keep this class focused on domain checks and error redirects.


class DynamicRedirectAccountAdapter(DefaultAccountAdapter):
    """
    Ensure redirects go back to the same domain that initiated the flow.
    Returning path-only URLs achieves same-origin redirects.
    """

    def get_login_redirect_url(self, request):
        if _is_localhost(request):
            base_url = _frontend_base_url(request)
            return f"{base_url}/auth/callback"
        return "/auth/callback"

    def get_logout_redirect_url(self, request):
        if _is_localhost(request):
            base_url = _frontend_base_url(request)
            return f"{base_url}/"
        return "/"

    def populate_user(self, request, user, data):
        """
        Ensure a unique username is set for default Django User models
        that still require a unique username field, even when we treat
        username as not required for login.
        """
        user = super().populate_user(request, user, data)
        if hasattr(user, 'username') and not getattr(user, 'username', None):
            base = ''
            email = getattr(user, 'email', '') or data.get('email') or ''
            if email and '@' in email:
                base = email.split('@')[0]
            candidate = base or uuid4().hex[:16]

            User = get_user_model()
            orig = candidate
            i = 0
            while User.objects.filter(username=candidate).exists():
                i += 1
                candidate = f"{orig}-{i}"
            user.username = candidate
        return user

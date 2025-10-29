from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from decouple import config
import logging

logger = logging.getLogger(__name__)


class RestrictedDomainAdapter(DefaultSocialAccountAdapter):
    """
    Adapter to restrict authentication to specific email domains.
    Only allows users with @hahahaproduction.com email addresses.
    """

    ALLOWED_DOMAINS = ['hahahaproduction.com']

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """
        Handle authentication errors and redirect to frontend with error message.
        """
        logger.error(f"OAuth authentication error: provider={provider_id}, error={error}, exception={exception}")

        # Redirect back to the same host the request came from
        base_url = f"{request.scheme}://{request.get_host()}"

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
            base_url = f"{request.scheme}://{request.get_host()}"
            error_url = f"{base_url}/auth/error?message=No email address provided"
            raise ImmediateHttpResponse(redirect(error_url))

        domain = email.split('@')[-1]

        if domain not in self.ALLOWED_DOMAINS:
            logger.warning(f"Domain not allowed: {domain}, email: {email}")
            error_message = f"Only @hahahaproduction.com emails allowed. You tried: {email}"
            base_url = f"{request.scheme}://{request.get_host()}"
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
        return "/auth/callback"

    def get_logout_redirect_url(self, request):
        return "/"

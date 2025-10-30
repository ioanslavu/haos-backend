"""
Middleware for handling user impersonation.
"""
from django.contrib.auth import get_user_model
from django.utils.functional import SimpleLazyObject

User = get_user_model()


class ImpersonationMiddleware:
    """
    Middleware to handle user impersonation.

    If the session contains an '_impersonate' key with a user ID,
    this middleware will replace request.user with that impersonated user.

    This allows admins to test the application as different roles.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store the real user before processing
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check if there's an impersonation in progress
            impersonate_id = request.session.get('_impersonate')

            if impersonate_id:
                try:
                    # Get the impersonated user
                    impersonated_user = User.objects.select_related('profile__role', 'profile__department').get(
                        id=impersonate_id
                    )

                    # Store the real user
                    request._real_user = request.user

                    # Replace request.user with the impersonated user
                    request.user = impersonated_user
                    request._is_impersonating = True

                except User.DoesNotExist:
                    # Invalid impersonation ID, clear it
                    del request.session['_impersonate']
                    request.session.modified = True

        response = self.get_response(request)
        return response

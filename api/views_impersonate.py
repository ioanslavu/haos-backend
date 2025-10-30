"""
API views for user impersonation (role testing).
"""

from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .permissions import IsAdministrator
from .serializers import UserSerializer

User = get_user_model()


class StartImpersonationView(APIView):
    """
    Start impersonating another user for role testing.
    Only administrators can impersonate.
    """
    permission_classes = [IsAuthenticated, IsAdministrator]
    throttle_scope = 'impersonation'

    def post(self, request):
        """
        Start impersonating a user.

        Request body:
            {
                "user_id": 123
            }

        Restrictions:
        - Only admins can use this endpoint
        - Cannot impersonate other admin users
        - Can only impersonate test users (email starts with 'test.')
        """
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the user to impersonate
            impersonate_user = User.objects.select_related('profile__role', 'profile__department').get(id=user_id)

            # Security check: Cannot impersonate admin users
            if hasattr(impersonate_user, 'profile') and impersonate_user.profile.is_admin:
                return Response(
                    {'error': 'Cannot impersonate administrator users. Impersonation is for testing non-admin roles only.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Security check: Can only impersonate test users
            if not impersonate_user.email.startswith('test.'):
                return Response(
                    {'error': 'Can only impersonate test users (email must start with "test.")'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Get the real user (before impersonation)
            real_user = getattr(request, '_real_user', request.user)

            # Store the impersonation in session
            request.session['_impersonate'] = impersonate_user.id
            request.session['_impersonate_real_user'] = real_user.id
            request.session.modified = True

            # Return the impersonated user's data
            serializer = UserSerializer(impersonate_user)

            return Response({
                'success': True,
                'message': f'Now impersonating {impersonate_user.email}',
                'user': serializer.data,
            })

        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StopImpersonationView(APIView):
    """
    Stop impersonating and return to original user.
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'impersonation'

    def post(self, request):
        """
        Stop impersonation and return to real user.
        """
        # Check if currently impersonating
        if '_impersonate' not in request.session:
            return Response(
                {'error': 'Not currently impersonating'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the real user ID
        real_user_id = request.session.get('_impersonate_real_user')

        # Remove impersonation from session
        del request.session['_impersonate']
        if '_impersonate_real_user' in request.session:
            del request.session['_impersonate_real_user']
        request.session.modified = True

        # Get the real user object
        if real_user_id:
            try:
                real_user = User.objects.select_related('profile__role', 'profile__department').get(id=real_user_id)
                serializer = UserSerializer(real_user)
            except User.DoesNotExist:
                # Fallback to current user if real user not found
                serializer = UserSerializer(request.user)
        else:
            # Fallback to current user
            serializer = UserSerializer(request.user)

        return Response({
            'success': True,
            'message': 'Stopped impersonation',
            'user': serializer.data,
        })


class ImpersonationStatusView(APIView):
    """
    Get current impersonation status.
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'impersonation'

    def get(self, request):
        """
        Check if currently impersonating.
        """
        is_impersonating = '_impersonate' in request.session

        response_data = {
            'is_impersonating': is_impersonating,
        }

        if is_impersonating:
            # Get the real user (impersonator)
            # Note: request.user is the impersonated user
            # The real user is stored differently by django-impersonate
            response_data['impersonated_user_id'] = request.session.get('_impersonate')

        return Response(response_data)


class TestUsersListView(APIView):
    """
    List all test users available for impersonation.
    Only returns users with email starting with 'test.'.
    """
    permission_classes = [IsAuthenticated, IsAdministrator]
    throttle_scope = 'impersonation'

    def get(self, request):
        """
        Get list of test users for impersonation dropdown.

        Returns users sorted by role level (managers first, then employees, guest last).
        Excludes administrator users (cannot impersonate admins).
        """
        # Get all test users (those with email starting with 'test.')
        # Exclude administrators (level >= 1000)
        test_users = User.objects.filter(
            email__startswith='test.',
            profile__role__level__lt=1000  # Exclude admin level
        ).select_related('profile__role', 'profile__department').order_by(
            '-profile__role__level',  # Sort by role level descending
            'email'
        )

        # Serialize the users
        users_data = []
        for user in test_users:
            if hasattr(user, 'profile') and user.profile.role:
                # Double-check not admin (in case query didn't filter properly)
                if user.profile.is_admin:
                    continue

                users_data.append({
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'full_name': f"{user.first_name} {user.last_name}".strip() or user.email,
                    'role': {
                        'code': user.profile.role.code,
                        'name': user.profile.role.name,
                        'level': user.profile.role.level,
                    },
                    'department': {
                        'code': user.profile.department.code,
                        'name': user.profile.department.name,
                    } if user.profile.department else None,
                })

        return Response({
            'test_users': users_data,
            'count': len(users_data),
        })

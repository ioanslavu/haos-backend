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
        """
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Get the user to impersonate
            impersonate_user = User.objects.select_related('profile').get(id=user_id)

            # Store the impersonation in session
            # This is what django-impersonate middleware looks for
            request.session['_impersonate'] = impersonate_user.id
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

        # Remove impersonation from session
        del request.session['_impersonate']
        request.session.modified = True

        # Return the real user's data
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

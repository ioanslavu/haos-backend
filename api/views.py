from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, generics
from django.contrib.auth import get_user_model
from .models import CompanySettings, UserProfile, DepartmentRequest, Department, Role
from .serializers import (
    CompanySettingsSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    UserRoleUpdateSerializer,
    DepartmentRequestSerializer,
    DepartmentRequestCreateSerializer,
    DepartmentRequestReviewSerializer,
    DepartmentSerializer,
    RoleSerializer,
)
from .permissions import (
    IsAdministrator,
    IsAdministratorOrManager,
    IsNotGuest,
    HasDepartmentAccess,
)

User = get_user_model()


@ratelimit(key='ip', rate='10/m', method='GET')
@require_http_methods(["GET"])
@ensure_csrf_cookie
def auth_status(request):
    """
    Returns the current authentication status and user info with profile.
    Also sets CSRF cookie for the frontend.
    Rate limited to 10 requests per minute per IP.
    """
    if request.user.is_authenticated:
        # Ensure profile exists
        if not hasattr(request.user, 'profile'):
            from .models import Role
            guest_role = Role.objects.get(code='guest')
            UserProfile.objects.create(user=request.user, role=guest_role)

        profile = request.user.profile

        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'role': profile.role_code,
                'role_detail': {
                    'id': profile.role.id,
                    'code': profile.role.code,
                    'name': profile.role.name,
                    'level': profile.role.level,
                } if profile.role else None,
                'department': profile.department_code,
                'department_detail': {
                    'id': profile.department.id,
                    'code': profile.department.code,
                    'name': profile.department.name,
                } if profile.department else None,
                'profile_picture': request.build_absolute_uri(profile.profile_picture.url) if profile.profile_picture else None,
                'setup_completed': profile.setup_completed,
            },
            'csrf_token': get_token(request)
        })

    return JsonResponse({
        'authenticated': False,
        'user': None,
        'csrf_token': get_token(request)
    })


@ratelimit(key='ip', rate='3/h', method='GET')
@require_http_methods(["GET"])
def oauth_debug(request):
    """
    Debug endpoint to check OAuth configuration.
    Rate limited to 3 requests per hour per IP.
    Only accessible to administrators.
    """
    # Allow only in DEBUG and for staff users. Return 404 to avoid leaking details.
    if not settings.DEBUG or not (request.user.is_authenticated and request.user.is_staff):
        return JsonResponse({'detail': 'Not found'}, status=404)

    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site

    try:
        site = Site.objects.get_current()
        google_app = SocialApp.objects.get(provider='google')

        return JsonResponse({
            'site': {
                'id': site.id,
                'domain': site.domain,
                'name': site.name,
            },
            'google_oauth': {
                'id': google_app.id,
                'name': google_app.name,
                'client_id': google_app.client_id,
                'has_secret': bool(google_app.secret),
                'sites': [s.domain for s in google_app.sites.all()],
            },
            'expected_redirect_uri': f"http://{site.domain}/accounts/google/login/callback/",
            'session_data': {
                'session_key': request.session.session_key,
                'has_session': bool(request.session.session_key),
            }
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


class CompanySettingsView(APIView):
    """
    API endpoint for company settings (singleton).
    GET: Retrieve company settings
    PUT/PATCH: Update company settings
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get company settings."""
        settings = CompanySettings.load()
        serializer = CompanySettingsSerializer(settings)
        return Response(serializer.data)

    def put(self, request):
        """Update company settings (full update)."""
        settings = CompanySettings.load()
        serializer = CompanySettingsSerializer(settings, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Update company settings (partial update)."""
        settings = CompanySettings.load()
        serializer = CompanySettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# USER MANAGEMENT ENDPOINTS
# ============================================

class CurrentUserView(APIView):
    """
    Get current user profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user with profile information."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class CurrentUserProfileView(APIView):
    """
    Update current user profile (name, picture, setup status).
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        """Update current user profile."""
        profile = request.user.profile
        serializer = UserProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            user_serializer = UserSerializer(request.user)
            return Response(user_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """
    List users with flexible access rules:
    - Admins: Can list all users (no filter required)
    - Authenticated users: Can list users when filtering by department
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        """
        Filter users based on permissions and query parameters.
        """
        user = self.request.user
        department = self.request.query_params.get('department', None)

        # Base queryset
        queryset = User.objects.filter(is_active=True).select_related('profile').order_by('first_name', 'last_name', 'email')

        # Check if user has profile
        if not hasattr(user, 'profile'):
            return queryset.none()

        profile = user.profile

        # Admins can see all users, with or without filter
        if profile.is_admin:
            if department:
                return queryset.filter(profile__department__code=department)
            return queryset

        # Non-admin users must provide a department filter
        if not department:
            return queryset.none()

        # Filter by requested department
        return queryset.filter(profile__department__code=department)


class DepartmentUsersView(generics.ListAPIView):
    """
    List users from the current user's department (for campaign handlers, etc.).

    Access rules:
    - Admins: See all users
    - Managers/Employees: See users from their department only
    - Guests/No department: See nothing
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        """Filter users based on role and department."""
        user = self.request.user

        # Base queryset - only active users
        queryset = User.objects.filter(is_active=True).select_related('profile').order_by('first_name', 'last_name', 'email')

        # Check if user has profile
        if not hasattr(user, 'profile'):
            return queryset.none()

        profile = user.profile

        # Admins see all users
        if profile.is_admin:
            return queryset

        # Users without a department see nothing
        if not profile.department:
            return queryset.none()

        # Managers and employees see only users from their department
        return queryset.filter(profile__department=profile.department)


class UserDetailView(APIView):
    """
    Get or update a specific user (admin only).
    """
    permission_classes = [IsAuthenticated, IsAdministrator]

    def get(self, request, user_id):
        """Get user details."""
        try:
            user = User.objects.select_related('profile').get(id=user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, user_id):
        """Update user role and department."""
        try:
            user = User.objects.select_related('profile').get(id=user_id)
            profile = user.profile

            serializer = UserRoleUpdateSerializer(
                profile,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                serializer.save()
                user_serializer = UserSerializer(user)
                return Response(user_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================
# DEPARTMENT REQUEST ENDPOINTS
# ============================================

class DepartmentRequestListView(generics.ListAPIView):
    """
    List department requests.
    - Regular users: see their own requests
    - Admins/Managers: see all requests (or filter by department)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentRequestSerializer

    def get_queryset(self):
        user = self.request.user
        profile = user.profile

        # Admins see all requests
        if profile.is_admin:
            queryset = DepartmentRequest.objects.all()
        # Managers see requests for their department
        elif profile.is_manager and profile.department:
            queryset = DepartmentRequest.objects.filter(
                requested_department=profile.department_code
            )
        # Regular users see only their own requests
        else:
            queryset = DepartmentRequest.objects.filter(user=user)

        # Optional filtering by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.select_related('user', 'reviewed_by').order_by('-created_at')


class DepartmentRequestCreateView(generics.CreateAPIView):
    """
    Create a new department request.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DepartmentRequestCreateSerializer


class DepartmentRequestDetailView(APIView):
    """
    Get or review a department request.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        """Get department request details."""
        try:
            dept_request = DepartmentRequest.objects.select_related('user', 'reviewed_by').get(id=request_id)

            # Check permissions: user can see their own, admins/managers can see all
            profile = request.user.profile
            if not (
                dept_request.user == request.user or
                profile.is_admin or
                (profile.is_manager and profile.department_code == dept_request.requested_department)
            ):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )

            serializer = DepartmentRequestSerializer(dept_request)
            return Response(serializer.data)
        except DepartmentRequest.DoesNotExist:
            return Response(
                {'error': 'Department request not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def patch(self, request, request_id):
        """Review a department request (approve/reject)."""
        profile = request.user.profile

        # Only admins and managers can review
        if not (profile.is_admin or profile.is_manager):
            return Response(
                {'error': 'Only administrators and managers can review department requests'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            dept_request = DepartmentRequest.objects.select_related('user__profile').get(id=request_id)

            # Managers can only review requests for their department
            if profile.is_manager and profile.department_code != dept_request.requested_department:
                return Response(
                    {'error': 'You can only review requests for your department'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Can't review already reviewed requests
            if dept_request.status != 'pending':
                return Response(
                    {'error': 'This request has already been reviewed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = DepartmentRequestReviewSerializer(
                dept_request,
                data=request.data,
                partial=True
            )
            if serializer.is_valid():
                dept_request.reviewed_by = request.user
                dept_request.reviewed_at = timezone.now()
                serializer.save()

                # If approved, update user's role and department
                if dept_request.status == 'approved':
                    user_profile = dept_request.user.profile
                    # Get the Department object
                    department = Department.objects.get(code=dept_request.requested_department)
                    user_profile.department = department
                    # Assign employee role by default when approving
                    if dept_request.requested_department == 'digital':
                        user_profile.role = Role.objects.get(code='digital_employee')
                    elif dept_request.requested_department == 'sales':
                        user_profile.role = Role.objects.get(code='sales_employee')
                    user_profile.save()

                result_serializer = DepartmentRequestSerializer(dept_request)
                return Response(result_serializer.data)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except DepartmentRequest.DoesNotExist:
            return Response(
                {'error': 'Department request not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, request_id):
        """Cancel/withdraw a pending department request."""
        try:
            dept_request = DepartmentRequest.objects.get(id=request_id)

            # Only the user who created the request can cancel it
            if dept_request.user != request.user:
                return Response(
                    {'error': 'You can only cancel your own department requests'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Can only cancel pending requests
            if dept_request.status != 'pending':
                return Response(
                    {'error': 'Only pending requests can be canceled'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            dept_request.delete()
            return Response(
                {'message': 'Department request canceled successfully'},
                status=status.HTTP_200_OK
            )
        except DepartmentRequest.DoesNotExist:
            return Response(
                {'error': 'Department request not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PendingRequestsCountView(APIView):
    """
    Get count of pending department requests (for admins/managers).
    """
    permission_classes = [IsAuthenticated, IsAdministratorOrManager]

    def get(self, request):
        """Get pending requests count."""
        profile = request.user.profile

        if profile.is_admin:
            # Admins see all pending requests
            count = DepartmentRequest.objects.filter(status='pending').count()
        elif profile.is_manager and profile.department:
            # Managers see pending requests for their department
            count = DepartmentRequest.objects.filter(
                status='pending',
                requested_department=profile.department_code
            ).count()
        else:
            count = 0

        return Response({'count': count})


# ============================================
# DEPARTMENT MANAGEMENT ENDPOINTS
# ============================================

class DepartmentListView(generics.ListCreateAPIView):
    """
    List all departments or create a new department (admin only).
    """
    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a department (admin only).
    """
    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        """Prevent deletion if department has users or is used in roles."""
        if instance.users.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Cannot delete department '{instance.name}' because it has {instance.users.count()} users assigned."
            )
        if instance.roles.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Cannot delete department '{instance.name}' because it has {instance.roles.count()} roles."
            )
        instance.delete()


# ============================================
# ROLE MANAGEMENT ENDPOINTS
# ============================================

class RoleListView(generics.ListCreateAPIView):
    """
    List all roles or create a new role (admin only).
    """
    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = Role.objects.all().select_related('department').order_by('level', 'name')
    serializer_class = RoleSerializer


class RoleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a role (admin only).
    """
    permission_classes = [IsAuthenticated, IsAdministrator]
    queryset = Role.objects.all().select_related('department')
    serializer_class = RoleSerializer
    lookup_field = 'pk'

    def perform_destroy(self, instance):
        """Prevent deletion if role has users or is a system role."""
        if instance.is_system_role:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Cannot delete system role '{instance.name}'."
            )
        if instance.users.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                f"Cannot delete role '{instance.name}' because it has {instance.users.count()} users assigned."
            )
        instance.delete()

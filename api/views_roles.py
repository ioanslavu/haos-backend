from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminOrSuperuser
from rest_framework import status
from .models import UserProfile, Role

User = get_user_model()


class RolesListView(APIView):
    """
    List all roles from the database with user counts and permission counts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        roles = Role.objects.all().select_related('department').order_by('level', 'name')
        roles_data = []
        for role in roles:
            # Get user count for this role
            count = role.users.count()
            # Get permission count from associated group
            group, _ = Group.objects.get_or_create(name=role.code)
            perm_count = group.permissions.count()

            roles_data.append({
                'id': role.id,
                'code': role.code,
                'name': role.name,
                'level': role.level,
                'department': role.department.code if role.department else None,
                'department_name': role.department.name if role.department else None,
                'is_system_role': role.is_system_role,
                'is_active': role.is_active,
                'user_count': count,
                'permission_count': perm_count,
            })
        return Response(roles_data)

    def post(self, request):
        # Creating new roles should be done via the role management API
        return Response({
            'error': 'Use /api/v1/roles/management/ endpoint to create new roles'
        }, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailView(APIView):
    """
    Get details of a specific role including users and permissions.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, role_id):
        try:
            role = Role.objects.select_related('department').get(id=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

        # Get users with this role
        users = User.objects.filter(profile__role=role).select_related('profile__department')
        users_data = [{
            'id': u.id,
            'email': u.email,
            'full_name': f"{u.first_name} {u.last_name}".strip() or u.email,
            'department': u.profile.department.code if u.profile.department else None,
            'department_name': u.profile.department.name if u.profile.department else None,
        } for u in users]

        # Group-backed permissions
        group, _ = Group.objects.get_or_create(name=role.code)
        perms = group.permissions.select_related('content_type').all()

        return Response({
            'id': role.id,
            'code': role.code,
            'name': role.name,
            'level': role.level,
            'description': role.description,
            'department': role.department.code if role.department else None,
            'department_name': role.department.name if role.department else None,
            'is_system_role': role.is_system_role,
            'is_active': role.is_active,
            'user_count': len(users_data),
            'permission_count': perms.count(),
            'permissions': [
                {
                    'id': p.id,
                    'name': p.name,
                    'codename': p.codename,
                    'app_label': p.content_type.app_label,
                    'model': p.content_type.model,
                }
                for p in perms
            ],
            'users': users_data,
        })

    def patch(self, request, role_id):
        return Response({
            'error': 'Use /api/v1/roles/management/<id>/ endpoint to edit roles'
        }, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, role_id):
        return Response({
            'error': 'Use /api/v1/roles/management/<id>/ endpoint to delete roles'
        }, status=status.HTTP_400_BAD_REQUEST)


class RoleUsersView(APIView):
    """
    List all users with a specific role.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, role_id):
        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

        users = User.objects.filter(profile__role=role).select_related('profile__department')
        data = [{
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'department': u.profile.department.code if u.profile.department else None,
            'department_name': u.profile.department.name if u.profile.department else None,
        } for u in users]
        return Response(data)


class RolePermissionsView(APIView):
    """
    Manage permissions for a specific role (admin only).
    """
    permission_classes = [IsAuthenticated]
    throttle_scope = 'roles_admin'

    def get_permissions(self):
        # All methods on this view are admin/superuser only
        if self.request.method in ["GET", "POST", "DELETE"]:
            return [IsAuthenticated(), IsAdminOrSuperuser()]
        return super().get_permissions()

    def _resolve_role(self, role_id):
        """Get role and associated group from database."""
        try:
            role = Role.objects.get(id=role_id)
            group, _ = Group.objects.get_or_create(name=role.code)
            return role, group
        except Role.DoesNotExist:
            return None, None

    def get(self, request, role_id):
        """List all permissions for a role."""
        role, group = self._resolve_role(role_id)
        if not role:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        perms = group.permissions.select_related('content_type').all()
        return Response([
            {
                'id': p.id,
                'name': p.name,
                'codename': p.codename,
                'app_label': p.content_type.app_label,
                'model': p.content_type.model,
            }
            for p in perms
        ])

    def post(self, request, role_id):
        """Add, set, or remove permissions for a role."""
        role, group = self._resolve_role(role_id)
        if not role:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action')
        perm_ids = request.data.get('permissions') or []
        perm_codenames = request.data.get('permission_codenames') or []

        perms_to_apply = set()
        if perm_ids:
            perms_to_apply.update(Permission.objects.filter(id__in=perm_ids))
        if perm_codenames:
            # Expect format 'app_label.codename' or just 'codename' (will match across app labels)
            for code_name in perm_codenames:
                if '.' in code_name:
                    app_label, codename = code_name.split('.', 1)
                    perms_to_apply.update(Permission.objects.filter(codename=codename, content_type__app_label=app_label))
                else:
                    perms_to_apply.update(Permission.objects.filter(codename=code_name))

        if action == 'set':
            group.permissions.set(perms_to_apply)
        elif action == 'add':
            group.permissions.add(*list(perms_to_apply))
        elif action == 'remove':
            group.permissions.remove(*list(perms_to_apply))
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': 'ok'})

    def delete(self, request, role_id):
        """Clear all permissions for a role."""
        role, group = self._resolve_role(role_id)
        if not role:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        group.permissions.clear()
        return Response(status=status.HTTP_204_NO_CONTENT)

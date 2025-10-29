from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import UserProfile

User = get_user_model()


def _role_index_map():
    return {code: idx + 1 for idx, (code, _name) in enumerate(UserProfile.ROLE_CHOICES)}


class RolesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        idx_map = _role_index_map()
        roles = []
        for code, name in UserProfile.ROLE_CHOICES:
            count = User.objects.filter(profile__role=code).count()
            roles.append({
                'id': idx_map[code],
                'name': code,
                'user_count': count,
                'permission_count': 0,
            })
        return Response(roles)

    def post(self, request):
        # Creating new roles not supported with fixed role choices
        return Response({'error': 'Creating roles is not supported'}, status=status.HTTP_400_BAD_REQUEST)


class RoleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, role_id):
        idx_map = _role_index_map()
        reverse = {v: k for k, v in idx_map.items()}
        code = reverse.get(int(role_id))
        if not code:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        users = User.objects.filter(profile__role=code).select_related('profile')
        users_data = [{
            'id': u.id,
            'email': u.email,
            'full_name': f"{u.first_name} {u.last_name}".strip(),
            'department': getattr(getattr(u, 'profile', None), 'department', None),
        } for u in users]
        # Group-backed permissions
        group, _ = Group.objects.get_or_create(name=code)
        perms = group.permissions.select_related('content_type').all()

        return Response({
            'id': role_id,
            'name': code,
            'user_count': users.count(),
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
        return Response({'error': 'Editing role names is not supported'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, role_id):
        return Response({'error': 'Deleting roles is not supported'}, status=status.HTTP_400_BAD_REQUEST)


class RoleUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, role_id):
        idx_map = _role_index_map()
        reverse = {v: k for k, v in idx_map.items()}
        code = reverse.get(int(role_id))
        if not code:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        qs = User.objects.filter(profile__role=code).select_related('profile')
        data = [{
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'department': getattr(getattr(u, 'profile', None), 'department', None),
        } for u in qs]
        return Response(data)


class RolePermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def _resolve_role(self, role_id):
        idx_map = _role_index_map()
        reverse = {v: k for k, v in idx_map.items()}
        code = reverse.get(int(role_id))
        if not code:
            return None, None
        group, _ = Group.objects.get_or_create(name=code)
        return code, group

    def get(self, request, role_id):
        code, group = self._resolve_role(role_id)
        if not code:
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
        code, group = self._resolve_role(role_id)
        if not code:
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
        code, group = self._resolve_role(role_id)
        if not code:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
        group.permissions.clear()
        return Response(status=status.HTTP_204_NO_CONTENT)

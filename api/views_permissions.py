from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminOrSuperuser, IsSelfOrAdmin
from rest_framework import status

User = get_user_model()


class UserPermissionsView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'permissions_admin'

    def get_permissions(self):
        # GET: self or admin; POST/DELETE: admin/superuser only
        if self.request.method in ["POST", "DELETE"]:
            return [IsAuthenticated(), IsAdminOrSuperuser()]
        if self.request.method == "GET":
            return [IsAuthenticated(), IsSelfOrAdmin()]
        return super().get_permissions()

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        group_perms = set()
        for g in user.groups.all():
            for p in g.permissions.select_related('content_type').all():
                group_perms.add((p.id, p.codename, p.name, p.content_type.app_label, p.content_type.model, g.name))

        direct_perms = user.user_permissions.select_related('content_type').all()

        data = {
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'department': getattr(getattr(user, 'profile', None), 'department', None),
                'role': getattr(getattr(user, 'profile', None), 'role', None),
            },
            'permissions': {
                'from_groups': [
                    {
                        'id': pid,
                        'codename': codename,
                        'name': name,
                        'app_label': app_label,
                        'model': model,
                        'source': 'group',
                        'group': group_name,
                    }
                    for (pid, codename, name, app_label, model, group_name) in sorted(group_perms)
                ],
                'direct': [
                    {
                        'id': p.id,
                        'codename': p.codename,
                        'name': p.name,
                        'app_label': p.content_type.app_label,
                        'model': p.content_type.model,
                        'source': 'direct',
                    }
                    for p in direct_perms
                ],
                'is_superuser': user.is_superuser,
            },
        }
        return Response(data)

    def post(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        app_label = request.data.get('app_label')
        model = request.data.get('model')
        permission = request.data.get('permission')  # codename, e.g., 'view_contract'
        if not (app_label and model and permission):
            return Response({'error': 'app_label, model, and permission are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
            perm = Permission.objects.get(content_type=ct, codename=permission)
        except (ContentType.DoesNotExist, Permission.DoesNotExist):
            return Response({'error': 'Permission not found'}, status=status.HTTP_404_NOT_FOUND)

        user.user_permissions.add(perm)
        return Response({'status': 'ok'})

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        app_label = request.data.get('app_label') if isinstance(request.data, dict) else None
        model = request.data.get('model') if isinstance(request.data, dict) else None
        permission = request.data.get('permission') if isinstance(request.data, dict) else None

        if app_label and model and permission:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model)
                perm = Permission.objects.get(content_type=ct, codename=permission)
                user.user_permissions.remove(perm)
            except (ContentType.DoesNotExist, Permission.DoesNotExist):
                return Response({'error': 'Permission not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user.user_permissions.clear()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AllPermissionsListView(APIView):
    # Only admins can enumerate all permissions
    permission_classes = [IsAuthenticated, IsAdminOrSuperuser]
    throttle_scope = 'permissions_admin'

    def get(self, request):
        perms = Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'content_type__model', 'codename')
        grouped = {}
        flat = []
        for p in perms:
            app = p.content_type.app_label
            model = p.content_type.model
            entry = {
                'id': p.id,
                'name': p.name,
                'codename': p.codename,
                'app_label': app,
                'model': model,
            }
            flat.append(entry)
            grouped.setdefault(app, {})
            grouped[app].setdefault(model, {'model_name': model, 'permissions': []})
            grouped[app][model]['permissions'].append(entry)
        return Response({'permissions': flat, 'grouped': grouped, 'count': len(flat)})

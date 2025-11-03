from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Contract
from .rbac import ContractTypePolicy
from django.db import ProgrammingError, OperationalError

User = get_user_model()


class ContractVerbsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        verbs = [
            'view',
            'publish',
            'send',
            'update',
            'delete',
            'regenerate',
        ]
        return Response({'module': 'contracts', 'verbs': verbs, 'types': [c[0] for c in Contract.CONTRACT_TYPE_CHOICES]})


class ContractPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List policy records, optionally filtered by role/department."""
        role = request.query_params.get('role')
        department = request.query_params.get('department')
        try:
            qs = ContractTypePolicy.objects.all()
            if role:
                qs = qs.filter(role=role)
            if department:
                qs = qs.filter(department=department)
            data = [
                {
                    'role': p.role,
                    'department': p.department,
                    'contract_type': p.contract_type,
                    'can_view': p.can_view,
                    'can_publish': p.can_publish,
                    'can_send': p.can_send,
                    'can_update': p.can_update,
                    'can_delete': p.can_delete,
                    'can_regenerate': p.can_regenerate,
                }
                for p in qs.order_by('role', 'department', 'contract_type')
            ]
        except (ProgrammingError, OperationalError):
            data = []
        return Response({'results': data})

    def put(self, request):
        """Bulk upsert policy rows. Expects a list of records with role, department, contract_type, flags."""
        items = request.data if isinstance(request.data, list) else request.data.get('items', [])
        if not isinstance(items, list):
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        updated = []
        try:
            for item in items:
                try:
                    obj, _ = ContractTypePolicy.objects.get_or_create(
                        role=item['role'],
                        department=item['department'],
                        contract_type=item['contract_type'],
                    )
                    for f in ['can_view', 'can_publish', 'can_send', 'can_update', 'can_delete', 'can_regenerate']:
                        if f in item:
                            setattr(obj, f, bool(item[f]))
                    obj.save()
                    updated.append({'role': obj.role, 'department': obj.department, 'contract_type': obj.contract_type})
                except Exception as e:
                    return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except (ProgrammingError, OperationalError):
            return Response({'error': 'Contracts RBAC migration not applied. Please run migrations.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'updated': updated})


class UserContractsMatrixView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        """Effective policy matrix for a user (based on profile role+department)."""
        try:
            user = User.objects.select_related('profile', 'profile__role', 'profile__department').get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        prof = getattr(user, 'profile', None)
        if not prof or not prof.department or not prof.role:
            return Response({'role': None, 'department': None, 'policies': []})
        try:
            qs = ContractTypePolicy.objects.filter(role=prof.role.code, department=prof.department.code)
            data = [
                {
                    'contract_type': p.contract_type,
                    'can_view': p.can_view,
                    'can_publish': p.can_publish,
                    'can_send': p.can_send,
                    'can_update': p.can_update,
                    'can_delete': p.can_delete,
                    'can_regenerate': p.can_regenerate,
                }
                for p in qs.order_by('contract_type')
            ]
        except (ProgrammingError, OperationalError):
            data = []
        return Response({'role': prof.role.code, 'department': prof.department.code, 'policies': data})

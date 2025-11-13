from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CompanySettings, UserProfile, DepartmentRequest, Department, Role

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id',
            'code',
            'name',
            'description',
            'is_active',
            'user_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        """Return count of users in this department."""
        return obj.users.count() if hasattr(obj, 'users') else 0


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""
    department_detail = DepartmentSerializer(source='department', read_only=True)
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id',
            'code',
            'name',
            'description',
            'level',
            'department',
            'department_detail',
            'is_system_role',
            'is_active',
            'user_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        """Return count of users with this role."""
        return obj.users.count() if hasattr(obj, 'users') else 0


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    role_detail = RoleSerializer(source='role', read_only=True)
    department_detail = DepartmentSerializer(source='department', read_only=True)

    # For backward compatibility and easier access
    role_code = serializers.CharField(source='role.code', read_only=True)
    department_code = serializers.CharField(source='department.code', read_only=True, allow_null=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'role',
            'role_detail',
            'role_code',
            'department',
            'department_detail',
            'department_code',
            'profile_picture',
            'setup_completed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with profile information."""

    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    role = serializers.CharField(source='profile.role_code', read_only=True)
    role_detail = RoleSerializer(source='profile.role', read_only=True)
    department = serializers.CharField(source='profile.department_code', read_only=True, allow_null=True)
    department_detail = DepartmentSerializer(source='profile.department', read_only=True)
    profile_picture = serializers.ImageField(source='profile.profile_picture', read_only=True)
    setup_completed = serializers.BooleanField(source='profile.setup_completed', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'is_active',
            'date_joined',
            'profile',
            'role',
            'role_detail',
            'department',
            'department_detail',
            'profile_picture',
            'setup_completed',
        ]
        read_only_fields = ['id', 'email', 'date_joined', 'full_name']

    def get_full_name(self, obj):
        """Return full name or email as fallback"""
        return obj.get_full_name() or obj.email


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile (by the user themselves)."""

    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = UserProfile
        fields = [
            'first_name',
            'last_name',
            'profile_picture',
            'setup_completed',
        ]

    def update(self, instance, validated_data):
        # Update User fields
        user_data = validated_data.pop('user', {})
        if 'first_name' in user_data:
            instance.user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            instance.user.last_name = user_data['last_name']
        instance.user.save()

        # Update UserProfile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class UserRoleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user role and department (admin only)."""

    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.filter(is_active=True))
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        allow_null=True,
        required=False
    )

    class Meta:
        model = UserProfile
        fields = ['role', 'department']

    def validate(self, data):
        """
        Validate role and department compatibility.

        Rules:
        - If role has a specific department restriction, user must be assigned to that department
        - Employees and managers (level 200-999) must have a department
        - Guest and admin (level <200 or >=1000) don't require department
        """
        role = data.get('role', self.instance.role if self.instance else None)
        department = data.get('department', self.instance.department if self.instance else None)

        if role:
            # Check if role is restricted to specific department
            if role.department:
                if department != role.department:
                    data['department'] = role.department
            else:
                # Role has no department restriction
                # Check if this role level requires a department
                if 200 <= role.level < 1000:
                    if not department:
                        raise serializers.ValidationError({
                            'department': f"Role '{role.name}' (level {role.level}) requires a department to be assigned."
                        })
                else:
                    # Guest or Admin - no department required
                    pass

        return data


class DepartmentRequestSerializer(serializers.ModelSerializer):
    """Serializer for DepartmentRequest model."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True)

    class Meta:
        model = DepartmentRequest
        fields = [
            'id',
            'user',
            'user_email',
            'user_name',
            'requested_department',
            'status',
            'message',
            'reviewed_by',
            'reviewed_by_email',
            'reviewed_at',
            'rejection_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'user',
            'status',
            'reviewed_by',
            'reviewed_at',
            'created_at',
            'updated_at',
        ]

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email


class DepartmentRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a department request."""

    class Meta:
        model = DepartmentRequest
        fields = ['requested_department', 'message']

    def validate_requested_department(self, value):
        """Validate that user doesn't already have a pending request for this department."""
        user = self.context['request'].user

        # Check for existing pending requests
        existing_pending = DepartmentRequest.objects.filter(
            user=user,
            requested_department=value,
            status='pending'
        ).exists()

        if existing_pending:
            raise serializers.ValidationError(
                f"You already have a pending request for the {value} department."
            )

        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class DepartmentRequestReviewSerializer(serializers.ModelSerializer):
    """Serializer for reviewing department requests (admin/manager only)."""

    class Meta:
        model = DepartmentRequest
        fields = ['status', 'rejection_reason']

    def validate_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError("Status must be either 'approved' or 'rejected'.")
        return value

    def validate(self, data):
        if data.get('status') == 'rejected' and not data.get('rejection_reason'):
            raise serializers.ValidationError({
                'rejection_reason': 'Rejection reason is required when rejecting a request.'
            })
        return data


class CompanySettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for CompanySettings model.
    """

    class Meta:
        model = CompanySettings
        fields = [
            'id',
            'company_name',
            'legal_name',
            'admin_name',
            'admin_role',
            'registration_number',  # J40/XXXXX/2020
            'cif',  # RO12345678 (C.I.F.)
            'vat_number',  # Optional, defaults to C.I.F.
            'email',
            'phone',
            'website',
            'address',
            'city',
            'state',
            'zip_code',
            'country',
            'bank_name',
            'bank_account',
            'bank_swift',
            'timezone',
            'currency',
            'language',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

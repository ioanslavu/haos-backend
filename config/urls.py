"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from api import views as api_views
from api import views_impersonate
from api import views_roles as api_roles
from api import views_permissions as api_perms

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),

    # User Impersonation (admin role testing)
    path('impersonate/', include('impersonate.urls')),

    # API endpoints (matching frontend specification)
    path('api/auth/status/', api_views.auth_status, name='auth_status'),
    # Debug endpoint
    path('api/v1/auth/debug/', api_views.oauth_debug, name='oauth_debug'),

    # Company Settings API
    path('api/v1/settings/company/', api_views.CompanySettingsView.as_view(), name='company_settings'),

    # User Management API
    path('api/v1/users/me/', api_views.CurrentUserView.as_view(), name='current_user'),
    path('api/v1/users/me/profile/', api_views.CurrentUserProfileView.as_view(), name='current_user_profile'),
    path('api/v1/users/', api_views.UserListView.as_view(), name='user_list'),
    path('api/v1/users/department/', api_views.DepartmentUsersView.as_view(), name='department_users'),
    path('api/v1/users/<int:user_id>/', api_views.UserDetailView.as_view(), name='user_detail'),

    # Department Requests API
    path('api/v1/department-requests/', api_views.DepartmentRequestListView.as_view(), name='department_request_list'),
    path('api/v1/department-requests/create/', api_views.DepartmentRequestCreateView.as_view(), name='department_request_create'),
    path('api/v1/department-requests/<int:request_id>/', api_views.DepartmentRequestDetailView.as_view(), name='department_request_detail'),
    path('api/v1/department-requests/pending/count/', api_views.PendingRequestsCountView.as_view(), name='pending_requests_count'),

    # Department Management API (admin only)
    path('api/v1/departments/', api_views.DepartmentListView.as_view(), name='department_list'),
    path('api/v1/departments/<int:pk>/', api_views.DepartmentDetailView.as_view(), name='department_detail'),

    # Role Management API (admin only)
    path('api/v1/roles/management/', api_views.RoleListView.as_view(), name='role_management_list'),
    path('api/v1/roles/management/<int:pk>/', api_views.RoleDetailView.as_view(), name='role_management_detail'),

    # Roles API (fixed roles mapped from UserProfile)
    path('api/v1/roles/', api_roles.RolesListView.as_view(), name='roles_list'),
    path('api/v1/roles/<int:role_id>/', api_roles.RoleDetailView.as_view(), name='role_detail'),
    path('api/v1/roles/<int:role_id>/users/', api_roles.RoleUsersView.as_view(), name='role_users'),
    path('api/v1/roles/<int:role_id>/permissions/', api_roles.RolePermissionsView.as_view(), name='role_permissions'),

    # User permissions API (direct perms + from groups)
    path('api/v1/users/<int:user_id>/permissions/', api_perms.UserPermissionsView.as_view(), name='user_permissions'),
    path('api/v1/permissions/', api_perms.AllPermissionsListView.as_view(), name='permissions_list'),

    # Impersonation API (admin role testing)
    path('api/v1/impersonate/start/', views_impersonate.StartImpersonationView.as_view(), name='impersonate_start'),
    path('api/v1/impersonate/stop/', views_impersonate.StopImpersonationView.as_view(), name='impersonate_stop'),
    path('api/v1/impersonate/status/', views_impersonate.ImpersonationStatusView.as_view(), name='impersonate_status'),
    path('api/v1/impersonate/test-users/', views_impersonate.TestUsersListView.as_view(), name='impersonate_test_users'),

    # Contracts API
    path('api/v1/', include('contracts.urls')),

    # ERP System APIs
    path('api/v1/identity/', include('identity.urls')),
    path('api/v1/', include('catalog.urls')),
    path('api/v1/rights/', include('rights.urls')),
    path('api/v1/distribution/', include('distribution.urls')),

    # Distributions API (long-term distribution deals)
    path('api/v1/', include('distributions.urls')),

    # Campaigns API
    path('api/v1/', include('campaigns.urls')),

    # CRM Extensions API (Tasks, Activities, Metrics)
    path('api/v1/crm/', include('crm_extensions.urls')),

    # Artist Sales API (Image Rights & Brand Deals)
    path('api/v1/artist-sales/', include('artist_sales.urls')),

    # Notifications API
    path('api/v1/', include('notifications.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

"""
Queryset scoping modes for BaseViewSet.

Defines explicit constants for different data visibility patterns,
preventing typos and making scoping intentions clear.
"""
from enum import Enum


class QuerysetScoping(Enum):
    """
    Explicit scoping modes for BaseViewSet queryset filtering.

    These modes define "what rows exist" (data visibility), while
    permission classes define "who may act" (authorization).

    NONE: No queryset filtering
        - Use when permission class handles all access control
        - Permission class should return 403 for unauthorized users
        - Example: Admin-only endpoints

    GLOBAL: All authenticated users see all records
        - No department or role-based filtering
        - Example: Global catalog (artists, works, recordings)

    DEPARTMENT: Filter by user's department only
        - All users in department see all department records
        - Both managers and employees see same data
        - Example: Department-wide resources

    DEPARTMENT_WITH_OWNERSHIP: Filter by department AND ownership/assignment
        - Managers: see all records in their department
        - Employees: see only records they created OR are assigned to
        - Example: Campaigns, tasks, contracts
    """

    NONE = 'none'
    GLOBAL = 'global'
    DEPARTMENT = 'department'
    DEPARTMENT_WITH_OWNERSHIP = 'department_with_ownership'

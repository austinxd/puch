from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Only allows access to staff (admin) users."""

    def has_permission(self, request, view):
        return request.user and request.user.is_staff

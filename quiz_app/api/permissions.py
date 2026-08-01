"""Permission classes for the quiz endpoints."""

from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access to a quiz only for the user that owns it."""

    def has_object_permission(self, request, view, obj):
        """Return whether the requesting user owns the quiz."""
        return obj.owner == request.user

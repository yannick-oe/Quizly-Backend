"""Permission classes for the quiz endpoints.

The ownership rule is an object permission and nothing else. DRF looks
an object up before it checks object permissions, so filtering the
detail queryset on the owner would answer 404 where the endpoint
documentation asks for 403. The queryset therefore stays open for the
detail actions and this class decides; see DEVIATIONS.md.
"""

from rest_framework.permissions import BasePermission


class IsQuizOwner(BasePermission):
    """Allow access to a quiz only for the user that owns it.

    has_permission is left at its inherited True. Who may reach the
    endpoint at all is the job of IsAuthenticated, and a request for
    the list or for a new quiz has no object to compare against.
    """

    def has_object_permission(self, request, view, obj):
        """Return whether the requesting user owns the quiz."""
        return obj.owner == request.user

from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Lecture pour tout le monde
    Écriture uniquement pour admin/staff
    """

    def has_permission(self, request, view):
        # Autorise GET, HEAD, OPTIONS pour tous
        if request.method in permissions.SAFE_METHODS:
            return True

        # Autorise POST, PUT, PATCH, DELETE seulement aux staff/admin
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_staff
                or user.is_superuser
                or getattr(user, "role", None) == "ADMIN"
            )
        )

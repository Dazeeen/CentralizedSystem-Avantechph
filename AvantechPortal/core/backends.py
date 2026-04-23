from django.contrib.auth.backends import ModelBackend


class ExplicitUserPermissionBackend(ModelBackend):
    """Use direct user permissions as an override when explicitly assigned.

    Behavior:
    - Superusers keep full access.
    - If a user has at least one direct permission in `user_permissions`,
      only those direct permissions are used for authorization checks.
    - If a user has no direct permissions, normal role/group permissions apply.
    """

    @staticmethod
    def _has_explicit_user_permissions(user_obj):
        if not hasattr(user_obj, '_has_explicit_user_permissions_cache'):
            user_obj._has_explicit_user_permissions_cache = user_obj.user_permissions.exists()
        return user_obj._has_explicit_user_permissions_cache

    def get_group_permissions(self, user_obj, obj=None):
        if obj is not None or user_obj is None or not user_obj.is_active:
            return set()

        if self._has_explicit_user_permissions(user_obj):
            return set()

        return super().get_group_permissions(user_obj, obj=obj)

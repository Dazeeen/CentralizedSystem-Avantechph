from django.contrib.auth.backends import ModelBackend


CRM_ADMIN_PERMISSION = 'core.manage_crm_admin'
CRM_ADMIN_IMPLIED_PERMISSIONS = {
    'core.view_crm_dashboard',
    'core.view_crm_clients_section',
    'core.manage_crm_clients_section',
    'core.view_crm_sales_section',
    'core.manage_crm_sales_section',
    'core.view_crm_technicals_section',
    'core.manage_crm_technicals_section',
    'core.add_crmclient',
    'core.change_crmclient',
    'core.delete_crmclient',
    'core.view_crmclient',
    'core.add_crmclientmedia',
    'core.change_crmclientmedia',
    'core.delete_crmclientmedia',
    'core.view_crmclientmedia',
    'core.add_crmsalesrecord',
    'core.change_crmsalesrecord',
    'core.delete_crmsalesrecord',
    'core.view_crmsalesrecord',
    'core.add_crmtechnicalrecord',
    'core.change_crmtechnicalrecord',
    'core.delete_crmtechnicalrecord',
    'core.view_crmtechnicalrecord',
}
CUSTOM_ADMIN_IMPLIED_PERMISSIONS = {
    'core.can_manage_accountability': {
        'core.view_assetaccountability',
        'core.add_assetaccountability',
        'core.change_assetaccountability',
        'core.view_assetreturnproof',
    },
    'core.can_manage_supportticket': {
        'core.view_supportticket',
        'core.add_supportticket',
        'core.change_supportticket',
        'core.view_supportticketmessage',
        'core.add_supportticketmessage',
        'core.change_supportticketmessage',
    },
    'core.approve_clientdeletionrequest': {
        'core.view_client',
        'core.view_clientdeletionrequest',
        'core.change_clientdeletionrequest',
    },
    'core.approve_crmclientdeletionrequest': {
        'core.view_crm_clients_section',
        'core.view_crmclient',
        'core.view_crmclientdeletionrequest',
        'core.change_crmclientdeletionrequest',
    },
    'core.reveal_companyinternetaccount_password': {
        'core.view_companyinternetaccount',
    },
}


def _build_implied_permissions(permissions):
    implied = set()
    for permission in permissions:
        if permission == CRM_ADMIN_PERMISSION:
            implied.update(CRM_ADMIN_IMPLIED_PERMISSIONS)
        implied.update(CUSTOM_ADMIN_IMPLIED_PERMISSIONS.get(permission, set()))

        try:
            app_label, codename = permission.split('.', 1)
        except ValueError:
            continue

        for admin_action in ('add_', 'change_', 'delete_'):
            if codename.startswith(admin_action):
                implied.add(f'{app_label}.view_{codename[len(admin_action):]}')

        if codename.startswith('manage_'):
            implied.add(f'{app_label}.view_{codename[len("manage_"):]}')

        if codename.startswith('manage_crm_') and codename.endswith('_section'):
            implied.add(f'{app_label}.view_{codename[len("manage_"):]}')

        if codename.startswith('can_manage_'):
            implied.add(f'{app_label}.view_{codename[len("can_manage_"):]}')

    return implied


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

    def get_all_permissions(self, user_obj, obj=None):
        permissions = set(super().get_all_permissions(user_obj, obj=obj))
        if obj is not None or user_obj is None or not user_obj.is_active:
            return permissions
        return permissions | _build_implied_permissions(permissions)

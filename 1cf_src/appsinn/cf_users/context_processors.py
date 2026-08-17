# cf-dev/cf_src/appsinn/cf_users/context_processors.py

"""Template context processors for organisation and branch context."""

from .tenancy import branches_for_user_qs, organizations_for_user_qs


def user_organization_and_branch(request):
    """
    Expose active tenant context and switcher lists (bounded querysets).
    """
    if not request.user.is_authenticated:
        return {
            "user_organization": None,
            "user_branch": None,
            "active_organization": None,
            "active_branch": None,
            "tenant_organizations": [],
            "tenant_branches": [],
            "user_is_branch_manager": False,
            "user_is_superuser": False,
        }

    user = request.user
    active_org = getattr(request, "organization", None)
    active_branch = getattr(request, "branch", None)

    # Switcher lists: capped for template safety (search for huge fleets later).
    tenant_orgs = list(organizations_for_user_qs(user)[:100])
    tenant_branches = list(
        branches_for_user_qs(
            user, organization_id=getattr(active_org, "pk", None)
        )[:100]
    )

    return {
        "user_organization": active_org,
        "user_branch": active_branch,
        "active_organization": active_org,
        "active_branch": active_branch,
        "tenant_organizations": tenant_orgs,
        "tenant_branches": tenant_branches,
        "user_is_branch_manager": getattr(user, "is_branch_manager", False),
        "user_is_superuser": user.is_superuser,
    }

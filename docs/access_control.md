# Access control (simple)

## Three layers

| Layer | What it is | Where |
|--------|------------|--------|
| **User flags** | Active, Staff, Superuser, Is church staff | User form checkboxes |
| **Django Groups + User permissions** | Platform-wide model perms (admin) | User → *Platform permissions* |
| **Organisation / branch membership + org groups** | Who belongs where; org-scoped perms | User inlines |

## User flags

| Flag | Effect |
|------|--------|
| **Active** | Can log in |
| **Staff** | Can use `/admin/` |
| **Superuser** | **All operations, all data** (no tenant limits) |
| **Is church staff** | Label only (directory / HR), not access |

## Django Groups

Native `auth.Group`: platform permissions for staff.  
Does **not** set Staff/Superuser flags.

## Organisation & branch

| Link | Role |
|------|------|
| **Organisation membership** | User belongs to an org (`OrganizationUser`) |
| **Branch membership** | User belongs to a branch (`BranchUser`) → also creates org membership if missing |
| **Organisation groups** | Org-specific permission packs (`OrganizationGroup` + membership) |

Branch user save → org user (Viewer) + default org groups (e.g. Members).

## Superuser

- Sees and edits **all** rows and FK choices
- All `has_perm` / admin actions allowed
- No org/branch filter on querysets

## Non-superuser admin

1. Must be **staff** (+ model perms via Django groups or org groups)
2. Data limited to **accessible orgs/branches**
3. User pickers show **peers** in those orgs/branches

## Code map

- `cf_users/multitenancy.py` — admin scope + form FKs  
- `cf_users/managers.py` — `for_user`  
- `cf_users/tenancy.py` — branch/org helpers, `users_visible_to_user_qs`  
- `cf_users/backends.py` — login + org-group perms + superuser  

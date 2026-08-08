# CF Church platform architecture

## Apps (`cf_src/appsinn/`)

| App | Responsibility |
|-----|----------------|
| `cf_users` | Users, orgs, branches, tenancy, groups, audit |
| `cf_people` | Members, families, zones, sub groups, visitors |
| `cf_operations` | Events, sessions, sermons, attendance, documents |
| `cf_finance` | Funds, budgets, transactions, HR |
| `cf_communications` | Notifications, broadcasts, birthday greetings |
| `cf_social` | Feed, follows, DMs, discussions |
| `cf_utils` | Shared helpers, DRF pagination / viewsets |

## Package layout (domain apps)

```
cf_<app>/
  base/models.py   # Abstract models
  models.py        # Concrete models + managers
  settings.py      # App defaults (overridable)
  api/             # DRF serializers, views, urls
  admin.py
  services.py / tasks.py / …
```

## Multi-tenant scale notes

- Prefer **SQL subqueries** (`accessible_branch_ids_qs`, `organizations_for_user_qs`)
  over materialising millions of UUIDs.
- Active org/branch in session + contextvars for hot-path filters.
- Cursor pagination default for APIs (`-modified_at`).

## Surfaces

| URL | Audience |
|-----|----------|
| `/` portal login | Org users **and** staff |
| `/dashboard/` | Organisation portal |
| `/admin/` | Django admin (staff + permissions) |
| `/social/` | Platform social app |
| `/api/v1/…` | Versioned DRF APIs |

## Related docs

- [Access control and groups](access_control.md)
- [Audit fields and models](audit_and_models.md)
- [Member numbers](member_numbers.md)
- [API overview](api.md)

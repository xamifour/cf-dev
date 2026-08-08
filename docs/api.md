# REST API overview

Base path: **`/api/v1/`**

| Prefix | App |
|--------|-----|
| `/api/v1/health/` | Health check (`cf_utils`) |
| `/api/v1/users/` | Organisations, branches |
| `/api/v1/people/` | Members, zones, subgroups, visitors |
| `/api/v1/operations/` | Events, sessions, sermons, attendance |
| `/api/v1/finance/` | Funds, transactions, budgets |
| `/api/v1/communications/` | Notifications, broadcasts |
| `/api/v1/social/` | Profiles, posts, discussions |

## Defaults

- Auth: session authentication (DRF); authenticated by default
- Pagination: cursor (`CFCursorPagination`), ordered by `-modified_at`
- Page size: `CF_API_PAGE_SIZE` (default 50), max `CF_API_MAX_PAGE_SIZE` (200)
- Viewsets: `CFModelViewSet` / `CFReadOnlyModelViewSet` with optional
  `for_user` tenant scoping

## Feature flags

Each domain app exposes `CF_<APP>_API_ENABLED` in its `settings.py`
(default `True`).

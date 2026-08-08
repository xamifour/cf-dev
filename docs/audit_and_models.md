# Audit fields and model conventions

## AuditMixin

Most domain models inherit `cf_users.mixins.AuditMixin`, which provides:

| Field | Behaviour |
|--------|-----------|
| `id` | UUID primary key (`uuid4`, set on create) |
| `created_at` | Set once on first save (`auto_now_add`) |
| `modified_at` | Updated on every save (`auto_now`) |
| `created_by` | User who first created the row |
| `modified_by` | User who last saved the row |

### How `created_by` / `modified_by` are set

1. **`AuditUserMiddleware`** binds the authenticated request user into a
   contextvar (`cf_users.audit`).
2. **`AuditMixin.save()`** reads that user and:
   - sets `created_by` on insert if empty
   - always sets `modified_by` on save
3. **`BaseAdmin.save_model()`** also stamps these fields as a safety net for
   admin saves.

Celery tasks and management commands without a request user leave
`created_by` / `modified_by` null unless set explicitly.

### Default ordering

`AuditMixin.Meta.ordering = ("-modified_at",)` so the most recently modified
objects appear first. Domain models may add secondary keys (name, serial, …).
Structural exceptions remain (e.g. event session `sort_order`, week stats by
week number).

## Abstract vs concrete models

| Layer | Location | Role |
|--------|----------|------|
| Abstract | `app/base/models.py` | Fields, validation, domain logic |
| Concrete | `app/models.py` | DB tables, managers (`TenantManager`) |

## Codes and sequences

- Organisation codes: global `ORG…` sequence (`AutoIncrementCodeMixin` +
  `CodeSequence`).
- Member numbers: **per organisation**, prefix = first 3 letters of the org
  name (see `member_numbers.md`).

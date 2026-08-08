# Member numbers

## Rules

1. **Unique per organisation** — not platform-wide  
   Constraint: `(organization, member_number)`.
2. **Prefix from organisation name** — first three **letters** of the org
   display name (trade name if set, else name), uppercased.  
   Examples:
   - `Word Chapel International` → `WOR00000001`
   - `Grace Assembly` → `GRA00000001`
   - Short / non-alpha names are padded with `X` (minimum length 3).
3. **Auto-generated** if left blank on create; immutable after create
   (same rules as other auto codes).
4. **Sequence** is per organisation + prefix:  
   `CodeSequence` name `{PREFIX}_{organization_id}_seq`.

## Implementation

- Model: `cf_people.Member` / `AbstractMember`
- Denormalised `organization` FK (synced from `branch.organization` on save)
- Generation: `_member_code_prefix()`, `_generate_code()`, org-scoped floor

## Admin

- Member number is read-only after generation
- Organisation is read-only (derived from branch)

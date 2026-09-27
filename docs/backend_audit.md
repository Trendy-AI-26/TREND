# P1-T05 Backend Audit

## Account

| Method | Route | Auth | Purpose | Status |
|---|---|---|---|---|
| GET | /me | get_current_user | Get Profile | Existing |
| PATCH | /me | get_current_user | Update Profile | Existing |
| POST | /me/avatar | get_current_user | Upload avatar | New/Under implementation |

## Brand Kit

| Method | Route | Auth | Purpose | Ownership check | Status |
|---|---|---|---|---|---|
| GET | /kit?brand_id={brand_id} | get_current_user | Get Brand | Required | Existing |
| PATCH | /kit?brand_id={brand_id} | get_current_user | Update Brand | Required | Existing |

## Provider Keys / BYOK

| Method | Route | Auth | Purpose | Raw key returned? | Future action |
|---|---|---|---|---|---|
| GET | /keys?brand_id={brand_id}/keys | get_current_user | List keys | Must be no | Hide/remove later |
| POST | /keys?brand_id={brand_id}/Keys | get_current_user | Add keys | Must be no | Disable later |
| POST | /keys/{key_id}/validate | get_current_user | Validate key | Must be no | Disable later |
| PATCH | /keys/{key_id}/activate | get_current_user | Activate key | Must be no | Disable later |
| DELETE | /keys/{key_id} | get_current_user | Delete key | N/A | Disable later |


## Navigation ownership decision

- Account Settings owns user profile data and language.
- Brand Settings owns brand-level settings.
- Brand Kit owns brand identity answers.
- Provider Keys are legacy BYOK functionality and should not be presented as the primary generation path after Managed Generation is enabled.


## BYOK audit

Current state:
- Provider key API exists in backend/app/routers/keys.py.
- Provider keys are stored per brand.
- Frontend has a brand keys page.
- The API must never return the raw provider key.
- BYOK is planned for removal from the public user flow.
- Removal belongs to the Managed Generation implementation phase, not this audit task.


## Ownership verification

- Brand Kit calls _get_brand_or_404(brand_id, current_user.id).
- Provider Key calls verify brand ownership before read/write/delete.
- Cross-user brand access should return 404.
- No route accepts owner_user_id from the request body.

# Asset Accountability Permission Checklist

Use this checklist when assigning roles for Asset Borrow Request workflow.

## Borrower Role (requester)

Required permissions:
- core.view_assetitem
- core.view_assetaccountability
- core.add_assetaccountability

What this role can do:
- Open Asset Accountability page
- Submit borrow requests
- View approved borrower records
- Receive in-app + email updates for request decision

## Reviewer/Admin Role (approver/decliner)

Required permissions:
- core.view_assetitem
- core.view_assetaccountability
- core.change_assetaccountability

Recommended permissions:
- core.add_assetitem
- core.change_assetitem
- core.add_assetdepartment
- core.change_assetdepartment

What this role can do:
- View pending borrow requests
- Approve request (deduct stock)
- Decline request with reason
- Mark approved borrow records as returned
- Receive in-app + email alert when new request arrives

## Superuser

- No extra setup required
- Has full access to submit, review, approve/decline, return, and manage assets

## Quick Validation Steps

1. Log in as Borrower role account.
2. Confirm Borrow Item button is visible in Asset Accountability.
3. Submit a borrow request and verify success message appears.
4. Log in as Reviewer/Admin role account.
5. Confirm request appears under Pending Borrow Requests.
6. Approve one request and decline one request with reason.
7. Confirm borrower receives in-app notification for both actions.
8. Confirm email is received by reviewer on new request and borrower on decision.

## Email Configuration Required

Set in .env (or environment variables):
- DEFAULT_FROM_EMAIL
- EMAIL_BACKEND
- EMAIL_HOST
- EMAIL_PORT
- EMAIL_HOST_USER
- EMAIL_HOST_PASSWORD
- EMAIL_USE_TLS

For local testing, you can keep:
- EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

Then emails will print in server logs/terminal.

# Avantech Centralized System User SOP

## 1. Purpose

This document is the daily operations guide for end users and team leads.
Use this for step-by-step procedures, role-based responsibilities, and routine checks.

This SOP is intentionally non-technical.
For architecture and developer details, see docs/system_documentation.md.

---

## 2. User Roles and Responsibilities

## Superuser
- Full access to all modules and settings.
- Creates roles, users, and permission assignments.
- Handles escalations, lockout support, and critical corrections.

## Admin / Reviewer
- Reviews and decides asset borrow requests.
- Manages assets, departments, item types, and returns.
- Can perform bulk actions when assigned required permissions.

## Staff / Borrower
- Submits asset borrow requests.
- Monitors request status and returns borrowed items on time.

## Sales / Client Handler
- Creates and updates client records.
- Uploads quotation files and tracks negotiation status.

---

## 3. Login and Account SOP

## 3.1 Log In
1. Open the login page.
2. Enter username and password.
3. Complete captcha.
4. If OTP is required, enter 6-digit authenticator code.
5. Click login.

## 3.2 If Login Is Blocked
1. Check if credentials are correct.
2. Wait for lockout cooldown if too many failed attempts happened.
3. Contact support/admin to unlock via lockout support page when needed.

## 3.3 Password Change
1. Go to Profile or Account settings.
2. Enter current password.
3. Enter and confirm new password.
4. Complete captcha.
5. Save changes.

---

## 4. Users and Roles SOP

## 4.1 Create a Role
1. Go to Roles.
2. Click Create Role.
3. Enter role name.
4. Select permissions using checkbox groups.
5. Save role.

## 4.2 Create a User
1. Go to Users.
2. Click Create User.
3. Fill profile fields (username, name, email, branch, status flags).
4. Assign one or more roles.
5. Optionally assign direct permissions.
6. Save user.

Important behavior:
- If direct permissions are assigned to a user, those direct permissions override role-derived permissions for access checks.

## 4.3 Edit or Bulk Update Users
1. Go to Users list.
2. Use row actions for single-user edit/delete.
3. Use checkboxes for bulk actions (status, role, delete).
4. Confirm action in prompt/modal.

---

## 5. Clients and Quotations SOP

## 5.1 Create a Client
1. Go to Clients.
2. Click Add/Create Client.
3. Fill required client details.
4. Set client status and lead status.
5. If lead status is Lost or Not Qualified, provide reason and proof image.
6. Save client.

## 5.2 Update Client Status in Bulk
1. In Clients list, select target rows.
2. Use bulk status action.
3. Confirm update.

## 5.3 Create Quotation
1. Open target client record.
2. Click Create Quotation.
3. Enter package and amount.
4. Set negotiation status.
5. Upload document(s) if status requires it.
6. Save quotation.

## 5.4 Generate/View Quotation Document
1. Open client quotation entry.
2. Use document action/view button.
3. Verify version and attached files before sending externally.

---

## 6. Asset Tracker SOP

## 6.1 Department Setup
1. Go to Asset Tracker.
2. Add Department for new organizational units.
3. Edit existing departments only when naming standard changes.

## 6.2 Item Type Setup
1. Open Item Types.
2. Create type with name, code, and prefix.
3. Keep prefix 2 to 5 alphanumeric characters.
4. Set active/inactive status as needed.

## 6.3 Add Asset Item (Parent Item)
1. Click Add Asset Item.
2. Select Department.
3. Leave Parent Item blank (for parent entry).
4. Fill name, type, optional specification, optional note.
5. Set stock quantity and low-stock threshold.
6. Optionally upload images.
7. Save.

## 6.4 Add Variant Item
1. Click Add Asset Item.
2. Select same department as parent.
3. Select Parent Item.
4. Fill variant details.
5. Add optional image(s), specification, note.
6. Save.

## 6.5 View Asset Item Details
1. In Asset list, click parent item row.
2. Review popup modal details:
- parent image (if available)
- specification (if available)
- note (if available)
- variants table and holder info
3. Click image thumbnail to open larger popup preview.

## 6.6 Asset Tag Generation
1. In Asset Tracker, click Generate Asset Tagging.
2. Select department scope if needed.
3. Generate and review created batch.
4. Open tagging document for print/export.

---

## 7. Asset Accountability SOP

## 7.1 Submit Borrow Request (Borrower)
1. Open Accountability.
2. Click Borrow Item.
3. Select item and quantity.
4. Add optional notes.
5. Submit request.

## 7.2 Review Request (Reviewer/Admin)
1. Open Accountability Pending section.
2. Review item, borrower, and quantity.
3. Choose Approve or Decline.
4. If declining, provide clear reason.
5. Confirm decision.

## 7.3 Return Item
1. Open approved borrowed record.
2. Click Return.
3. Upload return proof image when required.
4. Confirm return action.
5. Verify status changed to Returned.

## 7.4 Reports and CSV
1. Open Accountability Reports (summary or list).
2. Apply filters.
3. Export CSV when needed for audit or reporting.

---

## 8. Notifications SOP

## 8.1 Check Notifications
1. Open notification feed/list.
2. Review unread items first.
3. Click linked notification for direct record access.

## 8.2 Mark Notifications as Read
1. Open notification panel.
2. Mark single or all as read.
3. Ensure no critical decision alerts remain unread.

---

## 9. Daily Operations Checklist

## Start of Day
1. Log in and verify account status is active.
2. Check notifications and pending approvals.
3. Review low-stock indicators in Asset Tracker.

## During Day
1. Process borrow requests on schedule.
2. Update client and quotation statuses promptly.
3. Keep record notes clear and factual.

## End of Day
1. Ensure pending approvals are minimized.
2. Confirm returns are recorded.
3. Validate critical notifications are acknowledged.

---

## 10. Data Quality Rules

- Use complete and correct names for clients and users.
- Keep status fields up to date (do not leave stale statuses).
- Attach required proof files for lead/accountability workflows.
- Do not use duplicate or misleading notes.
- Use bulk actions carefully; always review selected rows before confirming.

---

## 11. Troubleshooting Quick Guide

## Cannot Log In
- Recheck username/password and captcha.
- If locked out, wait cooldown or request admin unlock.

## Borrow Request Not Visible
- Confirm user has accountability permissions.
- Confirm item has available stock.

## Cannot Approve/Decline
- Confirm reviewer has change/manage accountability permissions.

## Image Not Showing
- Verify file uploaded successfully.
- Reopen modal and click thumbnail for popup viewer.

## Missing Menu/Module
- Menu visibility depends on role and permissions.
- Request admin to review role or direct permissions.

---

## 12. Escalation Path

1. End user checks this SOP first.
2. Team lead validates process and permissions.
3. Admin/superuser checks role mapping and lockouts.
4. Developer support handles bugs, data fixes, and code-level issues.

---

## 13. Related Documents

- docs/system_documentation.md: technical and architecture reference
- docs/asset_accountability_permissions_checklist.md: accountability permission matrix

# Brightloop Subscription Management System: Implementation Plan

Team of 4 | Django only | 4-hour build window

## 1. Project Description

Brightloop Software sells software on subscription (monthly or yearly plans, add-ons, product variants). Today subscriptions live in a spreadsheet, renewals are remembered by hand, invoices are typed manually, payments are matched by scrolling bank statements, and revenue reports are built once a quarter.

We are building **one unified platform** that runs the full life of a subscription business: set up products and plans, create quotations and subscriptions, generate invoices automatically on billing day, apply taxes and discounts by rule, record payments, and report revenue in one dashboard.

### Users and roles

| Role | Access |
| --- | --- |
| Admin | Everything. Only role that can create staff, products, plans, taxes and discounts. |
| Staff | Day-to-day work: customers, subscriptions, invoices, payments. No catalog or discount setup. |
| Customer | Self-service portal: sees only their own subscriptions and invoices. |

### Success criteria (what judges will check)

1. Signup rejects weak passwords and duplicate emails; password reset email works.
2. Roles are enforced on the server, not just hidden in the UI.
3. Billing creates invoices automatically, with tax and discount filled in.
4. Running billing twice creates **zero duplicate invoices**.
5. Discounts apply on their own and stop when expired or used up.
6. Payments move invoices to Paid; outstanding and overdue are visible.
7. Finance dashboard answers: active subscriptions, revenue, amount owed, overdue invoices.
8. Lists and dashboard respond in under 2 seconds with thousands of rows.

## 2. Technical Decisions

- **Django 5 + Django templates + Bootstrap 5.** No DRF or React; all effort goes to the billing logic.
- **PostgreSQL, Redis, Celery** run through Docker Compose (web, db, redis, worker, beat). Fallback if Docker blocks anyone: SQLite and the management command.
- Django admin used for bulk CRUD (catalog, taxes, templates). Custom pages for signup, login, subscriptions, invoices, payments, dashboard, portal, create staff.
- Billing exists twice: the `run_billing` management command (fallback) and a Celery task `bill_subscription(id)` fanned out per subscription. Both rely on the same service function and the database constraint for idempotency.
- Dashboard reads a `DailyMetricSnapshot` table refreshed by Celery, plus indexed filters for drill-down.
- Money: `DecimalField(max_digits=12, decimal_places=2)` everywhere. Never floats.
- PDF invoices with `xhtml2pdf`; email through the console backend.
- Audit trail with `django-simple-history`; load test with Locust.

## 3. Project Structure

```
brightloop/
  config/            settings, urls
  accounts/          Member 1
  catalog/           Member 2  (+ pricing.py)
  subscriptions/     Member 3  (+ invoices, billing)
  payments/          Member 4  (+ dashboard, seed)
  templates/         base.html (Member 4), per-app folders
  manage.py
  README.md
```

## 4. Data Model (agreed up front, do not redesign)

### accounts

**User** (AbstractUser): `email` (unique, USERNAME\_FIELD), `name`, `role` (admin / staff / customer), `phone`, `company`.

### catalog (Member 2)

- **Product**: name, type (service / software / addon), sales\_price, cost\_price, notes, is\_active.
- **ProductVariant**: product FK, attribute (e.g. Brand), value (e.g. Odoo), extra\_price (e.g. 560).
- **Plan**: name, price, billing\_period (daily / weekly / monthly / yearly), min\_quantity, start\_date, end\_date, auto\_close (bool), closable (bool), pausable (bool), renewable (bool).
- **Tax**: name, percent, is\_active.
- **Discount**: name, type (fixed / percent), value, min\_purchase, min\_quantity, start\_date, end\_date, usage\_limit, times\_used, apply\_to (product / subscription), products M2M.

### subscriptions (Member 3)

- **QuotationTemplate**: name, plan FK, validity\_days. **QuotationTemplateLine**: template FK, product FK, variant FK (nullable), quantity.
- **Subscription**: number (SUB-0001, auto), customer FK, plan FK, start\_date, expiry\_date, payment\_terms, status (draft / quotation / confirmed / active / closed), next\_billing\_date (indexed), template FK (nullable), created\_by.
- **SubscriptionLine**: subscription FK, product FK, variant FK (nullable), quantity, unit\_price, tax FK (nullable), amount.
- **Invoice**: number (INV-0001, auto), subscription FK, customer FK, period\_start, period\_end, issue\_date, due\_date (indexed), status (draft / confirmed / paid / cancelled, indexed), subtotal, discount\_total, tax\_total, total, amount\_paid.
  - **UniqueConstraint(subscription, period\_start)** prevents double billing.
- **InvoiceLine**: invoice FK, description, quantity, unit\_price, tax\_percent, amount.

### payments (Member 4)

- **Payment**: invoice FK, method (cash / card / bank transfer / UPI / cheque), amount, payment\_date, note, recorded\_by.

### Allowed status transitions

- Subscription: Draft -> Quotation -> Confirmed -> Active -> Closed.
- Invoice: Draft -> Confirmed -> Paid. Cancel allowed from Draft or Confirmed.
- Illegal jumps raise an error inside model methods.

## 5. Shared Interfaces (agree in the first 10 minutes)

| Function | Owner | Used by |
| --- | --- | --- |
| `RoleRequiredMixin(roles=[...])` and `@role_required` | Member 1 | everyone |
| `calculate_totals(lines, discounts) -> dict(subtotal, discount_total, tax_total, total)` | Member 2 | Member 3 |
| `get_applicable_discounts(subscription, today) -> queryset` | Member 2 | Member 3 |
| `consume_discount(discount) -> bool` (atomic F() increment) | Member 2 | Member 3 |
| `generate_invoice(subscription, period_start) -> Invoice or None` | Member 3 | `run_billing`, UI |
| `record_payment(invoice, method, amount, date, note)` | Member 4 | payment view |
| `base.html` with `{% block content %}` and navbar | Member 4 | everyone |

## 6. Task Division and Timeline

Every member works in all four hours. The table shows each person's load per hour; the sections below give the detail and the checkpoint that closes each hour.

| Member | Hour 1: Foundations | Hour 2: Core features | Hour 3: Automation and scale | Hour 4: Hardening and demo |
| --- | --- | --- | --- | --- |
| Member 1: Accounts | Project, apps, custom user, password validator, signup, login, reset, Docker Compose. Push `RoleRequiredMixin` by 0:20. | Create-staff page, customer portal, role protection on every view. | Merge owner, audit history, health endpoint, throttling, role tests with three accounts. | Permission sweep, auth UI polish. Demo steps 1, 2, 8. |
| Member 2: Catalog | Catalog models and admin, pricing stubs pushed by 0:20. | `calculate_totals`, `get_applicable_discounts`, admin-only catalog pages. | `consume_discount`, discounts wired into invoices, pricing unit tests. | Catalog UI polish, pricing bug fixes. Demo step 3. |
| Member 3: Subscriptions | Subscription and invoice models, numbering, status methods, unique constraint. | Subscription and quotation pages, `generate_invoice`, invoice pages. | `run_billing`, Celery `bill_subscription` task with retries, PDF invoice, send email. | Failure log, double-run and worker-kill tests. Demo steps 4, 5. |
| Member 4: Payments | `Payment` model, `base.html` by 0:20, seed skeleton. | `record_payment` with row locking, outstanding and overdue lists, dashboard v1. | Seed 5,000 subscriptions, indexes, pagination, `DailyMetricSnapshot` task. | Locust load test, dashboard from snapshots, README. Demo steps 6, 7. |

### Hour 1 (0:00 to 1:00): Foundations

- **All four, first 10 minutes:** read Sections 4 and 5, create branches (`m1-accounts`, `m2-catalog`, `m3-subs`, `m4-payments`). No model changes after this without telling the group.
- **Member 1:** Create the project and four apps, custom `User` (unique email, `role`), set `AUTH_USER_MODEL`. Add the password validator and the signup, login and logout pages. Wire built-in password reset to the console email backend. Add `docker-compose.yml` (web, PostgreSQL, Redis). Push `RoleRequiredMixin` and `role_required` by 0:20.
- **Member 2:** Models for Product, ProductVariant, Plan, Tax and Discount, all registered in admin with filters. Push `pricing.py` stubs with the Section 5 signatures by 0:20 so Member 3 is unblocked.
- **Member 3:** Models for QuotationTemplate (+lines), Subscription (+lines) and Invoice (+lines), with the unique constraint on `(subscription, period_start)` and indexes. Add auto-numbering and the status methods (`confirm`, `activate`, `close`; invoice `confirm`, `cancel`, `mark_paid`).
- **Member 4:** `Payment` model, `base.html` with a role-aware navbar and pagination partial by 0:20, seed command skeleton, payment form wireframe.
- **Checkpoint at 1:00:** merge to main, Member 1 runs migrations, `docker compose up` works on every laptop, all models show in admin.

### Hour 2 (1:00 to 2:00): Core features

- **Member 1:** Admin-only Create staff page. Customer portal (My subscriptions, My invoices) filtered by `request.user`. Apply role protection to every view built so far; wrong role returns 403.
- **Member 2:** `calculate_totals` (line = quantity x (unit price + variant extra), tax per line, discounts applied before tax). `get_applicable_discounts` (date window, usage limit, minimum purchase or quantity, product or subscription scope). Admin-only list pages for products, plans, taxes and discounts.
- **Member 3:** Subscription create page (from a quotation template or from scratch), list with status filter, detail page with Confirm, Activate and Close buttons. Invoice list and detail. `generate_invoice(subscription, period_start)` inside `transaction.atomic()`.
- **Member 4:** `record_payment`: lock the invoice with `select_for_update`, save the payment, recompute `amount_paid`, set Paid at zero balance, reject overpayment. Outstanding and overdue lists with filters. First version of the dashboard (active subscriptions, revenue, outstanding, overdue).
- **Checkpoint at 2:00:** the full manual flow works on main: signup, plan, subscription, invoice, payment, dashboard.

### Hour 3 (2:00 to 3:00): Automation and scale

- **Member 1:** Merge owner. Add `django-simple-history` audit trail on Subscription, Invoice and Payment, a `/health` endpoint, and login throttling. Test every URL with admin, staff and customer accounts.
- **Member 2:** `consume_discount` with the atomic `F()` increment. Wire discounts into `generate_invoice`: discount lines appear, `consume_discount` runs once per applied discount, expired or used-up discounts are skipped. Unit tests for percent, fixed, expired, exhausted, and product versus subscription scope.
- **Member 3:** `run_billing` management command: select active subscriptions with `next_billing_date <= today`, bill each in its own `transaction.atomic()`, catch `IntegrityError`, advance `next_billing_date` by the plan period, auto-close expired subscriptions. Celery task `bill_subscription(id)` with beat schedule, retries and a `BillingFailure` log. PDF invoice with `xhtml2pdf` and Send by email.
- **Member 4:** Seed 5,000 customers and subscriptions with invoices and partial payments using `bulk_create`. Add indexes on status, due\_date and next\_billing\_date, and paginate at 25 per page. Add the `DailyMetricSnapshot` model and a Celery task that refreshes it.
- **Checkpoint at 3:00:** billing run twice creates zero duplicates (command and Celery), 5,000 rows loaded, every list and dashboard page timed.

### Hour 4 (3:00 to 4:00): Hardening and demo

- **3:00 to 3:30, all four:** fix the bugs the checkpoint found. Feature freeze at 3:30.
- **Member 1:** Final permission sweep across every URL. Polish login, signup and portal pages. Presents demo steps 1, 2 and 8.
- **Member 2:** Polish catalog pages, fix pricing and discount bugs from integration. Presents demo step 3.
- **Member 3:** Kill a worker mid-run and confirm no duplicate or skipped invoices. Billing failure list page, invoice print layout. Presents demo steps 4 and 5.
- **Member 4:** Locust load test on the dashboard and list pages (target p95 under 2 seconds). Dashboard reads from snapshots with date and status filters. Finish README with setup steps and demo logins. Presents demo steps 6 and 7.
- **3:30 to 3:50, all four:** rehearse the 5-minute demo twice on clean data. **3:50 to 4:00:** buffer, no new code.

## 7. Demo Script (5 minutes)

| Step | Presenter | What to show |
| --- | --- | --- |
| 1 | Member 1 | Sign up with a weak password (rejected), duplicate email (rejected), valid signup, forgot password email in console |
| 2 | Member 1 | Log in as admin, create a staff user; show a customer getting 403 on an admin URL |
| 3 | Member 2 | Create a product with the Odoo variant (+560), a monthly plan, a 10% discount with usage limit |
| 4 | Member 3 | Create a subscription from a quotation template, move Draft -> Quotation -> Confirmed -> Active |
| 5 | Member 3 | Run `run_billing`; open the invoice with tax and discount; run it again: zero new invoices |
| 6 | Member 4 | Confirm and send invoice, record a partial payment then the remainder; invoice becomes Paid |
| 7 | Member 4 | Finance dashboard on seeded data: active subs, revenue, outstanding, overdue, with filters; show response time |
| 8 | Member 1 | Customer portal showing only their own data |

## 8. Definition of Done Checklist

- [ ] Password rules enforced (server side) and unique email enforced
- [ ] Password reset email appears in console
- [ ] Admin, staff and customer restrictions verified on every URL
- [ ] Only admin can create staff, catalog items and discounts
- [ ] Product variants change the price (Odoo +560)
- [ ] Plans support all four billing periods and the closable / pausable / renewable flags
- [ ] Subscription numbers auto-generate; status flow enforced
- [ ] Invoices generated from subscriptions with tax, discount and totals
- [ ] Second `run_billing` run creates no duplicates
- [ ] Discount appears automatically and stops at expiry or usage limit
- [ ] Payments recorded with method, amount, date, note; invoice flips to Paid
- [ ] Outstanding and overdue views work
- [ ] Dashboard with filters and summary
- [ ] Pages respond in under 2 seconds on seeded data
- [ ] README with setup and demo logins

## 9. Risk Management

| Risk | Prevention |
| --- | --- |
| Migration conflicts | Only Member 1 runs `makemigrations`/`migrate` on main; others delete local DB and re-pull after merges |
| Someone blocked waiting for another module | Stub functions in Section 5 are pushed early; use Django admin for data entry |
| Running out of time | Cut in this order: Celery (keep the management command), snapshot table, real PDF, quotation template UI, custom catalog pages (use admin) |
| Late integration bugs | Merge at 1:00, 2:00 and 3:00; hand-test the full flow at each checkpoint |

**Never cut:** password rules, role enforcement, idempotent billing, automatic discounts, payment to Paid flow, dashboard.

## 10. Scale Roadmap (for README, not built in 4 hours)

- Partition invoices and payments by month; add a read replica for reporting.
- Keyset (cursor) pagination for very large lists.
- Payment gateway webhooks with idempotency keys.
- Versioned DRF API with JWT, then a React frontend over the same services.
- Sentry and Flower for monitoring workers; autoscale Celery workers with queue depth.

# Brightloop

### Subscription Management & Billing Platform

Brightloop is a web-based subscription management and billing platform designed to simplify the complete subscription lifecycle — from product and plan management to quotations, subscriptions, automated billing, invoicing, payments, and business insights.

Built with Django, Brightloop provides a centralized platform for managing customers, subscriptions, invoices, payments, taxes, discounts, and billing operations through secure role-based workflows.

---

## Overview

Managing subscriptions manually can become difficult as the number of customers, plans, invoices, and payments increases.

Brightloop provides a unified system that helps businesses:

- Manage products and subscription plans
- Manage customers and staff
- Create and manage subscriptions
- Generate invoices automatically
- Apply taxes and discounts
- Track payments and outstanding balances
- Monitor overdue invoices
- Provide customers with a dedicated portal
- Automate recurring billing operations
- Maintain audit history for important business records
- Monitor business performance through dashboards

The platform is designed with reliability, security, and scalability in mind.

---

## Key Features

### Authentication & Account Management

- Custom email-based authentication
- User registration
- Secure password validation
- Duplicate email prevention
- Password confirmation
- Password reset through email
- Login throttling against repeated failed attempts
- User profile information
- Role-based access control

### Role-Based Access Control

Brightloop supports three primary roles:

| Role | Access |
|------|--------|
| **Admin** | Full system access |
| **Staff** | Day-to-day business operations |
| **Customer** | Own subscriptions and invoices |

Access restrictions are enforced server-side to prevent unauthorized users from accessing protected functionality.

---

## Product & Plan Management

Brightloop provides centralized management of the products and subscription plans offered by a business.

### Products

Products represent the services or offerings available for subscription.

### Product Variants

Products can have multiple variants for different configurations or offerings.

### Plans

Subscription plans define pricing and billing options for customers.

### Taxes

Administrators can configure taxes that can be applied during billing.

### Discounts

Discounts can be configured with rules controlling their applicability and validity.

---

## Subscription Management

Brightloop manages the complete subscription lifecycle.

The platform supports:

- Customer subscriptions
- Subscription line items
- Subscription periods
- Plan-based subscriptions
- Subscription status tracking
- Subscription billing periods
- Customer subscription history

Subscriptions are connected to billing and invoice generation so that billing operations can be automated.

---

## Quotations

Brightloop supports quotation-based subscription workflows.

Quotation functionality allows businesses to prepare subscription offerings before they become active subscriptions.

The quotation system supports:

- Quotation templates
- Quotation line items
- Product/plan selection
- Customer-specific subscription proposals

---

## Automated Billing

Brightloop includes an automated billing architecture designed to generate invoices for subscription billing periods.

Billing can be executed through:

- Django management commands
- Background Celery tasks

The billing system uses the same underlying billing service so that manual and automated billing follow consistent business rules.

### Idempotent Billing

The billing process is designed to prevent duplicate invoices.

A subscription billing period can generate only one invoice, even if the billing operation is executed multiple times.

This protects the system from duplicate billing caused by:

- Repeated commands
- Background task retries
- Accidental repeated execution
- System interruptions

---

## Invoicing

Brightloop automatically generates invoices from subscription billing information.

Invoices contain:

- Customer information
- Subscription information
- Invoice lines
- Billing period
- Product/plan details
- Taxes
- Discounts
- Subtotals
- Final totals
- Payment status

Invoice generation is integrated with the subscription and payment workflows.

---

## Taxes & Discounts

Brightloop supports flexible billing calculations using taxes and discounts.

The billing calculation system is responsible for determining:

- Subtotal
- Applicable discounts
- Taxable amount
- Tax amount
- Final invoice total

Discounts can automatically stop applying when their validity period expires or their usage limit has been reached.

---

## Payment Management

Payments are associated with generated invoices.

The payment workflow allows the system to:

- Record payments
- Associate payments with invoices
- Update invoice payment status
- Track outstanding amounts
- Identify paid invoices
- Identify overdue invoices

Payment processing is designed around a centralized payment-recording service so that invoice status remains consistent.

---

## Customer Portal

Customers have access to a dedicated portal where they can view information belonging to their own account.

Customers can access:

- Their subscriptions
- Their invoices
- Billing information
- Payment-related information

Customer data is restricted so that users cannot access another customer's records.

---

## Dashboard & Analytics

Brightloop provides dashboard functionality for monitoring important business metrics.

The dashboard is designed to provide visibility into:

- Active subscriptions
- Revenue
- Outstanding amounts
- Overdue invoices
- Payment information

The platform also supports daily metric snapshots for maintaining historical business metrics.

---

## Audit History

Important business records can maintain historical changes through audit history.

This provides visibility into changes made to important entities such as:

- Subscriptions
- Invoices
- Payments

Audit history helps with accountability, troubleshooting, and operational tracking.

---

## Architecture

Brightloop follows a modular Django application architecture.

```text
                         ┌─────────────────────┐
                         │       Browser       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Django       │
                         │   Web Application  │
                         └──────────┬──────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             │                      │                      │
             ▼                      ▼                      ▼
      ┌─────────────┐       ┌──────────────┐       ┌──────────────┐
      │  Accounts   │       │   Catalog    │       │Subscriptions │
      │             │       │              │       │  & Billing   │
      └─────────────┘       └──────────────┘       └──────┬───────┘
                                                           │
                                                           ▼
                                                  ┌────────────────┐
                                                  │     Celery     │
                                                  │ Background Jobs│
                                                  └───────┬────────┘
                                                          │
                                                          ▼
                                                  ┌────────────────┐
                                                  │     Redis      │
                                                  │ Message Broker │
                                                  └────────────────┘

             ┌─────────────────────────────────────────────────────┐
             │                     PostgreSQL                      │
             │                    Application DB                   │
             └─────────────────────────────────────────────────────┘

                         ┌─────────────────────┐
                         │ Payments & Dashboard│
                         └─────────────────────┘
```

---

## Application Structure

```text
brightloop/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── ...
│
├── accounts/
│   ├── models.py
│   ├── forms.py
│   ├── views.py
│   ├── decorators.py
│   ├── mixins.py
│   ├── urls.py
│   └── ...
│
├── catalog/
│   ├── models.py
│   ├── pricing.py
│   └── ...
│
├── subscriptions/
│   ├── models.py
│   ├── billing.py
│   ├── invoices.py
│   └── ...
│
├── payments/
│   ├── models.py
│   ├── services.py
│   ├── dashboard.py
│   └── ...
│
├── templates/
│   ├── accounts/
│   └── ...
│
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Technology Stack

### Backend

- **Python**
- **Django 5**
- Django Templates
- Bootstrap 5

### Database

- **PostgreSQL**
- SQLite for local/fallback development

### Background Processing

- **Celery**
- **Redis**

Celery handles background operations such as automated billing tasks.

Redis acts as the message broker and supports background task processing.

### Additional Technologies

- `django-simple-history` — audit history
- `xhtml2pdf` — invoice PDF generation
- Locust — performance/load testing
- Docker & Docker Compose — development infrastructure

---

## Data Model

The major entities in Brightloop are organized around four primary domains.

### Accounts

```text
User
 ├── email
 ├── name
 ├── role
 ├── phone
 └── company
```

### Catalog

```text
Product
   │
   └── ProductVariant
          │
          └── Plan

Tax
Discount
```

### Subscriptions & Billing

```text
QuotationTemplate
        │
        └── QuotationLine

Subscription
        │
        └── SubscriptionLine
                │
                ▼
             Invoice
                │
                └── InvoiceLine
```

### Payments

```text
Invoice
   │
   └── Payment
```

---

## Security

Security is an important part of Brightloop's architecture.

### Password Security

Passwords are stored using Django's secure password hashing system.

The application applies password validation rules including:

- Minimum password length
- Common password rejection
- Numeric-only password rejection
- User attribute similarity checks

### Authentication

The platform uses email as the primary login identifier.

### Authorization

Role-based authorization is enforced on the server.

Protected operations cannot be accessed simply by modifying URLs or frontend controls.

### Login Protection

Repeated failed login attempts are restricted through login throttling.

### Customer Data Isolation

Customers are restricted to resources belonging to their own accounts.

---

## Configuration

Brightloop supports environment-based configuration for deployment.

A typical environment configuration can contain:

```env
DEBUG=True

SECRET_KEY=your-secret-key

DATABASE_URL=your-database-url

REDIS_URL=redis://localhost:6379/0
```

Sensitive values such as secret keys, database credentials, and production configuration should not be committed to version control.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Jiyo-pv/subscription-management-system.git
cd subscription-management-system
```

### 2. Create a virtual environment

#### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

#### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the environment

Create the required environment configuration and database settings.

For local development, SQLite can be used where PostgreSQL is not required.

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Create an administrator

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The application will be available at:

```text
http://127.0.0.1:8000/
```

---

## Docker

Brightloop is designed to support a containerized development environment.

The Docker Compose architecture can run the major infrastructure components together:

```text
┌──────────────────────────────────────────┐
│              Docker Compose              │
│                                          │
│  ┌──────────┐   ┌──────────┐             │
│  │  Django  │   │ PostgreSQL│             │
│  └────┬─────┘   └──────────┘             │
│       │                                   │
│       ▼                                   │
│  ┌──────────┐   ┌──────────┐             │
│  │  Celery  │──▶│  Redis   │             │
│  └──────────┘   └──────────┘             │
│                                          │
└──────────────────────────────────────────┘
```

Start the services with:

```bash
docker compose up --build
```

Stop them with:

```bash
docker compose down
```

---

## Background Jobs

Recurring and potentially time-consuming operations can be executed asynchronously using Celery.

The architecture separates business logic from task execution so that billing can be triggered from multiple sources while using the same billing service.

```text
Billing Trigger
      │
      ▼
Celery Task
      │
      ▼
Billing Service
      │
      ├── Calculate totals
      ├── Apply discounts
      ├── Apply taxes
      ├── Generate invoice
      └── Prevent duplicate invoice
```

---

## Billing Reliability

Brightloop is designed around reliable billing operations.

A key requirement is **idempotent billing**.

Running billing multiple times for the same subscription period should not create duplicate invoices.

Conceptually:

```text
First billing run
       │
       ▼
Invoice created
       │
       ▼
Subscription + billing period recorded


Second billing run
       │
       ▼
Existing invoice detected
       │
       ▼
No duplicate invoice created
```

This approach is especially important when billing operations are executed through background workers where tasks may be retried.

---

## Performance

Brightloop is designed to support growing datasets and aims to keep common lists and dashboard operations responsive even with thousands of records.

Performance considerations include:

- Database indexing
- Efficient ORM queries
- Pagination
- Reusable business services
- Background processing for long-running operations
- Redis-backed asynchronous tasks
- Load testing using Locust

The target for common lists and dashboard pages is under two seconds with thousands of rows.

---

## Invoice PDF Generation

Brightloop supports invoice PDF generation using `xhtml2pdf`.

The invoice generation workflow can produce printable invoice documents containing:

- Customer information
- Invoice details
- Subscription details
- Line items
- Discounts
- Taxes
- Total amount
- Payment status

---

## Email

The application supports Django's email framework for account-related workflows such as password reset.

During development, email can be configured to use Django's console email backend, allowing email content to be viewed directly in the development terminal.

Production deployments can replace the development backend with a transactional email provider.

---

## Django Admin

Brightloop uses Django Admin for administrative and bulk management operations where appropriate.

The admin interface can be used for managing system data while the application provides dedicated workflows for regular business operations.

---


## Health Check

Brightloop provides a lightweight health endpoint:

```text
GET /health/
```

A healthy application returns:

```json
{
    "status": "ok"
}
```

This endpoint can be used by deployment infrastructure and monitoring systems to verify that the application is running.

---

## Testing

The application can be tested using Django's testing framework.

Run the test suite with:

```bash
python manage.py test
```

Important areas for testing include:

- Authentication
- Password validation
- Duplicate email handling
- Password reset
- Role authorization
- Customer data isolation
- Billing calculations
- Invoice generation
- Billing idempotency
- Discount expiration
- Payment recording
- Dashboard calculations

---

## Load Testing

Locust can be used to evaluate application performance under simulated traffic.

Example:

```bash
locust
```

Load testing can be used to evaluate:

- Authentication endpoints
- Dashboard performance
- Subscription lists
- Invoice lists
- Customer portal
- API/request response times

---

## Current Status

### Implemented

- Email-based authentication
- Custom user model
- Role-based access control
- Password validation
- Duplicate email protection
- Password reset workflow
- Login throttling
- Customer portal foundation
- Admin/staff account management
- Health check endpoint
- Production-oriented project architecture

### In Development

- Product management
- Product variants
- Subscription plans
- Taxes
- Discounts
- Quotations
- Subscription lifecycle
- Automated billing
- Invoice generation
- Payment tracking
- Dashboard analytics
- Background billing with Celery
- Redis integration
- Audit history
- Invoice PDF generation
- Performance testing

---

## Roadmap

Future improvements can include:

- Advanced analytics
- Subscription lifecycle automation
- Payment gateway integration
- Recurring payment collection
- Email notifications
- Customer billing notifications
- Advanced reporting
- Multi-currency support
- Multi-tenant architecture
- REST API
- Webhooks
- Improved monitoring
- Production deployment automation

---

## Design Principles

Brightloop follows several core design principles:

### Security First

Authentication and authorization are enforced at the server level.

### Reliable Billing

Billing operations are designed to prevent duplicate invoice creation.

### Separation of Concerns

Business logic is separated into reusable services instead of being tightly coupled to views.

### Automation

Recurring operations such as billing can be executed asynchronously.

### Scalability

The architecture supports PostgreSQL, Redis, Celery, Docker, pagination, indexing, and load testing.

### Maintainability

The project is divided into focused Django applications:

```text
Accounts
Catalog
Subscriptions
Payments
```

Each application owns its domain while shared interfaces allow the modules to work together.

---

## Screenshots

### Authentication

_Add application screenshots here._

### Dashboard

_Add dashboard screenshot here._

### Subscription Management

_Add subscription screenshot here._

### Invoice

_Add invoice screenshot here._

### Customer Portal

_Add customer portal screenshot here._

---

## Project Goals

Brightloop aims to provide a complete subscription lifecycle in a single platform:

```text
Customer
   │
   ▼
Quotation
   │
   ▼
Subscription
   │
   ▼
Billing Period
   │
   ▼
Invoice
   │
   ▼
Payment
   │
   ▼
Dashboard & Reporting
```

The goal is to reduce manual billing work while providing businesses with a reliable and centralized view of their subscription revenue and customer billing activity.

---


## License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for the full license text.
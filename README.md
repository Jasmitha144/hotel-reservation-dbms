# Hotel Reservation & Guest Services Management System

A final DBMS PBL prototype built with **Python Flask + SQLite**. The application manages hotel rooms, guests, reservations, stays, guest services, housekeeping, invoices, payments and SQL-based reports.

## Main Modules

- Dashboard and live operational statistics
- Guest management: add, search, edit and safe-delete
- Room management: inventory, availability and status updates
- Reservation management: create, search, filter, edit and cancel
- Stay management: check-in and check-out
- Guest services: service requests, status updates and charges
- Housekeeping: task assignment, status tracking and room release
- Billing: automatic invoice generation at checkout and payment recording
- Reports: availability, guest history, occupancy, revenue, services and outstanding invoices
- Database Validation: foreign keys and business-rule checks

## Core Workflow

`Guest → Reservation → Check-in → Stay → Services / Housekeeping → Check-out → Invoice → Payment → Reports`

At checkout the application:

1. Calculates room charges from planned nights and the reservation rate plan.
2. Adds posted service charges.
3. Calculates 10% tax for this prototype.
4. Creates or updates the invoice.
5. Completes the stay and reservation.
6. Marks the room as `Cleaning`.
7. Creates a `Checkout Cleaning` housekeeping task.
8. When that task is completed, the room returns to `Available`.

## Database

SQLite database file: `database/hotel.db`

Tables:

1. `room_type`
2. `room`
3. `rate_plan`
4. `guest`
5. `reservation`
6. `stay`
7. `service_request`
8. `housekeeping_task`
9. `service_charge`
10. `invoice`
11. `payment`

The design follows the project's 3NF structure and uses primary keys, foreign keys, unique constraints, check constraints, defaults and indexes.

## Requirements

- Python 3.10+
- Flask

## Run Locally

From the project root:

```bash
pip install -r requirements.txt
python app.py
```

Open:

`http://127.0.0.1:5000/`

## Important Validation Rules

- Check-out date must be after check-in date.
- Check-in cannot be in the past for a new reservation.
- Number of guests cannot exceed room capacity.
- A room must be currently available to be booked/checked in.
- Active reservations for the same room cannot overlap.
- Service charges must be greater than zero.
- One service request cannot receive duplicate charges.
- Payments cannot exceed the outstanding invoice balance.
- Occupied rooms cannot be manually changed to another status.
- Guests with reservation history cannot be deleted; their records should be updated instead.

## GitHub

Recommended repository name:

`hotel-reservation-dbms`

Push the project files from the project root after testing:

```bash
git init
git add .
git commit -m "Final hotel reservation DBMS prototype"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

## Project Documentation

- `database/schema.sql` — table definitions and constraints
- `database/seed.sql` — sample data
- `database/queries.sql` — SQL queries used for DBMS reporting
- `docs/functional_dependencies.md` — functional dependencies
- `docs/normalization.md` — 1NF, 2NF and 3NF explanation
- `docs/erd_source.mmd` — ERD source
- `tests/test_cases.md` — final prototype test cases

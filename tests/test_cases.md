# Final Prototype Test Cases

| ID | Module | Test | Expected Result |
|---|---|---|---|
| TC01 | Guests | Add guest with unique email | Guest is inserted and displayed |
| TC02 | Guests | Add duplicate email | Database validation rejects the record |
| TC03 | Guests | Search by name/phone/email | Matching guest records are displayed |
| TC04 | Guests | Edit guest | Updated values appear in the live database |
| TC05 | Rooms | Add room with duplicate room number | Insert is rejected by UNIQUE constraint |
| TC06 | Rooms | Change non-occupied room status | New status is stored |
| TC07 | Reservations | Check-out date before/equal to check-in | Validation message; no insert |
| TC08 | Reservations | Check-in date in the past | Validation message; no insert |
| TC09 | Reservations | Guests exceed room capacity | Validation message; no insert |
| TC10 | Reservations | Overlapping active reservation | Validation message; no insert |
| TC11 | Reservations | Edit reservation | Updated booking is stored after validation |
| TC12 | Reservations | Cancel confirmed booking | Status changes to Cancelled |
| TC13 | Stays | Check in eligible reservation | Stay becomes Active; room becomes Occupied |
| TC14 | Stays/Billing | Check out active stay | Stay completes, invoice is generated/updated, room becomes Cleaning, checkout cleaning task is created |
| TC15 | Services | Add service request to active stay | Request is inserted |
| TC16 | Services | Post service charge twice for same request | Second charge is rejected |
| TC17 | Housekeeping | Complete checkout cleaning | Room changes from Cleaning to Available |
| TC18 | Billing | Pay within outstanding balance | Payment is recorded and invoice status updates |
| TC19 | Billing | Pay more than outstanding balance | Payment is rejected |
| TC20 | Reports | Open reports | SQL-based reports show live database values |
| TC21 | DB Validation | Run integrity checks | Foreign keys, dates, capacity, payment and overlap checks pass |

# Normalization to 3NF

The design is organized so that each relation stores one subject area.

1NF:
- All attributes contain atomic values.
- There are no repeating groups or multi-valued attributes in a row.

2NF:
- Each relation has a single-attribute primary key.
- Therefore, non-key attributes cannot depend on only part of a composite key.

3NF:
- Non-key attributes depend on the key of their own relation and not on another non-key attribute.
- For example, room capacity and base rate are stored in ROOM_TYPE rather than repeatedly in ROOM.
- Guest contact details are stored in GUEST rather than in RESERVATION.
- Invoice payment details are stored separately in PAYMENT rather than inside INVOICE.
- Service details are separated into SERVICE_REQUEST and SERVICE_CHARGE.

Thus, the final logical design is in 3NF under the stated functional dependencies.

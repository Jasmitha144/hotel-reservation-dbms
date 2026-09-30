# Functional Dependencies

Important functional dependencies used for normalization:

- room_type_id -> type_name, description, capacity, base_rate
- room_id -> room_number, room_type_id, floor, status
- rate_plan_id -> plan_name, description, rate, cancellation_policy
- guest_id -> first_name, last_name, phone, email, address, id_proof
- reservation_id -> guest_id, room_id, rate_plan_id, reservation_date, check_in_date, check_out_date, number_of_guests, status
- stay_id -> reservation_id, actual_check_in, actual_check_out, status
- service_request_id -> stay_id, service_type, request_date, status
- task_id -> room_id, task_date, task_type, status, assigned_to
- charge_id -> stay_id, service_request_id, amount, charge_date
- invoice_id -> stay_id, invoice_date, room_charge, service_charge, tax, total_amount, status
- payment_id -> invoice_id, payment_date, amount, payment_method, status

The implemented relations use single-attribute primary keys, so non-key attributes depend on the whole key. Entity-specific attributes are separated into their own relations to avoid repeating groups and transitive dependencies.

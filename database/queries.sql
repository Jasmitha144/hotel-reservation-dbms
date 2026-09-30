-- 1. List available rooms
SELECT r.room_number, rt.type_name, rt.capacity, rt.base_rate
FROM room r JOIN room_type rt ON r.room_type_id = rt.room_type_id
WHERE r.status = 'Available';

-- 2. Guest reservation history
SELECT g.first_name || ' ' || g.last_name AS guest_name,
       r.room_number, rs.check_in_date, rs.check_out_date, rs.status
FROM guest g JOIN reservation rs ON g.guest_id = rs.guest_id
JOIN room r ON rs.room_id = r.room_id
ORDER BY rs.check_in_date DESC;

-- 3. Occupancy / stay count by room
SELECT r.room_number, rt.type_name, r.status, COUNT(s.stay_id) AS total_stays
FROM room r JOIN room_type rt ON r.room_type_id = rt.room_type_id
LEFT JOIN reservation rs ON r.room_id = rs.room_id
LEFT JOIN stay s ON rs.reservation_id = s.reservation_id
GROUP BY r.room_id, r.room_number, rt.type_name, r.status;

-- 4. Cancellation count
SELECT COUNT(*) AS cancelled_reservations
FROM reservation WHERE status = 'Cancelled';

-- 5. Housekeeping status
SELECT r.room_number, h.task_type, h.status, h.assigned_to
FROM housekeeping_task h JOIN room r ON h.room_id = r.room_id
ORDER BY h.task_date DESC;

-- 6. Service revenue
SELECT COALESCE(SUM(amount),0) AS total_service_revenue
FROM service_charge;

-- 7. Invoiced revenue (billing value)
SELECT COALESCE(SUM(total_amount),0) AS invoiced_revenue
FROM invoice;

-- 8. Collected revenue (successful payments)
SELECT COALESCE(SUM(amount),0) AS collected_revenue
FROM payment WHERE status='Successful';

-- 9. Outstanding balances
SELECT i.invoice_id, i.total_amount,
       COALESCE(SUM(p.amount),0) AS paid,
       i.total_amount - COALESCE(SUM(p.amount),0) AS outstanding
FROM invoice i
LEFT JOIN payment p ON i.invoice_id = p.invoice_id AND p.status='Successful'
GROUP BY i.invoice_id, i.total_amount
HAVING outstanding > 0;

-- 10. Revenue by payment method
SELECT payment_method, SUM(amount) AS total_collected
FROM payment WHERE status='Successful'
GROUP BY payment_method;

-- 11. Service revenue by type
SELECT sr.service_type, SUM(sc.amount) AS revenue
FROM service_charge sc JOIN service_request sr
ON sc.service_request_id = sr.service_request_id
GROUP BY sr.service_type ORDER BY revenue DESC;

-- 12. Available room report
SELECT r.room_number, rt.type_name, rt.capacity, rt.base_rate
FROM room r JOIN room_type rt ON r.room_type_id=rt.room_type_id
WHERE r.status='Available' ORDER BY r.room_number;

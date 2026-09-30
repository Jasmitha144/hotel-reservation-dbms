INSERT OR IGNORE INTO room_type(type_name, description, capacity, base_rate) VALUES
('Standard', 'Comfortable standard room', 2, 2500),
('Deluxe', 'Spacious deluxe room', 3, 4000),
('Suite', 'Premium suite with living area', 4, 6500);

INSERT OR IGNORE INTO rate_plan(plan_name, description, rate, cancellation_policy) VALUES
('Standard Flexible', 'Flexible booking rate', 2500, 'Free cancellation up to 24 hours before check-in'),
('Deluxe Flexible', 'Flexible deluxe rate', 4000, 'Free cancellation up to 24 hours before check-in'),
('Suite Premium', 'Premium suite rate', 6500, 'Cancellation subject to hotel policy');

INSERT OR IGNORE INTO guest(first_name,last_name,phone,email,address,id_proof) VALUES
('Aarav','Sharma','9876543210','aarav.sharma@example.com','Hyderabad','AADHAR-1001'),
('Meera','Reddy','9876543211','meera.reddy@example.com','Bengaluru','AADHAR-1002'),
('Rahul','Verma','9876543212','rahul.verma@example.com','Mumbai','AADHAR-1003'),
('Ananya','Patel','9876543213','ananya.patel@example.com','Chennai','AADHAR-1004'),
('Vikram','Singh','9876543214','vikram.singh@example.com','Delhi','AADHAR-1005');

INSERT OR IGNORE INTO room(room_number,room_type_id,floor,status) VALUES
('101',1,1,'Available'),
('102',1,1,'Available'),
('201',2,2,'Available'),
('202',2,2,'Available'),
('301',3,3,'Available'),
('302',3,3,'Maintenance');

INSERT OR IGNORE INTO reservation(guest_id,room_id,rate_plan_id,check_in_date,check_out_date,number_of_guests,status)
VALUES
(1,1,1,date('now','+1 day'),date('now','+3 day'),2,'Confirmed'),
(2,3,2,date('now','+2 day'),date('now','+5 day'),2,'Confirmed'),
(3,4,2,date('now','-2 day'),date('now','+1 day'),2,'Confirmed');

INSERT OR IGNORE INTO stay(reservation_id,actual_check_in,status)
VALUES (3,datetime('now','-2 day'),'Active');

INSERT OR IGNORE INTO service_request(stay_id,service_type,status)
VALUES (1,'Room Service','Completed'),
       (1,'Laundry','Completed');

INSERT OR IGNORE INTO service_charge(stay_id,service_request_id,amount)
VALUES (1,1,650),(1,2,300);

INSERT OR IGNORE INTO invoice(stay_id,room_charge,service_charge,tax,total_amount,status)
VALUES (1,7500,950,845,9295,'Partially Paid');

INSERT OR IGNORE INTO payment(invoice_id,amount,payment_method,status)
VALUES (1,5000,'UPI','Successful');

INSERT OR IGNORE INTO housekeeping_task(room_id,task_date,task_type,status,assigned_to)
VALUES
(1,date('now'),'Deep Cleaning','Pending','Housekeeping A'),
(3,date('now'),'Room Cleaning','In Progress','Housekeeping B'),
(4,date('now'),'Checkout Cleaning','Completed','Housekeeping C');

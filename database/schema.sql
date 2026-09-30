PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS room_type (
    room_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE,
    description TEXT,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    base_rate REAL NOT NULL CHECK (base_rate >= 0)
);

CREATE TABLE IF NOT EXISTS room (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL UNIQUE,
    room_type_id INTEGER NOT NULL,
    floor INTEGER NOT NULL CHECK (floor >= 0),
    status TEXT NOT NULL DEFAULT 'Available'
        CHECK (status IN ('Available','Occupied','Maintenance','Cleaning')),
    FOREIGN KEY (room_type_id) REFERENCES room_type(room_type_id)
);

CREATE TABLE IF NOT EXISTS rate_plan (
    rate_plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_name TEXT NOT NULL UNIQUE,
    description TEXT,
    rate REAL NOT NULL CHECK (rate >= 0),
    cancellation_policy TEXT
);

CREATE TABLE IF NOT EXISTS guest (
    guest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    address TEXT,
    id_proof TEXT
);

CREATE TABLE IF NOT EXISTS reservation (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guest_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    rate_plan_id INTEGER NOT NULL,
    reservation_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    check_in_date TEXT NOT NULL,
    check_out_date TEXT NOT NULL,
    number_of_guests INTEGER NOT NULL CHECK (number_of_guests > 0),
    status TEXT NOT NULL DEFAULT 'Confirmed'
        CHECK (status IN ('Pending','Confirmed','Cancelled','Completed')),
    FOREIGN KEY (guest_id) REFERENCES guest(guest_id),
    FOREIGN KEY (room_id) REFERENCES room(room_id),
    FOREIGN KEY (rate_plan_id) REFERENCES rate_plan(rate_plan_id),
    CHECK (date(check_out_date) > date(check_in_date))
);

CREATE TABLE IF NOT EXISTS stay (
    stay_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reservation_id INTEGER NOT NULL UNIQUE,
    actual_check_in TEXT,
    actual_check_out TEXT,
    status TEXT NOT NULL DEFAULT 'Active'
        CHECK (status IN ('Active','Completed')),
    FOREIGN KEY (reservation_id) REFERENCES reservation(reservation_id)
);

CREATE TABLE IF NOT EXISTS service_request (
    service_request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stay_id INTEGER NOT NULL,
    service_type TEXT NOT NULL,
    request_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'Requested'
        CHECK (status IN ('Requested','In Progress','Completed','Cancelled')),
    FOREIGN KEY (stay_id) REFERENCES stay(stay_id)
);

CREATE TABLE IF NOT EXISTS housekeeping_task (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    task_date TEXT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending','In Progress','Completed')),
    assigned_to TEXT,
    FOREIGN KEY (room_id) REFERENCES room(room_id)
);

CREATE TABLE IF NOT EXISTS service_charge (
    charge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stay_id INTEGER NOT NULL,
    service_request_id INTEGER,
    amount REAL NOT NULL CHECK (amount >= 0),
    charge_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY (stay_id) REFERENCES stay(stay_id),
    FOREIGN KEY (service_request_id) REFERENCES service_request(service_request_id)
);

CREATE TABLE IF NOT EXISTS invoice (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    stay_id INTEGER NOT NULL UNIQUE,
    invoice_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    room_charge REAL NOT NULL DEFAULT 0 CHECK (room_charge >= 0),
    service_charge REAL NOT NULL DEFAULT 0 CHECK (service_charge >= 0),
    tax REAL NOT NULL DEFAULT 0 CHECK (tax >= 0),
    total_amount REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    status TEXT NOT NULL DEFAULT 'Unpaid'
        CHECK (status IN ('Unpaid','Partially Paid','Paid')),
    FOREIGN KEY (stay_id) REFERENCES stay(stay_id)
);

CREATE TABLE IF NOT EXISTS payment (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    amount REAL NOT NULL CHECK (amount > 0),
    payment_method TEXT NOT NULL
        CHECK (payment_method IN ('Cash','Card','UPI','Bank Transfer')),
    status TEXT NOT NULL DEFAULT 'Successful'
        CHECK (status IN ('Successful','Failed')),
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id)
);

CREATE INDEX IF NOT EXISTS idx_reservation_dates ON reservation(room_id, check_in_date, check_out_date);
CREATE INDEX IF NOT EXISTS idx_service_stay ON service_request(stay_id);
CREATE INDEX IF NOT EXISTS idx_payment_invoice ON payment(invoice_id);

-- One charge per service request in the prototype.
CREATE UNIQUE INDEX IF NOT EXISTS idx_service_charge_request_unique
ON service_charge(service_request_id) WHERE service_request_id IS NOT NULL;

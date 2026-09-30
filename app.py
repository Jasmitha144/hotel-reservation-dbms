from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3, os
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "hotel.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")
SEED_PATH = os.path.join(BASE_DIR, "database", "seed.sql")

app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.secret_key = "hotel-pbl-demo-key"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    if conn.execute("SELECT COUNT(*) FROM guest").fetchone()[0] == 0:
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    # Keep one service charge per service request in the prototype.
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_service_charge_request_unique "
                 "ON service_charge(service_request_id) WHERE service_request_id IS NOT NULL")
    conn.commit()
    conn.close()


def rows(sql, params=()):
    conn = get_db()
    result = conn.execute(sql, params).fetchall()
    conn.close()
    return result


def scalar(sql, params=()):
    conn = get_db()
    value = conn.execute(sql, params).fetchone()[0]
    conn.close()
    return value


def reservation_conflict(room_id, check_in, check_out, exclude_id=None):
    sql = """SELECT COUNT(*) FROM reservation
             WHERE room_id = ?
             AND status IN ('Pending','Confirmed')
             AND date(check_in_date) < date(?)
             AND date(check_out_date) > date(?)"""
    params = [room_id, check_out, check_in]
    if exclude_id:
        sql += " AND reservation_id <> ?"
        params.append(exclude_id)
    return scalar(sql, params) > 0


def room_capacity(room_id):
    return scalar("""SELECT rt.capacity FROM room r
                     JOIN room_type rt ON r.room_type_id=rt.room_type_id
                     WHERE r.room_id=?""", (room_id,))


def room_available_for_booking(room_id):
    status = scalar("SELECT status FROM room WHERE room_id=?", (room_id,))
    return status == "Available"


def calculate_invoice(conn, stay_id):
    """Create/update the invoice for a completed stay and return invoice id."""
    stay = conn.execute("""SELECT s.stay_id, s.reservation_id, rs.room_id,
                                 rs.check_in_date, rs.check_out_date,
                                 rp.rate, r.room_number
                          FROM stay s
                          JOIN reservation rs ON s.reservation_id=rs.reservation_id
                          JOIN rate_plan rp ON rs.rate_plan_id=rp.rate_plan_id
                          JOIN room r ON rs.room_id=r.room_id
                          WHERE s.stay_id=?""", (stay_id,)).fetchone()
    if not stay:
        raise ValueError("Stay not found.")

    nights = max(1, (date.fromisoformat(stay["check_out_date"]) -
                       date.fromisoformat(stay["check_in_date"])).days)
    room_charge = nights * float(stay["rate"])
    service_charge = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM service_charge WHERE stay_id=?",
        (stay_id,)
    ).fetchone()[0]
    subtotal = room_charge + service_charge
    tax = round(subtotal * 0.10, 2)
    total = round(subtotal + tax, 2)

    existing = conn.execute("SELECT invoice_id FROM invoice WHERE stay_id=?", (stay_id,)).fetchone()
    if existing:
        invoice_id = existing["invoice_id"]
        paid = conn.execute("""SELECT COALESCE(SUM(amount),0) FROM payment
                               WHERE invoice_id=? AND status='Successful'""", (invoice_id,)).fetchone()[0]
        status = "Paid" if paid >= total else ("Partially Paid" if paid > 0 else "Unpaid")
        conn.execute("""UPDATE invoice SET room_charge=?, service_charge=?, tax=?, total_amount=?, status=?
                       WHERE invoice_id=?""", (room_charge, service_charge, tax, total, status, invoice_id))
    else:
        cur = conn.execute("""INSERT INTO invoice
            (stay_id, room_charge, service_charge, tax, total_amount, status)
            VALUES(?,?,?,?,?,'Unpaid')""",
            (stay_id, room_charge, service_charge, tax, total))
        invoice_id = cur.lastrowid
    return invoice_id


@app.context_processor
def common():
    return {"today": date.today().isoformat()}


@app.route("/")
def dashboard():
    stats = {
        "guests": scalar("SELECT COUNT(*) FROM guest"),
        "rooms": scalar("SELECT COUNT(*) FROM room"),
        "available": scalar("SELECT COUNT(*) FROM room WHERE status='Available'"),
        "occupied": scalar("SELECT COUNT(*) FROM room WHERE status='Occupied'"),
        "reservations": scalar("SELECT COUNT(*) FROM reservation WHERE status IN ('Pending','Confirmed')"),
        "active_stays": scalar("SELECT COUNT(*) FROM stay WHERE status='Active'"),
        "housekeeping": scalar("SELECT COUNT(*) FROM housekeeping_task WHERE status IN ('Pending','In Progress')"),
        "outstanding": scalar("""SELECT COUNT(*) FROM invoice i
            WHERE i.total_amount > COALESCE((SELECT SUM(p.amount) FROM payment p
            WHERE p.invoice_id=i.invoice_id AND p.status='Successful'),0)"""),
        "revenue": scalar("SELECT COALESCE(SUM(amount),0) FROM payment WHERE status='Successful'")
    }
    recent = rows("""SELECT rs.reservation_id,
                     g.first_name || ' ' || g.last_name AS guest_name,
                     r.room_number, rs.check_in_date, rs.check_out_date, rs.status
                     FROM reservation rs
                     JOIN guest g ON rs.guest_id=g.guest_id
                     JOIN room r ON rs.room_id=r.room_id
                     ORDER BY rs.reservation_id DESC LIMIT 8""")
    return render_template("dashboard.html", stats=stats, recent=recent)


@app.route("/guests", methods=["GET", "POST"])
def guests():
    if request.method == "POST":
        f = request.form
        try:
            conn = get_db()
            conn.execute("""INSERT INTO guest(first_name,last_name,phone,email,address,id_proof)
                            VALUES(?,?,?,?,?,?)""",
                         (f["first_name"].strip(), f["last_name"].strip(), f["phone"].strip(),
                          f["email"].strip().lower(), f.get("address", "").strip(), f.get("id_proof", "").strip()))
            conn.commit(); conn.close()
            flash("Guest added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("Email already exists or input violates a database rule.", "danger")
        return redirect(url_for("guests"))
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        data = rows("""SELECT * FROM guest
                       WHERE first_name LIKE ? OR last_name LIKE ? OR phone LIKE ? OR email LIKE ?
                       ORDER BY guest_id DESC""", (like, like, like, like))
    else:
        data = rows("SELECT * FROM guest ORDER BY guest_id DESC")
    return render_template("guests.html", guests=data, q=q)


@app.post("/guests/<int:gid>/edit")
def edit_guest(gid):
    f = request.form
    try:
        conn = get_db()
        conn.execute("""UPDATE guest SET first_name=?, last_name=?, phone=?, email=?, address=?, id_proof=?
                       WHERE guest_id=?""",
                     (f["first_name"].strip(), f["last_name"].strip(), f["phone"].strip(),
                      f["email"].strip().lower(), f.get("address", "").strip(), f.get("id_proof", "").strip(), gid))
        if conn.total_changes == 0:
            raise ValueError("Guest not found.")
        conn.commit(); conn.close()
        flash("Guest updated successfully.", "success")
    except (ValueError, sqlite3.IntegrityError):
        flash("Could not update guest. Check the email and required fields.", "danger")
    return redirect(url_for("guests"))


@app.post("/guests/<int:gid>/delete")
def delete_guest(gid):
    conn = get_db()
    linked = conn.execute("SELECT COUNT(*) FROM reservation WHERE guest_id=?", (gid,)).fetchone()[0]
    if linked:
        conn.close()
        flash("Guest cannot be deleted because reservation history exists. Update the record instead.", "danger")
        return redirect(url_for("guests"))
    conn.execute("DELETE FROM guest WHERE guest_id=?", (gid,))
    conn.commit(); conn.close()
    flash("Guest deleted.", "success")
    return redirect(url_for("guests"))


@app.route("/rooms")
def rooms():
    data = rows("""SELECT r.*, rt.type_name, rt.capacity, rt.base_rate
                 FROM room r JOIN room_type rt ON r.room_type_id=rt.room_type_id
                 ORDER BY r.room_number""")
    types = rows("SELECT * FROM room_type ORDER BY type_name")
    return render_template("rooms.html", rooms=data, types=types)


@app.post("/rooms/add")
def add_room():
    f = request.form
    try:
        conn = get_db()
        conn.execute("INSERT INTO room(room_number,room_type_id,floor,status) VALUES(?,?,?,?)",
                     (f["room_number"].strip(), f["room_type_id"], f["floor"], f["status"]))
        conn.commit(); conn.close()
        flash("Room added.", "success")
    except sqlite3.IntegrityError:
        flash("Room number must be unique and valid.", "danger")
    return redirect(url_for("rooms"))


@app.post("/rooms/<int:room_id>/status")
def update_room_status(room_id):
    status = request.form.get("status")
    allowed = {"Available", "Maintenance", "Cleaning"}
    if status not in allowed:
        flash("Invalid room status.", "danger")
        return redirect(url_for("rooms"))
    conn = get_db()
    current = conn.execute("SELECT status FROM room WHERE room_id=?", (room_id,)).fetchone()
    if not current:
        conn.close(); flash("Room not found.", "danger"); return redirect(url_for("rooms"))
    if current["status"] == "Occupied":
        conn.close(); flash("Occupied rooms cannot be manually changed. Check out the active stay first.", "danger")
        return redirect(url_for("rooms"))
    conn.execute("UPDATE room SET status=? WHERE room_id=?", (status, room_id))
    conn.commit(); conn.close()
    flash("Room status updated.", "success")
    return redirect(url_for("rooms"))


@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if request.method == "POST":
        f = request.form
        ci, co = f["check_in_date"], f["check_out_date"]
        try:
            ci_date, co_date = date.fromisoformat(ci), date.fromisoformat(co)
            if co_date <= ci_date:
                raise ValueError("Check-out must be after check-in.")
            if ci_date < date.today():
                raise ValueError("Check-in date cannot be in the past.")
            guests_count = int(f["number_of_guests"])
            if guests_count <= 0:
                raise ValueError("Number of guests must be greater than zero.")
            cap = room_capacity(f["room_id"])
            if guests_count > cap:
                raise ValueError(f"Selected room capacity is {cap}.")
            if not room_available_for_booking(f["room_id"]):
                raise ValueError("Selected room is not currently available for booking.")
            if reservation_conflict(f["room_id"], ci, co):
                raise ValueError("This room already has an overlapping reservation.")
            conn = get_db()
            conn.execute("""INSERT INTO reservation
                (guest_id,room_id,rate_plan_id,check_in_date,check_out_date,number_of_guests,status)
                VALUES(?,?,?,?,?,?,?)""",
                (f["guest_id"], f["room_id"], f["rate_plan_id"], ci, co, guests_count, f["status"]))
            conn.commit(); conn.close()
            flash("Reservation created successfully.", "success")
        except (ValueError, sqlite3.IntegrityError) as e:
            flash(str(e), "danger")
        return redirect(url_for("reservations"))

    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()
    sql = """SELECT rs.*, g.first_name || ' ' || g.last_name AS guest_name,
                         r.room_number, rp.plan_name
              FROM reservation rs
              JOIN guest g ON rs.guest_id=g.guest_id
              JOIN room r ON rs.room_id=r.room_id
              JOIN rate_plan rp ON rs.rate_plan_id=rp.rate_plan_id
              WHERE 1=1"""
    params = []
    if q:
        sql += " AND (g.first_name || ' ' || g.last_name LIKE ? OR r.room_number LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if status_filter:
        sql += " AND rs.status=?"
        params.append(status_filter)
    sql += " ORDER BY rs.reservation_id DESC"
    reservation_data = rows(sql, params)
    guest_data = rows("SELECT guest_id,first_name,last_name FROM guest ORDER BY first_name")
    room_data = rows("""SELECT r.room_id,r.room_number,rt.capacity
                  FROM room r JOIN room_type rt ON r.room_type_id=rt.room_type_id
                  WHERE r.status='Available' ORDER BY r.room_number""")
    plans = rows("SELECT * FROM rate_plan ORDER BY plan_name")
    return render_template("reservations.html", reservations=reservation_data, guests=guest_data,
                           rooms=room_data, plans=plans, q=q, status_filter=status_filter)


@app.post("/reservations/<int:rid>/edit")
def edit_reservation(rid):
    f = request.form
    try:
        ci, co = f["check_in_date"], f["check_out_date"]
        if date.fromisoformat(co) <= date.fromisoformat(ci):
            raise ValueError("Check-out must be after check-in.")
        if date.fromisoformat(ci) < date.today():
            raise ValueError("Check-in date cannot be in the past.")
        guests_count = int(f["number_of_guests"])
        cap = room_capacity(f["room_id"])
        if guests_count <= 0 or guests_count > cap:
            raise ValueError(f"Number of guests must be between 1 and the selected room capacity ({cap}).")
        if not room_available_for_booking(f["room_id"]):
            raise ValueError("Selected room is not currently available.")
        if reservation_conflict(f["room_id"], ci, co, rid):
            raise ValueError("The updated dates overlap another reservation for this room.")
        conn = get_db()
        existing = conn.execute("SELECT status FROM reservation WHERE reservation_id=?", (rid,)).fetchone()
        if not existing:
            raise ValueError("Reservation not found.")
        if existing["status"] == "Completed":
            raise ValueError("Completed reservations cannot be edited.")
        conn.execute("""UPDATE reservation SET guest_id=?, room_id=?, rate_plan_id=?,
                       check_in_date=?, check_out_date=?, number_of_guests=?, status=?
                       WHERE reservation_id=?""",
                     (f["guest_id"], f["room_id"], f["rate_plan_id"], ci, co,
                      guests_count, f["status"], rid))
        conn.commit(); conn.close()
        flash("Reservation updated successfully.", "success")
    except (ValueError, sqlite3.IntegrityError) as e:
        flash(str(e), "danger")
    return redirect(url_for("reservations"))


@app.post("/reservations/<int:rid>/cancel")
def cancel_reservation(rid):
    conn = get_db()
    conn.execute("UPDATE reservation SET status='Cancelled' WHERE reservation_id=? AND status IN ('Pending','Confirmed')", (rid,))
    conn.commit(); conn.close()
    flash("Reservation cancelled.", "success")
    return redirect(url_for("reservations"))


@app.route("/stays")
def stays():
    data = rows("""SELECT s.*, rs.check_in_date, rs.check_out_date, r.room_number,
                 g.first_name || ' ' || g.last_name AS guest_name
                 FROM stay s
                 JOIN reservation rs ON s.reservation_id=rs.reservation_id
                 JOIN room r ON rs.room_id=r.room_id
                 JOIN guest g ON rs.guest_id=g.guest_id
                 ORDER BY s.stay_id DESC""")
    pending = rows("""SELECT rs.reservation_id, g.first_name || ' ' || g.last_name AS guest_name,
                    r.room_number, rs.check_in_date, rs.check_out_date
                    FROM reservation rs
                    JOIN guest g ON rs.guest_id=g.guest_id
                    JOIN room r ON rs.room_id=r.room_id
                    WHERE rs.status='Confirmed'
                    AND date(rs.check_in_date) <= date('now')
                    AND NOT EXISTS (SELECT 1 FROM stay s WHERE s.reservation_id=rs.reservation_id)
                    ORDER BY rs.check_in_date""")
    return render_template("stays.html", stays=data, pending=pending)


@app.post("/stays/checkin/<int:rid>")
def checkin(rid):
    try:
        conn = get_db()
        rs = conn.execute("SELECT * FROM reservation WHERE reservation_id=? AND status='Confirmed'", (rid,)).fetchone()
        if not rs:
            raise ValueError("Reservation is not available for check-in.")
        if date.fromisoformat(rs["check_in_date"]) > date.today():
            raise ValueError("Check-in is only available on or after the reservation check-in date.")
        if conn.execute("SELECT 1 FROM stay WHERE reservation_id=?", (rid,)).fetchone():
            raise ValueError("Guest is already checked in.")
        if conn.execute("SELECT status FROM room WHERE room_id=?", (rs["room_id"],)).fetchone()[0] != "Available":
            raise ValueError("Room is not available for check-in.")
        conn.execute("INSERT INTO stay(reservation_id,actual_check_in,status) VALUES(?,datetime('now'),'Active')", (rid,))
        conn.execute("UPDATE room SET status='Occupied' WHERE room_id=?", (rs["room_id"],))
        conn.commit(); conn.close()
        flash("Guest checked in and room marked Occupied.", "success")
    except (ValueError, sqlite3.IntegrityError) as e:
        flash(str(e), "danger")
    return redirect(url_for("stays"))


@app.post("/stays/checkout/<int:sid>")
def checkout(sid):
    conn = get_db()
    try:
        stay = conn.execute("""SELECT s.*,rs.room_id FROM stay s JOIN reservation rs ON s.reservation_id=rs.reservation_id
                             WHERE s.stay_id=? AND s.status='Active'""", (sid,)).fetchone()
        if not stay:
            raise ValueError("Active stay not found.")
        invoice_id = calculate_invoice(conn, sid)
        conn.execute("UPDATE stay SET actual_check_out=datetime('now'),status='Completed' WHERE stay_id=?", (sid,))
        conn.execute("UPDATE reservation SET status='Completed' WHERE reservation_id=?", (stay["reservation_id"],))
        conn.execute("UPDATE room SET status='Cleaning' WHERE room_id=?", (stay["room_id"],))
        conn.execute("""INSERT INTO housekeeping_task(room_id,task_date,task_type,status,assigned_to)
                       VALUES(?,date('now'),'Checkout Cleaning','Pending',NULL)""", (stay["room_id"],))
        conn.commit(); conn.close()
        flash(f"Guest checked out. Invoice #{invoice_id} generated and room marked for cleaning.", "success")
    except (ValueError, sqlite3.IntegrityError) as e:
        conn.rollback(); conn.close()
        flash(str(e), "danger")
    return redirect(url_for("stays"))


@app.route("/services", methods=["GET", "POST"])
def services():
    if request.method == "POST":
        f = request.form
        try:
            conn = get_db()
            st = conn.execute("SELECT 1 FROM stay WHERE stay_id=? AND status='Active'", (f["stay_id"],)).fetchone()
            if not st:
                raise ValueError("Only an active stay can receive a service request.")
            conn.execute("INSERT INTO service_request(stay_id,service_type,status) VALUES(?,?,?)",
                         (f["stay_id"], f["service_type"].strip(), f["status"]))
            conn.commit(); conn.close()
            flash("Service request added.", "success")
        except (ValueError, sqlite3.IntegrityError) as e:
            flash(str(e), "danger")
        return redirect(url_for("services"))
    service_data = rows("""SELECT sr.*, g.first_name || ' ' || g.last_name AS guest_name, r.room_number,
                          (SELECT sc.amount FROM service_charge sc WHERE sc.service_request_id=sr.service_request_id) AS charge
                     FROM service_request sr
                     JOIN stay s ON sr.stay_id=s.stay_id
                     JOIN reservation rs ON s.reservation_id=rs.reservation_id
                     JOIN guest g ON rs.guest_id=g.guest_id
                     JOIN room r ON rs.room_id=r.room_id
                     ORDER BY sr.service_request_id DESC""")
    stay_data = rows("""SELECT s.stay_id,g.first_name || ' ' || g.last_name AS guest_name,r.room_number
                  FROM stay s JOIN reservation rs ON s.reservation_id=rs.reservation_id
                  JOIN guest g ON rs.guest_id=g.guest_id
                  JOIN room r ON rs.room_id=r.room_id WHERE s.status='Active'""")
    return render_template("services.html", services=service_data, stays=stay_data)


@app.post("/services/<int:srid>/status")
def update_service_status(srid):
    status = request.form.get("status")
    if status not in {"Requested", "In Progress", "Completed", "Cancelled"}:
        flash("Invalid service status.", "danger")
        return redirect(url_for("services"))
    conn = get_db()
    conn.execute("UPDATE service_request SET status=? WHERE service_request_id=?", (status, srid))
    conn.commit(); conn.close()
    flash("Service status updated.", "success")
    return redirect(url_for("services"))


@app.post("/services/<int:srid>/charge")
def service_charge(srid):
    f = request.form
    try:
        amount = float(f["amount"])
        if amount <= 0:
            raise ValueError("Service charge must be greater than zero.")
        conn = get_db()
        sr = conn.execute("SELECT stay_id FROM service_request WHERE service_request_id=?", (srid,)).fetchone()
        if not sr:
            raise ValueError("Service request not found.")
        if conn.execute("SELECT 1 FROM service_charge WHERE service_request_id=?", (srid,)).fetchone():
            raise ValueError("A charge has already been posted for this service request.")
        conn.execute("INSERT INTO service_charge(stay_id,service_request_id,amount) VALUES(?,?,?)",
                     (sr["stay_id"], srid, amount))
        conn.execute("UPDATE service_request SET status='Completed' WHERE service_request_id=?", (srid,))
        conn.commit(); conn.close()
        flash("Service charge posted and request marked Completed.", "success")
    except (ValueError, sqlite3.IntegrityError) as e:
        flash(str(e), "danger")
    return redirect(url_for("services"))


@app.route("/housekeeping", methods=["GET", "POST"])
def housekeeping():
    if request.method == "POST":
        f = request.form
        try:
            conn = get_db()
            conn.execute("""INSERT INTO housekeeping_task(room_id,task_date,task_type,status,assigned_to)
                            VALUES(?,?,?,?,?)""",
                         (f["room_id"], f["task_date"], f["task_type"].strip(), f["status"], f.get("assigned_to", "").strip()))
            conn.commit(); conn.close()
            flash("Housekeeping task added.", "success")
        except sqlite3.IntegrityError as e:
            flash(str(e), "danger")
        return redirect(url_for("housekeeping"))
    tasks = rows("""SELECT h.*,r.room_number FROM housekeeping_task h JOIN room r ON h.room_id=r.room_id
                  ORDER BY h.task_id DESC""")
    rooms_data = rows("SELECT room_id,room_number,status FROM room ORDER BY room_number")
    return render_template("housekeeping.html", tasks=tasks, rooms=rooms_data)


@app.post("/housekeeping/<int:tid>/status")
def housekeeping_status(tid):
    status = request.form.get("status")
    if status not in {"Pending", "In Progress", "Completed"}:
        flash("Invalid housekeeping status.", "danger")
        return redirect(url_for("housekeeping"))
    conn = get_db()
    task = conn.execute("SELECT room_id FROM housekeeping_task WHERE task_id=?", (tid,)).fetchone()
    if not task:
        conn.close(); flash("Housekeeping task not found.", "danger"); return redirect(url_for("housekeeping"))
    conn.execute("UPDATE housekeeping_task SET status=? WHERE task_id=?", (status, tid))
    if status == "Completed":
        active = conn.execute("""SELECT 1 FROM stay s JOIN reservation rs ON s.reservation_id=rs.reservation_id
                                WHERE rs.room_id=? AND s.status='Active'""", (task["room_id"],)).fetchone()
        if not active:
            conn.execute("UPDATE room SET status='Available' WHERE room_id=? AND status='Cleaning'", (task["room_id"],))
    conn.commit(); conn.close()
    flash("Housekeeping task updated." + (" Room is now Available." if status == "Completed" else ""), "success")
    return redirect(url_for("housekeeping"))


@app.route("/billing", methods=["GET", "POST"])
def billing():
    if request.method == "POST":
        f = request.form
        try:
            amount = float(f["amount"])
            conn = get_db()
            inv = conn.execute("SELECT * FROM invoice WHERE invoice_id=?", (f["invoice_id"],)).fetchone()
            paid = conn.execute("""SELECT COALESCE(SUM(amount),0) FROM payment
                                 WHERE invoice_id=? AND status='Successful'""", (f["invoice_id"],)).fetchone()[0]
            if not inv:
                raise ValueError("Invoice not found.")
            if amount <= 0:
                raise ValueError("Payment must be greater than zero.")
            outstanding = inv["total_amount"] - paid
            if amount > outstanding + 0.00001:
                raise ValueError("Payment exceeds outstanding invoice balance.")
            conn.execute("""INSERT INTO payment(invoice_id,amount,payment_method,status)
                            VALUES(?,?,?,'Successful')""", (f["invoice_id"], amount, f["payment_method"]))
            new_paid = paid + amount
            status = 'Paid' if new_paid >= inv["total_amount"] - 0.00001 else 'Partially Paid'
            conn.execute("UPDATE invoice SET status=? WHERE invoice_id=?", (status, f["invoice_id"]))
            conn.commit(); conn.close()
            flash("Payment recorded successfully.", "success")
        except (ValueError, sqlite3.IntegrityError) as e:
            try:
                conn.close()
            except Exception:
                pass
            flash(str(e), "danger")
        return redirect(url_for("billing"))
    invoices = rows("""SELECT i.*,g.first_name || ' ' || g.last_name AS guest_name,
                     r.room_number,
                     COALESCE((SELECT SUM(p.amount) FROM payment p WHERE p.invoice_id=i.invoice_id AND p.status='Successful'),0) AS paid
                     FROM invoice i
                     JOIN stay s ON i.stay_id=s.stay_id
                     JOIN reservation rs ON s.reservation_id=rs.reservation_id
                     JOIN guest g ON rs.guest_id=g.guest_id
                     JOIN room r ON rs.room_id=r.room_id
                     ORDER BY i.invoice_id DESC""")
    return render_template("billing.html", invoices=invoices)


@app.route("/reports")
def reports():
    occupancy = rows("""SELECT r.room_number,rt.type_name,r.status,COUNT(s.stay_id) AS total_stays
                      FROM room r JOIN room_type rt ON r.room_type_id=rt.room_type_id
                      LEFT JOIN reservation rs ON r.room_id=rs.room_id
                      LEFT JOIN stay s ON rs.reservation_id=s.reservation_id
                      GROUP BY r.room_id,r.room_number,rt.type_name,r.status
                      ORDER BY r.room_number""")
    revenue = scalar("SELECT COALESCE(SUM(amount),0) FROM payment WHERE status='Successful'")
    invoiced_revenue = scalar("SELECT COALESCE(SUM(total_amount),0) FROM invoice")
    service_rev = scalar("SELECT COALESCE(SUM(amount),0) FROM service_charge")
    cancellations = scalar("SELECT COUNT(*) FROM reservation WHERE status='Cancelled'")
    available_rooms = rows("""SELECT r.room_number,rt.type_name,rt.capacity,rt.base_rate
                             FROM room r JOIN room_type rt ON r.room_type_id=rt.room_type_id
                             WHERE r.status='Available' ORDER BY r.room_number""")
    guest_history = rows("""SELECT g.first_name || ' ' || g.last_name AS guest_name,
                                 r.room_number,rs.check_in_date,rs.check_out_date,rs.status
                          FROM guest g JOIN reservation rs ON g.guest_id=rs.guest_id
                          JOIN room r ON rs.room_id=r.room_id ORDER BY rs.check_in_date DESC""")
    outstanding = rows("""SELECT i.invoice_id,g.first_name || ' ' || g.last_name AS guest_name,
                       r.room_number,i.total_amount,
                       COALESCE(SUM(p.amount),0) AS paid,
                       i.total_amount-COALESCE(SUM(p.amount),0) AS outstanding
                       FROM invoice i
                       JOIN stay s ON i.stay_id=s.stay_id
                       JOIN reservation rs ON s.reservation_id=rs.reservation_id
                       JOIN guest g ON rs.guest_id=g.guest_id
                       JOIN room r ON rs.room_id=r.room_id
                       LEFT JOIN payment p ON i.invoice_id=p.invoice_id AND p.status='Successful'
                       GROUP BY i.invoice_id,i.total_amount,g.first_name,g.last_name,r.room_number
                       HAVING outstanding>0""")
    service_by_type = rows("""SELECT sr.service_type,SUM(sc.amount) revenue
                            FROM service_charge sc JOIN service_request sr
                            ON sc.service_request_id=sr.service_request_id
                            GROUP BY sr.service_type ORDER BY revenue DESC""")
    payment_methods = rows("""SELECT payment_method,SUM(amount) total_collected
                            FROM payment WHERE status='Successful'
                            GROUP BY payment_method ORDER BY total_collected DESC""")
    return render_template("reports.html", occupancy=occupancy,revenue=revenue,invoiced_revenue=invoiced_revenue,
                           service_rev=service_rev,cancellations=cancellations,outstanding=outstanding,
                           service_by_type=service_by_type,payment_methods=payment_methods,
                           available_rooms=available_rooms,guest_history=guest_history)


@app.route("/database-validation")
def database_validation():
    checks = []
    conn = get_db()
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    checks.append(("Foreign Key Integrity", not fk_errors, "No foreign-key violations" if not fk_errors else f"{len(fk_errors)} violation(s)"))
    checks.append(("Primary Key / Required IDs", conn.execute("SELECT COUNT(*) FROM guest WHERE guest_id IS NULL").fetchone()[0] == 0, "Validated"))
    checks.append(("Unique Guest Emails", conn.execute("SELECT COUNT(*) FROM guest") .fetchone()[0] == conn.execute("SELECT COUNT(DISTINCT email) FROM guest").fetchone()[0], "No duplicate emails"))
    checks.append(("Room Capacity Rules", conn.execute("SELECT COUNT(*) FROM room r JOIN room_type rt ON r.room_type_id=rt.room_type_id WHERE rt.capacity<=0").fetchone()[0] == 0, "All capacities valid"))
    checks.append(("Reservation Date Rules", conn.execute("SELECT COUNT(*) FROM reservation WHERE date(check_out_date)<=date(check_in_date)").fetchone()[0] == 0, "All date ranges valid"))
    checks.append(("Payment Limits", conn.execute("""SELECT COUNT(*) FROM invoice i WHERE
        (SELECT COALESCE(SUM(p.amount),0) FROM payment p WHERE p.invoice_id=i.invoice_id AND p.status='Successful') > i.total_amount + 0.00001""").fetchone()[0] == 0, "No payment exceeds invoice total"))
    checks.append(("Reservation Overlaps", conn.execute("""SELECT COUNT(*) FROM reservation a JOIN reservation b
        ON a.room_id=b.room_id AND a.reservation_id<b.reservation_id
        AND a.status IN ('Pending','Confirmed') AND b.status IN ('Pending','Confirmed')
        AND date(a.check_in_date)<date(b.check_out_date) AND date(b.check_in_date)<date(a.check_out_date)""").fetchone()[0] == 0, "No active overlapping reservations"))
    conn.close()
    return render_template("validation.html", checks=checks)


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "guests": scalar("SELECT COUNT(*) FROM guest"),
        "rooms": scalar("SELECT COUNT(*) FROM room"),
        "available_rooms": scalar("SELECT COUNT(*) FROM room WHERE status='Available'"),
        "active_stays": scalar("SELECT COUNT(*) FROM stay WHERE status='Active'"),
        "outstanding_invoices": scalar("""SELECT COUNT(*) FROM invoice i WHERE i.total_amount >
            COALESCE((SELECT SUM(amount) FROM payment p WHERE p.invoice_id=i.invoice_id AND p.status='Successful'),0)""")
    })


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

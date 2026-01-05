import sqlite3
import os
from datetime import datetime, timedelta 
from math import ceil

DB_NAME = 'instance/db.sqlite3'

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        mobile TEXT,
        vehicle_reg_no TEXT,
        address TEXT,
        pincode TEXT,
        is_admin INTEGER DEFAULT 0
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS parking_lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price_per_hour REAL NOT NULL,
        address TEXT,
        pin_code TEXT,
        total_spots INTEGER
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS parking_spots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lot_id INTEGER,
        status TEXT DEFAULT 'A',
        FOREIGN KEY (lot_id) REFERENCES parking_lots(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        spot_id INTEGER,
        user_id INTEGER,
        start_time TEXT,
        end_time TEXT,
        price_per_hour REAL,
        FOREIGN KEY (spot_id) REFERENCES parking_spots(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS booking_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        lot_id INTEGER,
        spot_id INTEGER,
        booked_on TEXT,
        released_on TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (lot_id) REFERENCES parking_lots(id),
        FOREIGN KEY (spot_id) REFERENCES parking_spots(id)
    )''')
    
    cur.execute('''CREATE TABLE IF NOT EXISTS user_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        lot_id INTEGER,
        spot_id INTEGER,
        booked_time TEXT,
        released_time TEXT,
        duration REAL,
        amount_paid REAL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (lot_id) REFERENCES parking_lots(id),
        FOREIGN KEY (spot_id) REFERENCES parking_spots(id)
    )''')

    cur.execute("SELECT * FROM users WHERE username = ?", ('admin',))
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                    ('admin', 'admin123', 1))
        print("Admin created: admin / admin123")

    conn.commit()
    conn.close()

def get_user_by_credentials(username, password):
    conn = get_connection()
    conn.row_factory = sqlite3.Row 
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
        SELECT username, email, mobile, vehicle_reg_no, address, pincode
        FROM users
        WHERE id = ?
    ''', (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def register_user(username, password, email, mobile, vehicle_reg_no, address, pincode):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT INTO users (username, password, email, mobile, vehicle_reg_no, address, pincode)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, password, email, mobile, vehicle_reg_no, address, pincode))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
        
def update_user_profile(user_id, username, email, vehicle_reg_no, address, pincode, mobile):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        UPDATE users
        SET username = ?, email = ?, vehicle_reg_no = ?, address = ?, pincode = ?, mobile = ?
        WHERE id = ?
    ''', (username, email, vehicle_reg_no, address, pincode, mobile, user_id))
    conn.commit()
    conn.close()

def get_all_lots():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM parking_lots")
    lots = cur.fetchall()
    conn.close()
    return lots

def create_parking_lot(name, price, address, pin_code, total_spots):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO parking_lots (name, price_per_hour, address, pin_code, total_spots) VALUES (?, ?, ?, ?, ?)",
                (name, price, address, pin_code, total_spots))
    lot_id = cur.lastrowid
    for _ in range(total_spots):
        cur.execute("INSERT INTO parking_spots (lot_id, status) VALUES (?, 'A')", (lot_id,))
    conn.commit()
    conn.close()

def lot_has_occupied_spots(lot_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM parking_spots WHERE lot_id=? AND status='O'", (lot_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count > 0

def delete_lot_by_id(lot_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM parking_spots WHERE lot_id=?", (lot_id,))
    cur.execute("DELETE FROM parking_lots WHERE id=?", (lot_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, email, mobile, vehicle_reg_no, address, pincode FROM users WHERE is_admin=0")
    users = cur.fetchall()
    conn.close()
    return users

def get_user_reservations(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT 
                r.id, 
                r.spot_id, 
                strftime('%Y-%m-%d %H:%M', r.start_time) as start_time,
                CASE WHEN r.end_time IS NULL THEN 'Ongoing' 
                     ELSE strftime('%Y-%m-%d %H:%M', r.end_time) END as end_time,
                CASE WHEN r.end_time IS NULL THEN r.price_per_hour
                     ELSE r.price_per_hour END as price_per_hour
            FROM reservations r
            WHERE r.user_id=?
            ORDER BY r.start_time DESC
        """, (user_id,))
        
        reservations = cur.fetchall()
        return reservations
        
    except Exception as e:
        print(f"Error getting reservations: {e}")
        return []
    finally:
        conn.close()

def reserve_spot(lot_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT id FROM parking_spots WHERE lot_id=? AND status='A' LIMIT 1", (lot_id,))
        spot = cur.fetchone()
        if not spot:
            return False

        spot_id = spot[0]
        
        cur.execute("SELECT price_per_hour FROM parking_lots WHERE id=?", (lot_id,))
        price_per_hour = cur.fetchone()[0]
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cur.execute("""
            INSERT INTO reservations (spot_id, user_id, start_time, price_per_hour)
            VALUES (?, ?, ?, ?)
        """, (spot_id, user_id, now, price_per_hour))
        
        cur.execute("UPDATE parking_spots SET status='O' WHERE id=?", (spot_id,))
        
        cur.execute("""
            INSERT INTO booking_history (user_id, lot_id, spot_id, booked_on)
            VALUES (?, ?, ?, ?)
        """, (user_id, lot_id, spot_id, now))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error reserving spot: {e}")
        return False
    finally:
        conn.close()

def release_reservation(reservation_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT r.spot_id, r.start_time, r.price_per_hour, p.lot_id
            FROM reservations r
            JOIN parking_spots p ON r.spot_id = p.id
            WHERE r.id=? AND r.user_id=? AND r.end_time IS NULL
        """, (reservation_id, user_id))
        data = cur.fetchone()
        
        if not data:
            return False

        spot_id, start_time, price_per_hour, lot_id = data
        end_time = datetime.now()
        start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        
        duration_hours = (end_time - start_dt).total_seconds() / 3600
        duration_hours = round(duration_hours, 2)
        amount_paid = price_per_hour * ceil(duration_hours)
        
        cur.execute("""
            UPDATE reservations 
            SET end_time=?
            WHERE id=?
        """, (end_time.strftime('%Y-%m-%d %H:%M:%S'), reservation_id))
        
        cur.execute("""
            INSERT INTO user_history (user_id, lot_id, spot_id, booked_time, released_time, duration, amount_paid)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, lot_id, spot_id, start_time, end_time.strftime('%Y-%m-%d %H:%M:%S'), duration_hours, amount_paid))
        
        cur.execute("UPDATE parking_spots SET status='A' WHERE id=?", (spot_id,))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error releasing reservation: {e}")
        return False
    finally:
        conn.close()
        
def get_user_history(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT h.id, l.name as lot_name, h.spot_id, 
               strftime('%Y-%m-%d %H:%M', h.booked_time) as booked_time,
               strftime('%Y-%m-%d %H:%M', h.released_time) as released_time,
               h.duration, h.amount_paid
        FROM user_history h
        JOIN parking_lots l ON h.lot_id = l.id
        WHERE h.user_id=?
        ORDER BY h.booked_time DESC
    """, (user_id,))
    history = cur.fetchall()
    conn.close()
    return history

def get_admin_stats():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    stats = {}
    
    cur.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM user_history")
    stats['total_revenue'] = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM parking_spots WHERE status='O'")
    occupied = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM parking_spots")
    total = cur.fetchone()[0]
    stats['occupancy_rate'] = (occupied / total) * 100 if total > 0 else 0
    
    cur.execute("""
        SELECT u.username, l.name as lot_name, h.booked_time
        FROM user_history h
        JOIN users u ON h.user_id = u.id
        JOIN parking_lots l ON h.lot_id = l.id
        ORDER BY h.booked_time DESC
        LIMIT 5
    """)
    stats['recent_bookings'] = cur.fetchall()
    
    conn.close()
    return stats

def get_user_stats(user_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    stats = {}
    
    try:
        cur.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM user_history WHERE user_id=?", (user_id,))
        stats['total_spent'] = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM user_history WHERE user_id=?", (user_id,))
        stats['total_bookings'] = cur.fetchone()[0]
        
        cur.execute("""
            SELECT l.name as lot_name, h.booked_time, h.released_time, h.amount_paid, h.duration
            FROM user_history h
            JOIN parking_lots l ON h.lot_id = l.id
            WHERE h.user_id=?
            ORDER BY h.booked_time DESC
            LIMIT 5
        """, (user_id,))
        stats['recent_activity'] = cur.fetchall()
        
        stats['usage_labels'] = []
        stats['usage_data'] = []
        
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cur.execute("""
                SELECT COALESCE(SUM(duration), 0)
                FROM user_history
                WHERE user_id=? AND date(released_time)=?
            """, (user_id, date))
            duration = cur.fetchone()[0]
            stats['usage_data'].append(float(duration))
            stats['usage_labels'].append((datetime.now() - timedelta(days=i)).strftime('%a'))
        
        return stats
        
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return None
    finally:
        conn.close()
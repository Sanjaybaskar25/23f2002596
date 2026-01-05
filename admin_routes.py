from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import sqlite3
from database import (
    get_all_lots, create_parking_lot, lot_has_occupied_spots,
    delete_lot_by_id, get_all_users, get_user_history,
    get_connection
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
def restrict_to_admin():
    if not session.get('is_admin'):
        return redirect(url_for('auth.login'))

def get_admin_stats():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    stats = {}
    
    try:
        cur.execute("SELECT COALESCE(SUM(amount_paid), 0) FROM user_history")
        stats['total_revenue'] = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM parking_spots WHERE status='O'")
        occupied = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM parking_spots")
        total = cur.fetchone()[0]
        stats['occupancy_rate'] = (occupied / total) * 100 if total > 0 else 0
        
        cur.execute("SELECT COUNT(*) FROM users WHERE is_admin=0")
        stats['total_users'] = cur.fetchone()[0]
        
        cur.execute("""
            SELECT u.username, l.name as lot_name, h.booked_time, h.amount_paid
            FROM user_history h
            JOIN users u ON h.user_id = u.id
            JOIN parking_lots l ON h.lot_id = l.id
            ORDER BY h.booked_time DESC
            LIMIT 5
        """)
        stats['recent_bookings'] = cur.fetchall()
        
        revenue_data = []
        revenue_labels = []
        
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cur.execute("""
                SELECT COALESCE(SUM(amount_paid), 0) 
                FROM user_history 
                WHERE date(released_time) = ?
            """, (date,))
            amount = cur.fetchone()[0]
            revenue_data.append(amount)
            revenue_labels.append((datetime.now() - timedelta(days=i)).strftime('%a'))
        
        stats['revenue_data'] = revenue_data
        stats['revenue_labels'] = revenue_labels
        
        return stats
        
    except Exception as e:
        print(f"Error getting admin stats: {e}")
        return None
    finally:
        conn.close()

@admin_bp.route('/dashboard')
def dashboard():
    lots = get_all_lots()
    stats = get_admin_stats()
    if not stats:
        flash('Could not load dashboard statistics', 'error')
        return redirect(url_for('admin.view_users'))
    return render_template('admin_dashboard.html', lots=lots, stats=stats)

@admin_bp.route('/user/<int:user_id>/history')
def user_history(user_id):
    history = get_user_history(user_id)
    return render_template('user_history.html', history=history, user_id=user_id)

@admin_bp.route('/add_lot', methods=['GET', 'POST'])
def add_lot():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        address = request.form['address']
        pin_code = request.form['pin_code']
        total_spots = int(request.form['total_spots'])

        if not name or price <= 0 or total_spots <= 0:
            flash('Invalid input data', 'error')
            return redirect(url_for('admin.add_lot'))

        try:
            create_parking_lot(name, price, address, pin_code, total_spots)
            flash('Parking lot created successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash(f'Error creating parking lot: {str(e)}', 'error')
    
    return render_template('create_lot.html')

@admin_bp.route('/delete_lot/<int:lot_id>')
def delete_lot(lot_id):
    try:
        if lot_has_occupied_spots(lot_id):
            flash('Cannot delete lot: one or more spots are currently occupied.', 'error')
            return redirect(url_for('admin.dashboard'))

        delete_lot_by_id(lot_id)
        flash('Parking lot deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting parking lot: {str(e)}', 'error')
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/view_users')
def view_users():
    try:
        users = get_all_users()
        return render_template('view_users.html', users=users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))
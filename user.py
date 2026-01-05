from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_all_lots, get_user_reservations, reserve_spot, release_reservation

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.before_request
def restrict_to_user():
    if session.get('is_admin') or 'user_id' not in session:
        return redirect(url_for('auth.login'))

@user_bp.route('/dashboard')
def dashboard():
    lots = get_all_lots()
    user_id = session.get('user_id')
    reservations = get_user_reservations(user_id)
    return render_template('user_dashboard.html', lots=lots, reservations=reservations)

@user_bp.route('/book/<int:lot_id>')
def book_spot(lot_id):
    user_id = session.get('user_id')
    success = reserve_spot(lot_id, user_id)
    if success:
        flash('Spot booked successfully.')
    else:
        flash('No available spots in this lot.')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/release/<int:reservation_id>')
def release_spot(reservation_id):
    user_id = session.get('user_id')
    success = release_reservation(reservation_id, user_id)
    if success:
        flash('Spot released successfully.')
    else:
        flash('Invalid request or reservation not found.')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    from database import get_user_by_id, update_user_profile

    if 'user_id' not in session:
        flash('Please log in to access your profile.')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user = get_user_by_id(user_id)

    if not user:
        flash('User not found.')
        return redirect(url_for('auth.login'))

    editable = request.args.get('edit') == 'true'

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        vehicle_reg_no = request.form['vehicle_reg_no']
        address = request.form['address']
        pincode = request.form['pincode']
        mobile = request.form['mobile']

        update_user_profile(user_id, username, email, vehicle_reg_no, address, pincode, mobile)
        flash('Profile updated successfully.')
        return redirect(url_for('user.profile'))

    return render_template('user_profile.html', user=user, editable=editable)


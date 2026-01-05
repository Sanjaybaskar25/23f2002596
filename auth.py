from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import get_user_by_credentials, register_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def home():
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_credentials(username, password)

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = bool(user['is_admin'])
            
            if user['is_admin']:
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']
        mobile = request.form['mobile'] 
        vehicle_reg_no = request.form['vehicle_reg_no']
        address = request.form['address']
        pincode = request.form['pincode']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        if register_user(username, password, email, mobile, vehicle_reg_no, address, pincode):
            flash('Registration successful. Please login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Username already exists.', 'danger')

    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('auth.login'))

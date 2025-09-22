from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "dev_secret"   # you can replace with a stronger secret later

# DB connection helper
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",             # your MySQL username
        password="abhay@123",    # your MySQL password
        database="waste_management"
    )

# Home
@app.route('/')
def home():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        pw_hash = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (name, email, password_hash) VALUES (%s,%s,%s)',
                           (name, email, pw_hash))
            conn.commit()
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Error as e:
            conn.rollback()
            flash('Error during registration: ' + str(e), 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('home'))

# Submit Waste
@app.route('/submit_waste', methods=['GET','POST'])
def submit_waste():
    if 'user_id' not in session:
        flash('Please log in to submit waste.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM landfills')
    landfills = cursor.fetchall()
    cursor.close()
    conn.close()

    if request.method == 'POST':
        user_id = session['user_id']
        landfill_id = request.form.get('landfill') or None
        waste_type = request.form['waste_type']
        weight = float(request.form.get('weight_kg') or 0)
        notes = request.form.get('notes')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO waste_records (user_id, landfill_id, waste_type, weight_kg, notes)
                          VALUES (%s,%s,%s,%s,%s)''',
                          (user_id, landfill_id, waste_type, weight, notes))
        conn.commit()

        # Credit score logic
        credit_change = 0
        if waste_type in ['dry','wet']:
            credit_change = int(5 * weight)
        elif waste_type == 'electronic':
            credit_change = int(10 * weight)
        elif waste_type == 'hazardous':
            credit_change = int(-20 * weight)
        else:
            credit_change = int(2 * weight)

        cursor.execute('UPDATE users SET credit_score = credit_score + %s WHERE user_id = %s',
                       (credit_change, user_id))
        conn.commit()
        cursor.close()
        conn.close()

        flash(f'Waste recorded. Credit change: {credit_change}', 'success')
        return redirect(url_for('dashboard'))

    return render_template('submit_waste.html', landfills=landfills)

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to see dashboard.', 'warning')
        return redirect(url_for('login'))

    uid = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT user_id, name, email, credit_score FROM users WHERE user_id = %s', (uid,))
    user = cursor.fetchone()

    cursor.execute('''SELECT r.*, l.name AS landfill_name
                      FROM waste_records r LEFT JOIN landfills l
                      ON r.landfill_id = l.landfill_id
                      WHERE r.user_id = %s ORDER BY r.created_at DESC LIMIT 100''', (uid,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('dashboard.html', user=user, records=records)


# Helper function to calculate credit points for a given record
def calculate_credit_points(waste_type, weight):
    """Calculates credit points based on waste type and weight."""
    weight = float(weight)  # Ensure weight is a float for calculations
    if waste_type in ['dry', 'wet']:
        return int(5 * weight)
    elif waste_type == 'electronic':
        return int(10 * weight)
    elif waste_type == 'hazardous':
        return int(-20 * weight)
    else:  # 'other'
        return int(2 * weight)


# Edit Waste Record Route
@app.route('/edit_record/<int:record_id>', methods=['GET', 'POST'])
def edit_record(record_id):
    if 'user_id' not in session:
        flash('Please log in to edit records.', 'warning')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if not conn:
        flash('Database connection failed.', 'danger')
        return redirect(url_for('dashboard'))

    cursor = conn.cursor(dictionary=True)

    # Fetch the record to edit, ensuring it belongs to the logged-in user
    cursor.execute('SELECT * FROM waste_records WHERE record_id = %s AND user_id = %s',
                   (record_id, session['user_id']))
    record = cursor.fetchone()

    if not record:
        flash('Record not found or you do not have permission to edit it.', 'danger')
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # 1. Calculate credit points for the ORIGINAL record
            old_credit = calculate_credit_points(record['waste_type'], record['weight_kg'])

            # 2. Get updated form data
            landfill_id = request.form.get('landfill')
            if landfill_id == '': landfill_id = None  # Handle empty string from form
            waste_type = request.form['waste_type']
            weight = float(request.form.get('weight_kg', 0))
            notes = request.form.get('notes', '').strip()

            # 3. Update the waste record in the database
            cursor.execute('''UPDATE waste_records
                              SET landfill_id=%s,
                                  waste_type=%s,
                                  weight_kg=%s,
                                  notes=%s
                              WHERE record_id = %s''',
                           (landfill_id, waste_type, weight, notes, record_id))

            # 4. Calculate new credit points and find the difference to apply
            new_credit = calculate_credit_points(waste_type, weight)
            credit_difference = new_credit - old_credit

            # 5. Apply the score difference to the user's total score
            if credit_difference != 0:
                cursor.execute('UPDATE users SET credit_score = credit_score + %s WHERE user_id = %s',
                               (credit_difference, session['user_id']))

            conn.commit()  # Commit both the record update and the score update
            flash('Record updated successfully!', 'success')
        except Error as e:
            conn.rollback()
            flash(f'An error occurred during the update: {e}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('dashboard'))

    # This part runs for a GET request
    # Fetch all landfills to populate the dropdown in the edit form
    cursor.execute('SELECT landfill_id, name FROM landfills ORDER BY name')
    landfills = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('edit_record.html', record=record, landfills=landfills)
if __name__ == '__main__':
    app.run(debug=True)

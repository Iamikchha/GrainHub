from flask import Flask, render_template, request, jsonify, session, url_for, redirect
from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash


app = Flask(__name__)
app.secret_key = 'grain-hub-secret-key-2025'  # IMPORTANT: Add this for sessions to work!
bcrypt = Bcrypt(app)

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Ikchha@20'
app.config['MYSQL_DB'] = 'grain_hub'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    email = data['email']
    password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    role = data['role']
    farm_size = data.get('farm_size')
    business_name = data.get('business_name')

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, email, password, role, farm_size, business_name)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, email, password, role, farm_size, business_name))
        mysql.connection.commit()
        cur.close()
        return jsonify({"message": "Registration successful"}), 200
    except Exception as e:
        cur.close()
        return jsonify({"message": "Registration failed. Email might already exist."}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']
    role = data['role']

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s AND role = %s", (email, role))
    user = cur.fetchone()
    cur.close()

    if user and bcrypt.check_password_hash(user[3], password):
        session['user_id'] = user[0]
        session['role'] = user[4]
        
        # Return JSON with redirect URL instead of redirecting directly
        if user[4] == 'farmer':
            return jsonify({
                "message": "Login successful! Redirecting to farmer dashboard...",
                "redirect": url_for('farmer_dashboard')
            }), 200
        elif user[4] == 'merchant':
            return jsonify({
                "message": "Login successful! Redirecting to merchant dashboard...",
                "redirect": url_for('merchant_dashboard')
            }), 200
        else:
            return jsonify({
                "message": "Login successful!",
                "redirect": url_for('home')
            }), 200
    else:
        return jsonify({"message": "Invalid email, password, or role"}), 401

@app.route('/farmer_dashboard')
def farmer_dashboard():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('home'))

    cur = mysql.connection.cursor()

    # Get logged-in farmer's profile
    cur.execute("SELECT * FROM users WHERE id = %s", [session['user_id']])
    user = cur.fetchone()

    # Get all grain listings by this farmer
    cur.execute("SELECT * FROM grain_listings WHERE user_id = %s", [session['user_id']])
    listings = cur.fetchall()

    # Get merchant inquiries for this farmer's listings
    cur.execute("""
        SELECT i.merchant_name, i.message, g.grain_type 
        FROM inquiries i
        JOIN grain_listings g ON i.listing_id = g.id
        WHERE g.user_id = %s
    """, [session['user_id']])
    inquiries = cur.fetchall()

    cur.close()

    return render_template('farmer_dashboard.html', user=user, listings=listings, inquiries=inquiries)

# Add merchant dashboard route (placeholder)
@app.route('/merchant_dashboard')
def merchant_dashboard():
    if 'user_id' not in session or session.get('role') != 'merchant':
        return redirect(url_for('home'))
    
    cur = mysql.connection.cursor()
    
    # Get logged-in merchant's profile
    cur.execute("SELECT * FROM users WHERE id = %s", [session['user_id']])
    user = cur.fetchone()
    
    # Get all grain listings from farmers
    cur.execute("SELECT * FROM grain_listings")
    listings = cur.fetchall()
    
    cur.close()
    
    return render_template('merchant_dash.html', user=user, listings=listings)

@app.route('/add_listing', methods=['POST'])
def add_listing():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    grain_type = request.form['grain_type']
    quantity = request.form['quantity']
    price = request.form['price']
    harvest_date = request.form['harvest_date']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO grain_listings (user_id, grain_type, quantity, price, harvest_date)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, grain_type, quantity, price, harvest_date))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('farmer_dashboard'))

@app.route('/delete_listing', methods=['POST'])
def delete_listing():
    listing_id = request.form['id']
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM grain_listings WHERE id = %s AND user_id = %s", (listing_id, session['user_id']))
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('farmer_dashboard'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)

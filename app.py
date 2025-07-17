from flask import Flask, render_template, request, redirect, url_for, flash, session
from models.models import db, User, ParkingLot, ParkingSpot, Booking

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
db.init_app(app)

# --- Admin Routes ---
@app.route('/admin/dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not session.get('is_admin'):
        flash("You must be an admin to access this page.", "error")
        return redirect(url_for('login'))

    # Add a Parking Lot Function
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        pincode = request.form.get('pincode')
        price = request.form.get('price_per_hour')
        capacity = request.form.get('capacity')

        if not all([name, address, pincode, price, capacity]):
            flash("All fields are required!", "error")
        else:
            new_lot = ParkingLot(
                name=name,
                address=address,
                pincode=pincode,
                price_per_hour=float(price),
                capacity=int(capacity)
            )
            db.session.add(new_lot)
            db.session.commit() 

            for i in range(1, int(capacity) + 1):
                new_spot = ParkingSpot(spot_number=i, lot_id=new_lot.id, status='A')
                db.session.add(new_spot)
            
            db.session.commit()
            flash(f"Parking lot '{name}' and its {capacity} spots created successfully!", "success")
            return redirect(url_for('admin_dashboard'))

    # Display All Parking Lots function
    elif request.method == 'GET':
        all_lots = ParkingLot.query.all()
        return render_template('admin_dashboard.html', lots=all_lots)
    
# Admin Dashboard: View Parking Lot Details Route 
@app.route('/admin/lot/<int:lot_id>')
def view_lot_details(lot_id):
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)
    spots = lot.spots 

    return render_template('lot_details.html', lot=lot, spots=spots)

# --- Login Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash("Login successful!", "success")
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                # ///
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid credentials.", "error")
    return render_template('login.html')

# --- User Routes ---
@app.route('/dashboard')
def user_dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return "<h1>Welcome User!</h1>" # ///
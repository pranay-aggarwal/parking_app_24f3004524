from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models.models import db, User, ParkingLot, ParkingSpot, Booking
from datetime import datetime
import math

# ------------------------------------------------------------------------------------------------------------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'PranaysSecretKey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
db.init_app(app)

# --- Index Route ---
@app.route('/')
def index():
    return render_template('index.html')


# ------------------------------------------------------------------------------------------------------------------------------------------------------


# --- Logout Function Helper ---
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))



# --- Format Duration ---
def format_duration(booking):
    if not (booking.check_out_time and booking.check_in_time):
        return "N/A"

    delta = booking.check_out_time - booking.check_in_time
    total_seconds = delta.total_seconds()
    
    days, remainder = divmod(total_seconds, (24*60*60))
    hours, remainder = divmod(remainder, (60*60))
    minutes, remainder = divmod(remainder, 60)
    
    parts = ""
    if days > 0:
        parts += (f"{int(days)} days ")
    if hours > 0:
        parts += (f"{int(hours)} hours ")
    if minutes > 0:
        parts += (f"{int(minutes)} minutes")
    
    if parts:
        return parts  
    else:
        return "Less than a minute"
    

# ------------------------------------------------------------------------------------------------------------------------------------------------------


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
                return redirect(url_for('user_dashboard'))
        else:
            flash("Invalid credentials.", "error")
    return render_template('login.html')


# ------------------------------------------------------------------------------------------------------------------------------------------------------


# ---- Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if username or email already exists
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash("Username or email already exists. Please choose another.", "error")
            return redirect(url_for('register'))

        # Create new user
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# ------------------------------------------------------------------------------------------------------------------------------------------------------


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
    all_lots = ParkingLot.query.all()
    return render_template('admin_dashboard.html', lots=all_lots)



# Admin Dashboard: View Parking Lot Details Route 
@app.route('/admin/lot/<int:lot_id>')
def view_lot_details(lot_id):
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)
    
    spot_details = []
    for spot in lot.spots:
        detail = {'spot': spot, 'user': None}
        if spot.status == 'O':
            active_booking = Booking.query.filter_by(spot_id=spot.id, check_out_time=None).first()
            if active_booking:
                detail['user'] = User.query.get(active_booking.user_id)
        spot_details.append(detail)

    return render_template('lot_details.html', lot=lot, spot_details=spot_details)


# Admin Dashboard: Spot Add and Delete Route 
@app.route('/admin/lot/<int:lot_id>/add_spot', methods=['POST'])
def add_spot(lot_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    lot = ParkingLot.query.get_or_404(lot_id)

    if len(lot.spots) >= lot.capacity:
        flash("Cannot add spot: Lot is at full capacity.", "error")
        return redirect(url_for('view_lot_details', lot_id=lot.id))
    
    highest_spot_num = db.session.query(db.func.max(ParkingSpot.spot_number)).filter_by(lot_id=lot.id).scalar() or 0
    new_spot_number = highest_spot_num + 1

    new_spot = ParkingSpot(spot_number=new_spot_number, lot_id=lot.id, status='A')
    db.session.add(new_spot)
    db.session.commit()
    
    flash(f"Spot {new_spot_number} added successfully.", "success")
    return redirect(url_for('view_lot_details', lot_id=lot.id))

@app.route('/admin/spot/delete/<int:spot_id>', methods=['POST'])
def delete_spot(spot_id):
    if not session.get('is_admin'):
        return redirect(url_for('login'))

    spot_to_delete = ParkingSpot.query.get_or_404(spot_id)
    lot_id = spot_to_delete.lot_id

    existing_booking = Booking.query.filter_by(spot_id=spot_id).first()

    if existing_booking:
        flash("Cannot delete spot: It has booking history. Deleting it would remove these records.", "error")
        return redirect(url_for('view_lot_details', lot_id=lot_id))
    
    if spot_to_delete.status == 'O':
        flash("Cannot delete an occupied spot.", "error")
        return redirect(url_for('view_lot_details', lot_id=lot_id))

    db.session.delete(spot_to_delete)
    db.session.commit()

    flash(f"Spot {spot_to_delete.spot_number} deleted successfully.", "success")
    return redirect(url_for('view_lot_details', lot_id=lot_id))



# Admin Dashboard: Edit Parking Lot Route 
@app.route('/admin/lot/edit/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    lot_to_edit = ParkingLot.query.get_or_404(lot_id)

    if request.method == 'POST':
        lot_to_edit.name = request.form.get('name')
        lot_to_edit.address = request.form.get('address')
        lot_to_edit.pincode = request.form.get('pincode')
        lot_to_edit.price_per_hour = float(request.form.get('price_per_hour'))
        
        db.session.commit()
        flash(f"Parking lot '{lot_to_edit.name}' updated successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_lot.html', lot=lot_to_edit)



# Admin Dashboard: Delete Parking Lot Route 
@app.route('/admin/lot/delete/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    lot_to_delete = ParkingLot.query.get_or_404(lot_id)
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').first()
    existing_booking = Booking.query.join(ParkingSpot).filter(ParkingSpot.lot_id == lot_id).first()

    if existing_booking:
        flash("Cannot delete lot: It has booking history. Deleting it would remove these records.", "error")
    elif occupied_spots:
        flash(f"Cannot delete '{lot_to_delete.name}'. It has occupied spots.", "error")
    else:
        db.session.delete(lot_to_delete)
        db.session.commit()
        flash(f"Parking lot '{lot_to_delete.name}' has been deleted successfully.", "success")
    
    return redirect(url_for('admin_dashboard'))



# Admin Dashboard: View all Users Route 
@app.route('/admin/users')
def view_users():
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    all_users = User.query.filter_by(is_admin=False).all()

    return render_template('view_users.html', users=all_users)



# Admin Dashboard: View Summary Charts Route
@app.route('/admin/charts')
def admin_charts():
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))
    return render_template('admin_charts.html')

@app.route('/api/admin/chart-data')
def admin_chart_data():
    if not session.get('is_admin'):
        return jsonify({"error": "Admin access required"}), 403

    total_occupied = ParkingSpot.query.filter_by(status='O').count()
    total_available = ParkingSpot.query.filter_by(status='A').count()

    lots = ParkingLot.query.all()
    occupied_counts = {}
    available_counts = {}

    for lot in lots:
        occupied_count = 0
        available_count = 0
        for spot in lot.spots:
            if spot.status == 'O':
                occupied_count += 1
            else:
                available_count += 1
        occupied_counts[lot.name] = occupied_count
        available_counts[lot.name] = available_count

    # Create Charts
    chart_data = {
        "overall_occupancy": {
            "labels": ["Occupied", "Available"],
            "data": [total_occupied, total_available]
        },
        "lot_occupancy": {
            "labels": list(occupied_counts.keys()),
            "occupied_data": list(occupied_counts.values()),
            "available_data": list(available_counts.values())
        }
    }
    
    return jsonify(chart_data)



# Admin Dashboard: View All Bookings Route
@app.route('/admin/bookings')
def admin_all_bookings():
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    all_bookings = Booking.query.filter(Booking.check_out_time.isnot(None)).order_by(Booking.check_out_time.desc()).all()

    for booking in all_bookings:
        booking.duration_str = format_duration(booking)

    return render_template('admin_all_bookings.html', bookings=all_bookings)


# ------------------------------------------------------------------------------------------------------------------------------------------------------


# --- User Routes ---    
@app.route('/dashboard')
def user_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    active_bookings = Booking.query.filter_by(user_id=user_id, check_out_time=None).all()

    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
            
    return render_template('user_dashboard.html', lots=lots, active_bookings=active_bookings)



# User Dashboard: Book Parking Spot Function 
@app.route('/book/<int:lot_id>', methods=['POST'])
def book_spot(lot_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to book a spot.", "error")
        return redirect(url_for('login'))

    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if available_spot:
        available_spot.status = 'O'
        vehicle_number = request.form.get('vehicle_number')

        if not vehicle_number:
            flash("Vehicle number is required.", "error")
            return redirect(url_for('user_dashboard'))

        new_booking = Booking(user_id=user_id, spot_id=available_spot.id, vehicle_number=vehicle_number)
        db.session.add(new_booking)
        db.session.commit()
        flash(f"Successfully booked Spot #{available_spot.spot_number} in {available_spot.parking_lot.name}!", "success")
    else:
        flash("Sorry, this parking lot is now full.", "error")

    return redirect(url_for('user_dashboard'))



# User Dashboard: Release Parking Spot Function
@app.route('/release_spot/<int:booking_id>', methods=['POST'])
def release_spot(booking_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    booking_to_release = Booking.query.filter_by(id=booking_id, user_id=user_id, check_out_time=None).first()

    if booking_to_release:
        booking_to_release.check_out_time = datetime.utcnow()
        spot = ParkingSpot.query.get(booking_to_release.spot_id)
        lot = ParkingLot.query.get(spot.lot_id)
        spot.status = 'A'

        # Calculate total cost 
        duration = booking_to_release.check_out_time - booking_to_release.check_in_time
        duration_in_hours = math.ceil(duration.total_seconds() / 3600)
        total_cost = duration_in_hours * lot.price_per_hour
        booking_to_release.total_cost = total_cost
        
        db.session.commit()
        
        flash(f"Spot released successfully.You Parked for approx. {duration_in_hours} hours. Total cost: ₹{total_cost:.2f}", "success")
    else:
        flash("Booking not found or already released.", "error")

    return redirect(url_for('user_dashboard'))



# User Dashboard: View Booking History Route
@app.route('/history')
def user_history():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    completed_bookings = Booking.query.filter(Booking.user_id == user_id,Booking.check_out_time.isnot(None)).order_by(Booking.check_out_time.desc()).all()

    
    for booking in completed_bookings:
        booking.duration_str = format_duration(booking)
        
    return render_template('user_history.html', bookings=completed_bookings)



# User Dashboard: View Summary Charts Route
@app.route('/user/charts')
def user_charts():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return render_template('user_charts.html')

@app.route('/api/user/chart-data')
def user_chart_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "User not logged in"}), 403

    bookings = Booking.query.filter(Booking.user_id == user_id,Booking.check_out_time.isnot(None)).all()

    cost_per_lot = {}
    visits_per_lot = {}

    for booking in bookings:
        lot_name = booking.parking_spot.parking_lot.name
        cost_per_lot[lot_name] = cost_per_lot.get(lot_name, 0) + booking.total_cost
        visits_per_lot[lot_name] = visits_per_lot.get(lot_name, 0) + 1

    # Create Charts
    chart_data = {
        "cost_per_lot": {
            "labels": list(cost_per_lot.keys()),
            "data": list(cost_per_lot.values())
        },
        "visits_per_lot": {
            "labels": list(visits_per_lot.keys()),
            "data": list(visits_per_lot.values())
        }
    }
    
    return jsonify(chart_data)





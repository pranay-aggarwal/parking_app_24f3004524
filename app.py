from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
    all_lots = ParkingLot.query.all()
    return render_template('admin_dashboard.html', lots=all_lots)



# Admin Dashboard: View Parking Lot Details Route (Read)
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


# Admin Dashboard: Spot Add and Delete Route (Create/Delete)
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

    if spot_to_delete.status == 'O':
        flash("Cannot delete an occupied spot.", "error")
        return redirect(url_for('view_lot_details', lot_id=lot_id))

    db.session.delete(spot_to_delete)
    db.session.commit()

    flash(f"Spot {spot_to_delete.spot_number} deleted successfully.", "success")
    return redirect(url_for('view_lot_details', lot_id=lot_id))



# Admin Dashboard: Edit Parking Lot Route (Update)
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



# Admin Dashboard: Delete Parking Lot Route (Delete)
@app.route('/admin/lot/delete/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if not session.get('is_admin'):
        flash("Admin access required.", "error")
        return redirect(url_for('login'))

    lot_to_delete = ParkingLot.query.get_or_404(lot_id)
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot_id, status='O').first()

    if occupied_spots:
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

    # Pie Chart: Overall Occupancy
    total_occupied = ParkingSpot.query.filter_by(status='O').count()
    total_available = ParkingSpot.query.filter_by(status='A').count()

    # Bar Chart: Occupancy per Lot
    lots = ParkingLot.query.all()
    lot_occupancy_data = {
        "labels": [lot.name for lot in lots],
        "datasets": [{
            "label": "Occupied Spots",
            "data": [len([spot for spot in lot.spots if spot.status == 'O']) for lot in lots],
            "backgroundColor": "rgba(220, 53, 69, 0.6)"
        }, {
            "label": "Available Spots",
            "data": [len([spot for spot in lot.spots if spot.status == 'A']) for lot in lots],
            "backgroundColor": "rgba(40, 167, 69, 0.6)"
        }]
    }

    # Create Charts
    chart_data = {
        "overall_occupancy": {
            "labels": ["Occupied", "Available"],
            "data": [total_occupied, total_available]
        },
        "lot_occupancy": lot_occupancy_data
    }
    
    return jsonify(chart_data)




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


# --- User Routes ---
@app.route('/dashboard')
def user_dashboard():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    return "<h1>Welcome User!</h1>" # ///
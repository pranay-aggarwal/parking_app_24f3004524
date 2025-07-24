from app import app, db, User

with app.app_context():
    db.create_all()
    
    # Check if admin user already exists, if not create it
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', email='admin@gmail..com', password='admin', is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
    else:
        print("Admin user already exists.")

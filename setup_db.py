from app import app, db, User

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    
    # Check if admin user already exists, if not create it
    if not User.query.filter_by(username='admin').first():
        print("Creating admin user...")
        admin_user = User(username='admin', email='admin@gmail..com', password='admin', is_admin=True)
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin user already exists.")

    print("Database setup complete.")
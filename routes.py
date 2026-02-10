from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app import app, db
from models import Student, Admin, Event, Registration
import logging

# Helper functions
def is_student_logged_in():
    return 'student_id' in session

def is_admin_logged_in():
    return 'admin_id' in session

def get_current_student():
    if is_student_logged_in():
        return Student.query.get(session['student_id'])
    return None

def get_current_admin():
    if is_admin_logged_in():
        return Admin.query.get(session['admin_id'])
    return None

# Home page - shows events for students
@app.route('/')
def index():
    if is_student_logged_in():
        return redirect(url_for('student_dashboard'))
    
    # Show public events list
    upcoming_events = Event.query.filter(Event.date > datetime.utcnow()).order_by(Event.date).all()
    return render_template('index.html', events=upcoming_events)

# Student routes
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        roll_number = request.form.get('roll_number')
        department = request.form.get('department')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([name, email, roll_number, department, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')
        
        # Check if email or roll number already exists
        if Student.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('signup.html')
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered.', 'danger')
            return render_template('signup.html')
        
        # Create new student
        try:
            student = Student(
                name=name,
                email=email,
                roll_number=roll_number,
                department=department,
                password_hash=generate_password_hash(password)
            )
            db.session.add(student)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Registration error: {e}")
            flash('Registration failed. Please try again.', 'danger')
            db.session.rollback()
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html')
        
        student = Student.query.filter_by(email=email).first()
        
        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.student_id
            session['student_name'] = student.name
            flash(f'Welcome back, {student.name}!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')

@app.route('/student_dashboard')
def student_dashboard():
    if not is_student_logged_in():
        flash('Please log in to access the dashboard.', 'warning')
        return redirect(url_for('login'))
    
    student = get_current_student()
    upcoming_events = Event.query.filter(Event.date > datetime.utcnow()).order_by(Event.date).all()
    
    # Get student's registered event IDs
    registered_event_ids = [reg.event_id for reg in student.registrations]
    
    return render_template('student_dashboard.html', 
                         events=upcoming_events, 
                         registered_event_ids=registered_event_ids,
                         student=student)

@app.route('/register/<int:event_id>')
def register_event(event_id):
    if not is_student_logged_in():
        flash('Please log in to register for events.', 'warning')
        return redirect(url_for('login'))
    
    student = get_current_student()
    event = Event.query.get_or_404(event_id)
    
    # Check if event is full
    if event.is_full:
        flash('Sorry, this event is full.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Check if event is past
    if event.is_past:
        flash('Cannot register for past events.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Check if already registered
    existing_registration = Registration.query.filter_by(
        event_id=event_id, student_id=student.student_id
    ).first()
    
    if existing_registration:
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('student_dashboard'))
    
    try:
        registration = Registration(event_id=event_id, student_id=student.student_id)
        db.session.add(registration)
        db.session.commit()
        flash(f'Successfully registered for {event.title}!', 'success')
    except Exception as e:
        logging.error(f"Registration error: {e}")
        flash('Registration failed. Please try again.', 'danger')
        db.session.rollback()
    
    return redirect(url_for('student_dashboard'))

@app.route('/my-registrations')
def my_registrations():
    if not is_student_logged_in():
        flash('Please log in to view your registrations.', 'warning')
        return redirect(url_for('login'))
    
    student = get_current_student()
    registrations = Registration.query.filter_by(student_id=student.student_id).order_by(Registration.timestamp.desc()).all()
    
    return render_template('my_registrations.html', registrations=registrations, student=student)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('admin_login.html')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.admin_id
            session['admin_username'] = admin.username
            flash(f'Welcome back, {admin.username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_logged_in():
        flash('Please log in as admin to access the dashboard.', 'warning')
        return redirect(url_for('admin_login'))
    
    events = Event.query.order_by(Event.date.desc()).all()
    return render_template('admin_dashboard.html', events=events)

@app.route('/admin/add-event', methods=['GET', 'POST'])
def add_event():
    if not is_admin_logged_in():
        flash('Please log in as admin to add events.', 'warning')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        venue = request.form.get('venue')
        department = request.form.get('department')
        max_participants = request.form.get('max_participants')
        
        if not all([title, description, date_str, venue, department, max_participants]):
            flash('All fields are required.', 'danger')
            return render_template('add_event.html')
        
        try:
            # Parse the datetime
            event_date = datetime.fromisoformat(date_str.replace('T', ' '))
            max_participants = int(max_participants)
            
            event = Event(
                title=title,
                description=description,
                date=event_date,
                venue=venue,
                department=department,
                max_participants=max_participants
            )
            db.session.add(event)
            db.session.commit()
            flash('Event added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except ValueError:
            flash('Invalid date format or participant count.', 'danger')
        except Exception as e:
            logging.error(f"Add event error: {e}")
            flash('Failed to add event. Please try again.', 'danger')
            db.session.rollback()
    
    return render_template('add_event.html')

@app.route('/admin/edit-event/<int:event_id>', methods=['GET', 'POST'])
def edit_event(event_id):
    if not is_admin_logged_in():
        flash('Please log in as admin to edit events.', 'warning')
        return redirect(url_for('admin_login'))
    
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        venue = request.form.get('venue')
        department = request.form.get('department')
        max_participants = request.form.get('max_participants')
        
        if not all([title, description, date_str, venue, department, max_participants]):
            flash('All fields are required.', 'danger')
            return render_template('edit_event.html', event=event)
        
        try:
            # Parse the datetime
            event_date = datetime.fromisoformat(date_str.replace('T', ' '))
            max_participants = int(max_participants)
            
            event.title = title
            event.description = description
            event.date = event_date
            event.venue = venue
            event.department = department
            event.max_participants = max_participants
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except ValueError:
            flash('Invalid date format or participant count.', 'danger')
        except Exception as e:
            logging.error(f"Edit event error: {e}")
            flash('Failed to update event. Please try again.', 'danger')
            db.session.rollback()
    
    return render_template('edit_event.html', event=event)

@app.route('/admin/delete-event/<int:event_id>',methods=['POST'])
def delete_event(event_id):
    if not is_admin_logged_in():
        flash('Please log in as admin to delete events.', 'warning')
        return redirect(url_for('admin_login'))
    
    event = Event.query.get_or_404(event_id)
    
    try:
        db.session.delete(event)
        db.session.commit()
        flash(f'Event "{event.title}" deleted successfully!', 'success')
    except Exception as e:
        logging.error(f"Delete event error: {e}")
        flash('Failed to delete event. Please try again.', 'danger')
        db.session.rollback()
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/event/<int:event_id>/participants')
def view_participants(event_id):
    if not is_admin_logged_in():
        flash('Please log in as admin to view participants.', 'warning')
        return redirect(url_for('admin_login'))
    
    event = Event.query.get_or_404(event_id)
    registrations = Registration.query.filter_by(event_id=event_id).order_by(Registration.timestamp).all()
    
    return render_template('participants.html', event=event, registrations=registrations)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('admin_login'))

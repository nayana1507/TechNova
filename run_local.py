import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import UniqueConstraint

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-for-local")

# Configure the database for local SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///technova.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Define Models
class Student(db.Model):
    __tablename__ = 'students'
    
    student_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    roll_number = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    registrations = db.relationship('Registration', backref='student', lazy=True, cascade='all, delete-orphan')

class Admin(db.Model):
    __tablename__ = 'admins'
    
    admin_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'events'
    
    event_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    max_participants = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    registrations = db.relationship('Registration', backref='event', lazy=True, cascade='all, delete-orphan')
    
    @property
    def current_participants(self):
        return len(self.registrations)
    
    @property
    def is_full(self):
        return self.current_participants >= self.max_participants
    
    @property
    def is_past(self):
        return self.date < datetime.utcnow()

class Registration(db.Model):
    __tablename__ = 'registrations'
    
    reg_id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.event_id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate registrations
    __table_args__ = (UniqueConstraint('event_id', 'student_id', name='unique_registration'),)

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

# Routes
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
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        
        # Check if email or roll number already exists
        if Student.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('signup.html')
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered.', 'error')
            return render_template('signup.html')
        
        # Create new student
        student = Student(
            name=name,
            email=email,
            roll_number=roll_number,
            department=department,
            password_hash=generate_password_hash(password)
        )
        
        try:
            db.session.add(student)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating student: {e}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html')
        
        student = Student.query.filter_by(email=email).first()
        
        if student and check_password_hash(student.password_hash, password):
            session['student_id'] = student.student_id
            session['student_name'] = student.name
            flash(f'Welcome back, {student.name}!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('login.html')

@app.route('/student/dashboard')
def student_dashboard():
    if not is_student_logged_in():
        flash('Please login to access your dashboard.', 'error')
        return redirect(url_for('login'))
    
    student = get_current_student()
    if not student:
        session.clear()
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('login'))
    
    # Get upcoming events
    upcoming_events = Event.query.filter(Event.date > datetime.utcnow()).order_by(Event.date).all()
    
    # Get student's registrations
    registered_event_ids = [reg.event_id for reg in student.registrations]
    
    return render_template('student_dashboard.html', 
                         student=student, 
                         events=upcoming_events,
                         registered_event_ids=registered_event_ids)

@app.route('/student/register/<int:event_id>')
def register_event(event_id):
    if not is_student_logged_in():
        flash('Please login to register for events.', 'error')
        return redirect(url_for('login'))
    
    student = get_current_student()
    event = Event.query.get_or_404(event_id)
    
    # Check if event is full
    if event.is_full:
        flash('Sorry, this event is full.', 'error')
        return redirect(url_for('student_dashboard'))
    
    # Check if event is in the past
    if event.is_past:
        flash('Cannot register for past events.', 'error')
        return redirect(url_for('student_dashboard'))
    
    # Check if already registered
    existing_registration = Registration.query.filter_by(
        event_id=event_id, 
        student_id=student.student_id
    ).first()
    
    if existing_registration:
        flash('You are already registered for this event.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Create registration
    registration = Registration(
        event_id=event_id,
        student_id=student.student_id
    )
    
    try:
        db.session.add(registration)
        db.session.commit()
        flash(f'Successfully registered for {event.title}!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error registering student: {e}")
        flash('Registration failed. Please try again.', 'error')
    
    return redirect(url_for('student_dashboard'))

@app.route('/student/unregister/<int:event_id>')
def unregister_event(event_id):
    if not is_student_logged_in():
        flash('Please login to manage your registrations.', 'error')
        return redirect(url_for('login'))
    
    student = get_current_student()
    registration = Registration.query.filter_by(
        event_id=event_id, 
        student_id=student.student_id
    ).first()
    
    if not registration:
        flash('You are not registered for this event.', 'error')
        return redirect(url_for('my_registrations'))
    
    event = Event.query.get(event_id)
    
    try:
        db.session.delete(registration)
        db.session.commit()
        flash(f'Successfully unregistered from {event.title}.', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error unregistering student: {e}")
        flash('Unregistration failed. Please try again.', 'error')
    
    return redirect(url_for('my_registrations'))

@app.route('/student/registrations')
def my_registrations():
    if not is_student_logged_in():
        flash('Please login to view your registrations.', 'error')
        return redirect(url_for('login'))
    
    student = get_current_student()
    if not student:
        session.clear()
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('login'))
    
    # Get student's registrations using the relationship - this will work with your template
    registrations = Registration.query.filter_by(student_id=student.student_id).order_by(
        Registration.timestamp.desc()
    ).all()
    
    return render_template('my_registrations.html', registrations=registrations, student=student)
    
    '''# Get student's registrations with event details
    registrations = db.session.query(Registration, Event).join(Event).filter(
        Registration.student_id == student.student_id
    ).order_by(Event.date).all()
    
    return render_template('my_registrations.html', registrations=registrations, student=student)'''

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('admin_login.html')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and check_password_hash(admin.password_hash, password):
            session['admin_id'] = admin.admin_id
            session['admin_username'] = admin.username
            flash(f'Welcome, {admin.username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin_logged_in():
        flash('Please login to access admin dashboard.', 'error')
        return redirect(url_for('admin_login'))
    
    admin = get_current_admin()
    if not admin:
        session.clear()
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('admin_login'))
    
    # Get all events with registration counts
    events = Event.query.order_by(Event.date).all()
    
    # Get statistics
    total_events = len(events)
    total_students = Student.query.count()
    total_registrations = Registration.query.count()
    upcoming_events = len([e for e in events if e.date > datetime.utcnow()])
    
    stats = {
        'total_events': total_events,
        'total_students': total_students,
        'total_registrations': total_registrations,
        'upcoming_events': upcoming_events
    }
    
    return render_template('admin_dashboard.html', events=events, admin=admin, stats=stats)

@app.route('/admin/events/add', methods=['GET', 'POST'])
def add_event():
    if not is_admin_logged_in():
        flash('Please login to access admin features.', 'error')
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        venue = request.form.get('venue')
        department = request.form.get('department')
        max_participants = request.form.get('max_participants')
        
        # Validation
        if not all([title, description, date_str, venue, department, max_participants]):
            flash('All fields are required.', 'error')
            return render_template('add_event.html')
        
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            max_participants = int(max_participants)
            
            if max_participants < 1:
                flash('Maximum participants must be at least 1.', 'error')
                return render_template('add_event.html')
            
            if event_date <= datetime.utcnow():
                flash('Event date must be in the future.', 'error')
                return render_template('add_event.html')
            
        except ValueError:
            flash('Invalid date format or participant count.', 'error')
            return render_template('add_event.html')
        
        # Create new event
        event = Event(
            title=title,
            description=description,
            date=event_date,
            venue=venue,
            department=department,
            max_participants=max_participants
        )
        
        try:
            db.session.add(event)
            db.session.commit()
            flash(f'Event "{title}" created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating event: {e}")
            flash('Failed to create event. Please try again.', 'error')
    
    return render_template('add_event.html')

@app.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
def edit_event(event_id):
    if not is_admin_logged_in():
        flash('Please login to access admin features.', 'error')
        return redirect(url_for('admin_login'))
    
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        date_str = request.form.get('date')
        venue = request.form.get('venue')
        department = request.form.get('department')
        max_participants = request.form.get('max_participants')
        
        # Validation
        if not all([title, description, date_str, venue, department, max_participants]):
            flash('All fields are required.', 'error')
            return render_template('edit_event.html', event=event)
        
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
            max_participants = int(max_participants)
            
            if max_participants < 1:
                flash('Maximum participants must be at least 1.', 'error')
                return render_template('edit_event.html', event=event)
            
            # Check if reducing max participants below current registrations
            if max_participants < event.current_participants:
                flash(f'Cannot reduce max participants to {max_participants}. Current registrations: {event.current_participants}', 'error')
                return render_template('edit_event.html', event=event)
            
        except ValueError:
            flash('Invalid date format or participant count.', 'error')
            return render_template('edit_event.html', event=event)
        
        # Update event
        event.title = title
        event.description = description
        event.date = event_date
        event.venue = venue
        event.department = department
        event.max_participants = max_participants
        
        try:
            db.session.commit()
            flash(f'Event "{title}" updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating event: {e}")
            flash('Failed to update event. Please try again.', 'error')
    
    return render_template('edit_event.html', event=event)

@app.route('/admin/events/<int:event_id>/delete', methods=['POST'])
def delete_event(event_id):
    if not is_admin_logged_in():
        flash('Please login to access admin features.', 'error')
        return redirect(url_for('admin_login'))
    
    event = Event.query.get_or_404(event_id)
    
    try:
        # Delete all registrations for this event (cascade should handle this)
        db.session.delete(event)
        db.session.commit()
        flash(f'Event "{event.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting event: {e}")
        flash('Failed to delete event. Please try again.', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/events/<int:event_id>/participants')
def view_participants(event_id):
    if not is_admin_logged_in():
        flash('Please login to access admin features.', 'error')
        return redirect(url_for('admin_login'))
    
    event = Event.query.get_or_404(event_id)
    
    registrations = Registration.query.filter_by(event_id=event_id).order_by(Registration.timestamp).all()
    
    return render_template('participants.html', event=event, registrations=registrations)
    
    '''# Get participants with their registration details
    participants = db.session.query(Registration, Student).join(Student).filter(
        Registration.event_id == event_id
    ).order_by(Registration.timestamp).all()
    
    return render_template('participants.html', event=event, participants=participants)'''

# Logout routes
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Admin logged out successfully.', 'success')
    return redirect(url_for('index'))

def initialize_sample_data():
    """Initialize the database with events and admin account"""
    try:
        # Create all tables first
        db.create_all()
        
        # Check if data already exists
        if Event.query.count() > 0:
            print("Events already exist, skipping initialization.")
            return
        
        print("Initializing TechNova events...")
        
        # Create default admin
        if not Admin.query.filter_by(username='admin').first():
            default_admin = Admin(
                username='admin',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(default_admin)
        
        # TechNova Engineering Competition Events
        events_data = [
            {
                'title': 'Debugging Contest',
                'description': 'Find and fix bugs in given code snippets within time limits. Test your debugging skills across multiple programming languages.',
                'date': datetime(2025, 9, 15, 10, 0),
                'venue': 'Computer Lab A',
                'department': 'Computer Science',
                'max_participants': 50
            },
            {
                'title': 'UI/UX Design Challenge',
                'description': 'Design user-friendly interfaces for given problem statements. Create wireframes, prototypes, and present your design solutions.',
                'date': datetime(2025, 9, 16, 14, 30),
                'venue': 'Design Studio',
                'department': 'Computer Science',
                'max_participants': 50
            },
            {
                'title': 'Circuit Debugging',
                'description': 'Identify and fix issues in electronic circuits. Test your knowledge of circuit analysis and troubleshooting techniques.',
                'date': datetime(2025, 9, 17, 9, 0),
                'venue': 'Electronics Lab',
                'department': 'Electronics',
                'max_participants': 50
            },
            {
                'title': 'PCB Design Contest',
                'description': 'Design printed circuit boards for given specifications using industry-standard tools. Focus on layout optimization and design rules.',
                'date': datetime(2025, 9, 18, 11, 0),
                'venue': 'PCB Lab',
                'department': 'Electronics',
                'max_participants': 50
            },
            {
                'title': 'CAD Modelling',
                'description': 'Create 3D models and technical drawings using CAD software. Demonstrate precision in mechanical design and engineering drawings.',
                'date': datetime(2025, 9, 19, 13, 0),
                'venue': 'CAD Lab',
                'department': 'Mechanical',
                'max_participants': 50
            },
            {
                'title': 'Surveying Challenge',
                'description': 'Perform land surveying tasks and create accurate topographic maps. Use traditional and modern surveying instruments.',
                'date': datetime(2025, 9, 20, 8, 30),
                'venue': 'Survey Field',
                'department': 'Civil',
                'max_participants': 50
            },
            {
                'title': 'Poster Design (Technical Theme)',
                'description': 'Create informative technical posters on engineering topics. Focus on visual communication and technical accuracy.',
                'date': datetime(2025, 9, 21, 15, 0),
                'venue': 'Exhibition Hall',
                'department': 'General',
                'max_participants': 50
            },
            {
                'title': 'Case Study Analysis',
                'description': 'Analyze real-world engineering problems and present solutions. Demonstrate analytical thinking and problem-solving skills.',
                'date': datetime(2025, 9, 22, 10, 30),
                'venue': 'Seminar Hall',
                'department': 'General',
                'max_participants': 50
            },
            {
                'title': 'Tech Quiz',
                'description': 'MCQs from multiple engineering fields. Test your knowledge across Computer Science, Electronics, Mechanical, Civil, and emerging technologies.',
                'date': datetime(2025, 9, 23, 14, 0),
                'venue': 'Main Auditorium',
                'department': 'General',
                'max_participants': 50
            },
            {
                'title': 'Paper Presentation',
                'description': 'Individual research/innovation presentation. Present your original research, innovative ideas, or technical solutions to a panel of expert judges.',
                'date': datetime(2025, 9, 24, 10, 30),
                'venue': 'Conference Hall',
                'department': 'General',
                'max_participants': 50
            }
        ]
        
        # Add events to database
        for event_data in events_data:
            event = Event(**event_data)
            db.session.add(event)
        
        # Commit changes
        db.session.commit()
        
        print("✅ TechNova events initialized successfully!")
        print("📊 Created 10 engineering competition events")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error initializing events: {e}")
        logging.error(f"Error in initialize_sample_data: {e}")

# Initialize database and sample data
with app.app_context():
    initialize_sample_data()

if __name__ == '__main__':
    print("\n🚀 Starting TechNova - Where Innovation Meets Future")
    print("📱 Access your portal at: http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
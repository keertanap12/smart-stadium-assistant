import os
import json
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from modules.gate_flow import process_gate_flow
from modules.parking_allocator import allocate_parking
from modules.auth import validate_signup_inputs, hash_password, verify_password
from modules.venue import validate_venue_inputs

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon-stadium-ops-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stadium_ops.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Paths to JSON data files
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
GATES_FILE = os.path.join(DATA_DIR, 'mock_gates.json')
LOTS_FILE = os.path.join(DATA_DIR, 'mock_lots.json')
BATCHES_FILE = os.path.join(DATA_DIR, 'mock_batches.json')

# ==========================================================================
# DATABASE MODELS
# ==========================================================================

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    venues = db.relationship('Venue', backref='operator', lazy=True, cascade="all, delete-orphan")

class Venue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ==========================================================================
# DEFAULT MOCK DATA STRUCTURES
# ==========================================================================

DEFAULT_GATES = [
    {"venue_id": 1, "gate_id": "Gate A (North)", "current_crowd_count": 1470, "gate_capacity": 1500, "time_to_kickoff_minutes": 25},
    {"venue_id": 1, "gate_id": "Gate B (South)", "current_crowd_count": 1320, "gate_capacity": 1500, "time_to_kickoff_minutes": 25},
    {"venue_id": 2, "gate_id": "Gate C (East Entrance)", "current_crowd_count": 880, "gate_capacity": 1000, "time_to_kickoff_minutes": 45},
    {"venue_id": 2, "gate_id": "Gate D (West Entrance)", "current_crowd_count": 450, "gate_capacity": 1000, "time_to_kickoff_minutes": 45}
]

DEFAULT_LOTS = [
    {"venue_id": 1, "lot_id": "Lot A (VIP / Bus Zone)", "lot_capacity": 100, "current_occupancy": 60, "is_overflow": False},
    {"venue_id": 1, "lot_id": "Lot B (General North)", "lot_capacity": 200, "current_occupancy": 150, "is_overflow": False},
    {"venue_id": 1, "lot_id": "Lot C (General South)", "lot_capacity": 150, "current_occupancy": 110, "is_overflow": False},
    {"venue_id": 1, "lot_id": "Lot D (East Overflow)", "lot_capacity": 100, "current_occupancy": 0, "is_overflow": True},
    {"venue_id": 2, "lot_id": "Lot E (Main Deck)", "lot_capacity": 150, "current_occupancy": 120, "is_overflow": False},
    {"venue_id": 2, "lot_id": "Lot F (Basement A)", "lot_capacity": 200, "current_occupancy": 185, "is_overflow": False},
    {"venue_id": 2, "lot_id": "Lot G (Overflow Back Lot)", "lot_capacity": 100, "current_occupancy": 0, "is_overflow": True}
]

DEFAULT_BATCHES = [
    {"venue_id": 1, "batch_id": "Batch_01", "vehicle_type": "car", "count": 15, "expected_arrival_time": "17:15"},
    {"venue_id": 1, "batch_id": "Batch_02", "vehicle_type": "bus", "count": 4, "expected_arrival_time": "17:20"},
    {"venue_id": 1, "batch_id": "Batch_03", "vehicle_type": "car", "count": 25, "expected_arrival_time": "17:30"},
    {"venue_id": 1, "batch_id": "Batch_04", "vehicle_type": "bus", "count": 2, "expected_arrival_time": "17:35"},
    {"venue_id": 2, "batch_id": "Batch_Mall_01", "vehicle_type": "car", "count": 10, "expected_arrival_time": "12:15"},
    {"venue_id": 2, "batch_id": "Batch_Mall_02", "vehicle_type": "car", "count": 20, "expected_arrival_time": "12:30"},
    {"venue_id": 2, "batch_id": "Batch_Mall_03", "vehicle_type": "bus", "count": 3, "expected_arrival_time": "13:00"}
]

# ==========================================================================
# JSON FILES MANAGEMENT HELPERS (VENUE SCOPED)
# ==========================================================================

def load_json(filepath, default):
    """Safely loads a JSON file, initializing it with defaults if it doesn't exist."""
    if not os.path.exists(filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(filepath, 'w') as f:
            json.dump(default, f, indent=2)
        return default

def save_json(filepath, data):
    """Safely writes data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_scoped_gates(venue_id):
    """Returns gates filtered by venue_id."""
    gates = load_json(GATES_FILE, DEFAULT_GATES)
    return [g for g in gates if g.get('venue_id') == venue_id]

def load_scoped_lots(venue_id):
    """Returns lots filtered by venue_id."""
    lots = load_json(LOTS_FILE, DEFAULT_LOTS)
    return [l for l in lots if l.get('venue_id') == venue_id]

def load_scoped_batches(venue_id):
    """Returns batches filtered by venue_id."""
    batches = load_json(BATCHES_FILE, DEFAULT_BATCHES)
    return [b for b in batches if b.get('venue_id') == venue_id]

# ==========================================================================
# AUTHENTICATION ROUTING
# ==========================================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('venues'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        is_valid, err_msg = validate_signup_inputs(name, email, password)
        if not is_valid:
            flash(err_msg, 'error')
            return render_template('signup.html')
            
        email = email.strip().lower()
        
        # Check duplicate email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please login.", 'error')
            return render_template('signup.html')
            
        # Create user
        new_user = User(
            name=name.strip(),
            email=email,
            password_hash=hash_password(password.strip())
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Pre-seed default venues for user 1 to map to pre-existing json mock data
        if new_user.id == 1:
            venue1 = Venue(name="Wankhede Stadium", type="Cricket Stadium", city="Mumbai", user_id=new_user.id)
            venue2 = Venue(name="City Mall", type="Shopping Mall", city="Delhi", user_id=new_user.id)
            db.session.add(venue1)
            db.session.add(venue2)
            db.session.commit()
            
        flash("Account created successfully! Please log in.", 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('venues'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash("All fields are required.", 'error')
            return render_template('login.html')
            
        user = User.query.filter_by(email=email).first()
        if not user or not verify_password(user.password_hash, password):
            flash("Invalid email or password. Please try again.", 'error')
            return render_template('login.html')
            
        login_user(user)
        return redirect(url_for('venues'))
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('selected_venue_id', None)
    session.pop('selected_venue_name', None)
    flash("You have logged out successfully.", 'success')
    return redirect(url_for('login'))

# ==========================================================================
# VENUES MANAGEMENT ROUTING
# ==========================================================================

@app.route('/venues', methods=['GET', 'POST'])
@login_required
def venues():
    if request.method == 'POST':
        name = request.form.get('name')
        type = request.form.get('type')
        city = request.form.get('city')
        
        is_valid, err_msg = validate_venue_inputs(name, type, city)
        if not is_valid:
            flash(err_msg, 'error')
        else:
            new_venue = Venue(
                name=name.strip(),
                type=type,
                city=city.strip(),
                user_id=current_user.id
            )
            db.session.add(new_venue)
            db.session.commit()
            flash(f"Venue '{new_venue.name}' registered successfully!", 'success')
            
    user_venues = Venue.query.filter_by(user_id=current_user.id).all()
    return render_template('venues.html', venues=user_venues)

@app.route('/venues/select/<int:venue_id>', methods=['POST'])
@login_required
def select_venue(venue_id):
    venue = db.session.get(Venue, venue_id)
    if not venue or venue.user_id != current_user.id:
        flash("Venue not found or access denied.", "error")
        return redirect(url_for('venues'))
        
    session['selected_venue_id'] = venue.id
    session['selected_venue_name'] = f"{venue.name} ({venue.city})"
    return redirect(url_for('dashboard'))

# ==========================================================================
# CORE DASHBOARD ROUTING (PROTECTED & SCOPED)
# ==========================================================================

@app.route('/')
@login_required
def dashboard():
    if 'selected_venue_id' not in session:
        return redirect(url_for('venues'))
    return render_template('index.html')

# ==========================================================================
# API ENDPOINTS (PROTECTED & SCOPED)
# ==========================================================================

@app.route('/api/gates', methods=['GET'])
@login_required
def get_gates():
    venue_id = session.get('selected_venue_id')
    if not venue_id:
        return jsonify({"success": False, "error": "No venue selected."}), 400
        
    gates = load_scoped_gates(venue_id)
    try:
        results = process_gate_flow(gates)
        return jsonify({"success": True, "gates": results})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/gates', methods=['POST'])
@login_required
def add_gate():
    venue_id = session.get('selected_venue_id')
    if not venue_id:
        return jsonify({"success": False, "error": "No venue selected."}), 400
        
    data = request.get_json() or {}
    
    for field in ['gate_id', 'current_crowd_count', 'gate_capacity', 'time_to_kickoff_minutes']:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            return jsonify({"success": False, "error": f"Field '{field}' is required."}), 400
            
    # Load all gates to append
    all_gates = load_json(GATES_FILE, DEFAULT_GATES)
    
    new_gate = {
        "venue_id": venue_id,
        "gate_id": str(data['gate_id']).strip(),
        "current_crowd_count": data['current_crowd_count'],
        "gate_capacity": data['gate_capacity'],
        "time_to_kickoff_minutes": data['time_to_kickoff_minutes']
    }
    
    # Pre-validate only this venue's list + the new gate
    scoped_gates = [g for g in all_gates if g.get('venue_id') == venue_id]
    try:
        process_gate_flow(scoped_gates + [new_gate])
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
        
    all_gates.append(new_gate)
    save_json(GATES_FILE, all_gates)
    
    # Return updated scoped list
    updated_scoped = load_scoped_gates(venue_id)
    return jsonify({"success": True, "gates": process_gate_flow(updated_scoped)})

@app.route('/api/parking', methods=['GET'])
@login_required
def get_parking():
    venue_id = session.get('selected_venue_id')
    if not venue_id:
        return jsonify({"success": False, "error": "No venue selected."}), 400
        
    lots = load_scoped_lots(venue_id)
    batches = load_scoped_batches(venue_id)
    
    try:
        results = allocate_parking(lots, batches)
        return jsonify({
            "success": True,
            "allocations": results["allocations"],
            "lots": results["lots_after_allocation"],
            "recommendation": results["recommendation"]
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/parking/batches', methods=['POST'])
@login_required
def add_batch():
    venue_id = session.get('selected_venue_id')
    if not venue_id:
        return jsonify({"success": False, "error": "No venue selected."}), 400
        
    data = request.get_json() or {}
    
    for field in ['batch_id', 'vehicle_type', 'count', 'expected_arrival_time']:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            return jsonify({"success": False, "error": f"Field '{field}' is required."}), 400
            
    all_lots = load_json(LOTS_FILE, DEFAULT_LOTS)
    all_batches = load_json(BATCHES_FILE, DEFAULT_BATCHES)
    
    new_batch = {
        "venue_id": venue_id,
        "batch_id": str(data['batch_id']).strip(),
        "vehicle_type": str(data['vehicle_type']).strip().lower(),
        "count": data['count'],
        "expected_arrival_time": str(data['expected_arrival_time']).strip()
    }
    
    # Pre-validate allocation simulation on scoped items
    scoped_lots = [l for l in all_lots if l.get('venue_id') == venue_id]
    scoped_batches = [b for b in all_batches if b.get('venue_id') == venue_id]
    try:
        allocate_parking(scoped_lots, scoped_batches + [new_batch])
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
        
    all_batches.append(new_batch)
    save_json(BATCHES_FILE, all_batches)
    
    # Re-run scoped allocations
    results = allocate_parking(scoped_lots, scoped_batches + [new_batch])
    return jsonify({
        "success": True,
        "allocations": results["allocations"],
        "lots": results["lots_after_allocation"],
        "recommendation": results["recommendation"]
    })

@app.route('/api/parking/lots', methods=['POST'])
@login_required
def add_lot():
    venue_id = session.get('selected_venue_id')
    if not venue_id:
        return jsonify({"success": False, "error": "No venue selected."}), 400
        
    data = request.get_json() or {}
    
    for field in ['lot_id', 'lot_capacity', 'current_occupancy']:
        if field not in data or data[field] is None or str(data[field]).strip() == "":
            return jsonify({"success": False, "error": f"Field '{field}' is required."}), 400
            
    all_lots = load_json(LOTS_FILE, DEFAULT_LOTS)
    all_batches = load_json(BATCHES_FILE, DEFAULT_BATCHES)
    
    new_lot = {
        "venue_id": venue_id,
        "lot_id": str(data['lot_id']).strip(),
        "lot_capacity": data['lot_capacity'],
        "current_occupancy": data['current_occupancy'],
        "is_overflow": bool(data.get('is_overflow', False))
    }
    
    scoped_lots = [l for l in all_lots if l.get('venue_id') == venue_id]
    scoped_batches = [b for b in all_batches if b.get('venue_id') == venue_id]
    try:
        allocate_parking(scoped_lots + [new_lot], scoped_batches)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
        
    all_lots.append(new_lot)
    save_json(LOTS_FILE, all_lots)
    
    results = allocate_parking(scoped_lots + [new_lot], scoped_batches)
    return jsonify({
        "success": True,
        "allocations": results["allocations"],
        "lots": results["lots_after_allocation"],
        "recommendation": results["recommendation"]
    })

@app.route('/api/reset', methods=['POST'])
@login_required
def reset_data():
    save_json(GATES_FILE, DEFAULT_GATES)
    save_json(LOTS_FILE, DEFAULT_LOTS)
    save_json(BATCHES_FILE, DEFAULT_BATCHES)
    return jsonify({"success": True, "message": "All mock data has been reset to defaults."})

# Initialize Database on Startup
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

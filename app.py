# ======================================
# Flask Backend – Hospital Management System
# ======================================

import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Patient, Bed

app = Flask(__name__)
CORS(app)

# ---------- Configuration ----------
basedir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(basedir, 'instance')
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, 'hms.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---------- Extensions ----------
# Initialize db instance declared in models.py
db.init_app(app)

# Ensure tables exist on startup (works with flask run or direct execution)
with app.app_context():
    db.create_all()

# Debug: log all requests
@app.before_request
def log_request():
    print(f"Method: {request.method}, Path: {request.path}, Content-Type: {request.content_type}")
    print(f"Data: {request.data[:200] if request.data else 'None'}")

# ======================================
# Authentication API
# ======================================

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(id=data['id'], role=data['role']).first()

    if not user or not check_password_hash(user.password, data.get('password', '')):
        return jsonify({'msg': 'Invalid credentials'}), 401

    return jsonify({
        "msg": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role
        }
    })

# ======================================
# Admin APIs
# ======================================

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([
        {'id': u.id, 'name': u.name, 'email': u.email, 'role': u.role}
        for u in users
    ])

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    user = User(
        id=data['id'],
        name=data['name'],
        email=data['email'],
        password=generate_password_hash(data['password']),
        role=data['role'],
        gender=data.get('gender')
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({
        'msg': 'User created',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'gender': user.gender
        }
    }), 201

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify({'msg': 'User deleted'})

# ======================================
# Registrar APIs
# ======================================

@app.route('/patients', methods=['GET'])
def get_patients():
    patients = Patient.query.all()
    return jsonify([
        {
            'id': p.id,
            'name': p.name,
            'age': p.age,
            'gender': p.gender,
            'symptoms': p.symptoms,
            'date': p.date,
            'doctor_id': p.doctor_id
        } for p in patients
    ])

@app.route('/patients', methods=['POST'])
def create_patient():
    data = request.json
    # Accept both doctor_id and doctorId keys from frontend
    doctor_id = data.get('doctor_id') or data.get('doctorId')
    patient = Patient(
        name=data['name'],
        age=data.get('age'),
        gender=data.get('gender'),
        symptoms=data.get('symptoms'),
        date=data.get('date'),
        doctor_id=doctor_id
    )
    db.session.add(patient)
    db.session.commit()
    # Return the created patient with generated id at the top level to ensure grids get a usable row key
    return jsonify({
        'msg': 'Patient registered',
        'id': patient.id,
        'name': patient.name,
        'age': patient.age,
        'gender': patient.gender,
        'symptoms': patient.symptoms,
        'date': patient.date,
        'doctor_id': patient.doctor_id
    }), 201

@app.route('/patients/<int:patient_id>', methods=['DELETE'])
def delete_patient(patient_id):
    patient = Patient.query.get(patient_id)
    if not patient:
        return jsonify({'msg': 'Patient not found'}), 404
    db.session.delete(patient)
    db.session.commit()
    return jsonify({'msg': 'Patient deleted'})

# ======================================
# Doctor APIs
# ======================================

# Alternate endpoint using query param to avoid 404s when client omits path param
@app.route('/doctor/patients', methods=['GET'])
def doctor_patients_query():
    doctor_id = request.args.get('doctor_id')
    # If doctor_id is missing, return all patients so the client still renders data.
    patients = Patient.query.filter_by(doctor_id=doctor_id).all() if doctor_id else Patient.query.all()
    return jsonify([
        {'id': p.id, 'name': p.name, 'symptoms': p.symptoms, 'doctor_id': p.doctor_id}
        for p in patients
    ])

# ======================================
# IPD APIs
# ======================================

@app.route('/beds', methods=['GET'])
def get_beds():
    beds = Bed.query.all()
    return jsonify([
        {'bed_no': b.bed_no, 'ward': b.ward, 'status': b.status, 'patient_id': b.patient_id}
        for b in beds
    ])

@app.route('/beds', methods=['POST'])
def create_or_update_bed():
    try:
        data = json.loads(request.data)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({'msg': f'Invalid JSON: {str(e)}'}), 400
    
    if not data:
        return jsonify({'msg': 'Empty payload'}), 400
    
    bed_no = data.get('bed_no')
    ward = data.get('ward')
    status = data.get('status', 'Available')
    
    print(f"Received: bed_no={bed_no}, ward={ward}, status={status}")
    
    if not bed_no or not ward:
        return jsonify({'msg': 'bed_no and ward are required'}), 400
    
    # Check if bed already exists
    bed = Bed.query.filter_by(bed_no=bed_no, ward=ward).first()
    
    if bed:
        # Update existing bed status (e.g., vacate an occupied bed)
        bed.status = status
        if status == 'Available':
            bed.patient_id = None  # Clear patient when bed becomes available
        db.session.commit()
        return jsonify({
            'msg': 'Bed status updated',
            'bed_no': bed.bed_no,
            'ward': bed.ward,
            'status': bed.status,
            'patient_id': bed.patient_id
        })
    else:
        # Create new bed
        bed = Bed(
            bed_no=bed_no,
            ward=ward,
            status=status
        )
        db.session.add(bed)
        db.session.commit()
        return jsonify({
            'msg': 'Bed created',
            'bed_no': bed.bed_no,
            'ward': bed.ward,
            'status': bed.status,
            'patient_id': bed.patient_id
        }), 201

@app.route('/assign-bed', methods=['POST'])
def assign_bed():
    try:
        data = json.loads(request.data)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return jsonify({'msg': f'Invalid JSON: {str(e)}'}), 400
    
    if not data:
        return jsonify({'msg': 'Empty payload'}), 400
    
    # Accept both camelCase and snake_case from frontend
    bed_no = data.get('bed_no') or data.get('bedNo')
    ward = data.get('ward')
    patient_id = data.get('patient_id') or data.get('patientId')
    
    print(f"Received: patient_id={patient_id}, bed_no={bed_no}, ward={ward}")
    
    if not bed_no or not ward or not patient_id:
        return jsonify({'msg': 'bed_no, ward, and patient_id are required'}), 400
    
    # Find bed by both bed_no and ward (try exact match first, then partial)
    bed = Bed.query.filter_by(bed_no=bed_no, ward=ward).first()
    if not bed:
        # Try finding by bed_no and ward containing the value (e.g., "A" in "Ward A")
        bed = Bed.query.filter(Bed.bed_no == bed_no, Bed.ward.contains(ward)).first()
    
    if not bed:
        print(f"Bed not found: bed_no={bed_no}, ward={ward}")
        return jsonify({'msg': f'Bed not found with bed_no={bed_no} and ward={ward}'}), 404
    
    if bed.status == 'Occupied':
        return jsonify({'msg': 'Bed already occupied'}), 400

    bed.status = 'Occupied'
    bed.patient_id = patient_id
    db.session.commit()
    return jsonify({
        'msg': 'Bed assigned',
        'bed_no': bed.bed_no,
        'ward': bed.ward,
        'status': bed.status,
        'patient_id': bed.patient_id
    })

# ======================================
# Initialize Database
# ======================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

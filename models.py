# ======================================
# Database Models
# ======================================

from flask_sqlalchemy import SQLAlchemy

# Single shared SQLAlchemy instance initialized in app.py
db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    gender = db.Column(db.String(10))

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    symptoms = db.Column(db.Text)
    date = db.Column(db.String(50))
    doctor_id = db.Column(db.String, db.ForeignKey('user.id'))

class Bed(db.Model):
    bed_no = db.Column(db.String, primary_key=True)
    ward = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Available')
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
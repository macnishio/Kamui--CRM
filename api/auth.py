from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta

from src.models import User, APIKey, db
from src.utils.api_key_manager import APIKeyManager

auth_bp = Blueprint('auth', __name__)
key_manager = APIKeyManager()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({'message': 'Login successful', 'user_id': user.id})
    return jsonify({'error': 'Invalid credentials'}), 401

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 400
        
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        created_at=datetime.utcnow()
    )
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'Registration successful', 'user_id': user.id})

@auth_bp.route('/api-keys', methods=['POST'])
@login_required
def create_api_key():
    key = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    api_key = APIKey(
        user_id=current_user.id,
        key=key_manager.hash_key(key),
        expires_at=expires_at
    )
    db.session.add(api_key)
    db.session.commit()
    
    return jsonify({'api_key': key, 'expires_at': expires_at.isoformat()})

@auth_bp.route('/api-keys', methods=['GET'])
@login_required
def list_api_keys():
    keys = APIKey.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': key.id,
        'created_at': key.created_at.isoformat(),
        'expires_at': key.expires_at.isoformat(),
        'is_active': key.is_active
    } for key in keys])

@auth_bp.route('/api-keys/<int:key_id>', methods=['DELETE'])
@login_required
def revoke_api_key(key_id):
    key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if not key:
        return jsonify({'error': 'API key not found'}), 404
        
    key.is_active = False
    db.session.commit()
    return jsonify({'message': 'API key revoked successfully'})

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'})
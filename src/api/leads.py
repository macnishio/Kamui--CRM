from flask import Blueprint, request, jsonify
from flask_login import login_required
from sqlalchemy import desc
from src.models import Lead, db
from src.utils.ml_models import LeadScorer

leads_bp = Blueprint('leads', __name__)

@leads_bp.route('/api/leads', methods=['GET'])
@login_required
def get_leads():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')

    query = Lead.query
    if order == 'desc':
        query = query.order_by(desc(getattr(Lead, sort_by)))
    else:
        query = query.order_by(getattr(Lead, sort_by))

    pagination = query.paginate(page=page, per_page=per_page)
    leads = pagination.items

    return jsonify({
        'leads': [lead.to_dict() for lead in leads],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })

@leads_bp.route('/api/leads', methods=['POST'])
@login_required
def create_lead():
    data = request.get_json()
    required_fields = ['name', 'email', 'company']
    
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    lead = Lead(
        name=data['name'],
        email=data['email'],
        company=data['company'],
        phone=data.get('phone'),
        source=data.get('source'),
        status=data.get('status', 'new')
    )

    lead_scorer = LeadScorer()
    lead.score = lead_scorer.calculate_score(lead)

    db.session.add(lead)
    db.session.commit()

    return jsonify(lead.to_dict()), 201

@leads_bp.route('/api/leads/<int:lead_id>', methods=['GET'])
@login_required
def get_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return jsonify(lead.to_dict())

@leads_bp.route('/api/leads/<int:lead_id>', methods=['PUT'])
@login_required
def update_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    data = request.get_json()

    updateable_fields = ['name', 'email', 'company', 'phone', 'source', 'status']
    for field in updateable_fields:
        if field in data:
            setattr(lead, field, data[field])

    if any(field in data for field in ['name', 'email', 'company']):
        lead_scorer = LeadScorer()
        lead.score = lead_scorer.calculate_score(lead)

    db.session.commit()
    return jsonify(lead.to_dict())

@leads_bp.route('/api/leads/<int:lead_id>', methods=['DELETE'])
@login_required
def delete_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    return '', 204
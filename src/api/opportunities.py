from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime

from src.models import Opportunity, Lead, db
from src.utils.task_generator import TaskGenerator

opportunities = Blueprint('opportunities', __name__)

@opportunities.route('/api/opportunities', methods=['GET'])
@login_required
def get_opportunities():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = Opportunity.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Opportunity.created_at))
    
    opportunities = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'opportunities': [opp.to_dict() for opp in opportunities.items],
        'total': opportunities.total,
        'pages': opportunities.pages,
        'current_page': opportunities.page
    }), 200

@opportunities.route('/api/opportunities', methods=['POST'])
@login_required
def create_opportunity():
    data = request.get_json()
    
    required_fields = ['lead_id', 'title', 'amount', 'stage']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
        
    lead = Lead.query.get(data['lead_id'])
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
        
    opportunity = Opportunity(
        user_id=current_user.id,
        lead_id=data['lead_id'],
        title=data['title'],
        amount=data['amount'],
        stage=data['stage'],
        description=data.get('description', ''),
        expected_close_date=datetime.strptime(data.get('expected_close_date', ''), '%Y-%m-%d') if data.get('expected_close_date') else None
    )
    
    db.session.add(opportunity)
    db.session.commit()
    
    TaskGenerator.generate_opportunity_tasks(opportunity)
    
    return jsonify(opportunity.to_dict()), 201

@opportunities.route('/api/opportunities/<int:opp_id>/stage', methods=['PUT'])
@login_required
def update_opportunity_stage(opp_id):
    opportunity = Opportunity.query.get_or_404(opp_id)
    
    if opportunity.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.get_json()
    if 'stage' not in data:
        return jsonify({'error': 'Stage is required'}), 400
        
    opportunity.stage = data['stage']
    opportunity.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    TaskGenerator.generate_stage_change_tasks(opportunity)
    
    return jsonify(opportunity.to_dict()), 200

@opportunities.route('/api/opportunities/<int:opp_id>', methods=['GET'])
@login_required
def get_opportunity(opp_id):
    opportunity = Opportunity.query.get_or_404(opp_id)
    
    if opportunity.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    return jsonify(opportunity.to_dict()), 200
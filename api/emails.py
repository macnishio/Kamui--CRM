from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import desc
from datetime import datetime

from src.models import Email, Lead, db
from src.utils.email_analyzer import EmailAnalyzer

emails_bp = Blueprint('emails', __name__)
email_analyzer = EmailAnalyzer()

@emails_bp.route('/api/emails', methods=['GET'])
@login_required
def get_emails():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    emails = Email.query.filter_by(user_id=current_user.id)\
        .order_by(desc(Email.received_date))\
        .paginate(page=page, per_page=per_page)
    
    return jsonify({
        'emails': [email.to_dict() for email in emails.items],
        'total': emails.total,
        'pages': emails.pages,
        'current_page': emails.page
    })

@emails_bp.route('/api/emails/<int:email_id>/analyze', methods=['POST'])
@login_required
def analyze_email(email_id):
    email = Email.query.get_or_404(email_id)
    
    if email.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    analysis_result = email_analyzer.analyze(email.content)
    email.analysis_result = analysis_result
    email.analyzed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'email_id': email.id,
        'analysis_result': analysis_result
    })

@emails_bp.route('/api/emails/<int:email_id>/link-lead/<int:lead_id>', methods=['POST'])
@login_required
def link_email_to_lead(email_id, lead_id):
    email = Email.query.get_or_404(email_id)
    lead = Lead.query.get_or_404(lead_id)
    
    if email.user_id != current_user.id or lead.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    email.lead_id = lead.id
    db.session.commit()
    
    return jsonify({
        'email_id': email.id,
        'lead_id': lead.id,
        'message': 'Email successfully linked to lead'
    })

@emails_bp.route('/api/emails/sync', methods=['POST'])
@login_required
def sync_emails():
    try:
        new_emails = email_analyzer.sync_emails(current_user.id)
        return jsonify({
            'message': 'Email sync completed',
            'new_emails_count': len(new_emails),
            'new_emails': [email.to_dict() for email in new_emails]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
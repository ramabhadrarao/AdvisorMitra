from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.plan_service import PlanService
from utils.decorators import owner_required

plans_bp = Blueprint('plans', __name__)

@plans_bp.route('/')
@login_required
@owner_required
def list():
    page = request.args.get('page', 1, type=int)
    plan_service = PlanService()
    result = plan_service.get_all_plans(page=page)
    return render_template('plans/list.html', **result)

@plans_bp.route('/create', methods=['GET', 'POST'])
@login_required
@owner_required
def create():
    if request.method == 'POST':
        plan_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'period_type': request.form.get('period_type'),
            'period_value': int(request.form.get('period_value', 1)),
            'price': float(request.form.get('price', 0)),
            'pdf_limit': int(request.form.get('pdf_limit', 0)),
            'features': request.form.getlist('features'),
            'is_active': True
        }
        
        plan_service = PlanService()
        plan_id, error = plan_service.create_plan(plan_data, current_user.id)
        
        if plan_id:
            flash('Plan created successfully.', 'success')
            return redirect(url_for('plans.list'))
        else:
            flash(error, 'danger')
    
    return render_template('plans/create.html')

@plans_bp.route('/<plan_id>/edit', methods=['GET', 'POST'])
@login_required
@owner_required
def edit(plan_id):
    plan_service = PlanService()
    plan = plan_service.get_plan_by_id(plan_id)
    
    if not plan:
        flash('Plan not found.', 'danger')
        return redirect(url_for('plans.list'))
    
    if request.method == 'POST':
        update_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'period_type': request.form.get('period_type'),
            'period_value': int(request.form.get('period_value', 1)),
            'price': float(request.form.get('price', 0)),
            'pdf_limit': int(request.form.get('pdf_limit', 0)),
            'features': request.form.getlist('features')
        }
        
        success, message = plan_service.update_plan(plan_id, update_data, current_user.id)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('plans.list'))
        else:
            flash(message, 'danger')
    
    return render_template('plans/edit.html', plan=plan)

@plans_bp.route('/<plan_id>/toggle-status', methods=['POST'])
@login_required
@owner_required
def toggle_status(plan_id):
    plan_service = PlanService()
    success, message = plan_service.toggle_plan_status(plan_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('plans.list'))

# API endpoints
@plans_bp.route('/api/list')
@login_required
def api_list():
    if not current_user.is_owner():
        return jsonify({'error': 'Unauthorized'}), 403
    
    page = request.args.get('page', 1, type=int)
    plan_service = PlanService()
    result = plan_service.get_all_plans(page=page)
    
    plans_data = []
    for plan in result['plans']:
        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'description': plan.description,
            'period_type': plan.period_type,
            'period_value': plan.period_value,
            'period_display': plan.get_period_display(),
            'price': plan.price,
            'pdf_limit': plan.pdf_limit,
            'features': plan.features,
            'is_active': plan.is_active,
            'created_at': plan.created_at.isoformat() if plan.created_at else None
        })
    
    return jsonify({
        'success': True,
        'plans': plans_data,
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages']
    })

@plans_bp.route('/api/active')
@login_required
def api_active_plans():
    plan_service = PlanService()
    plans = plan_service.get_active_plans()
    
    plans_data = []
    for plan in plans:
        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'period_display': plan.get_period_display(),
            'price': plan.price,
            'pdf_limit': plan.pdf_limit
        })
    
    return jsonify({
        'success': True,
        'plans': plans_data
    })

@plans_bp.route('/api/create', methods=['POST'])
@login_required
def api_create():
    if not current_user.is_owner():
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    plan_data = {
        'name': data.get('name'),
        'description': data.get('description'),
        'period_type': data.get('period_type', 'YEARLY'),
        'period_value': data.get('period_value', 1),
        'price': data.get('price', 0),
        'pdf_limit': data.get('pdf_limit', 0),
        'features': data.get('features', []),
        'is_active': data.get('is_active', True)
    }
    
    # Validate required fields
    if not plan_data['name']:
        return jsonify({'success': False, 'error': 'Plan name is required'}), 400
    
    plan_service = PlanService()
    plan_id, error = plan_service.create_plan(plan_data, current_user.id)
    
    if plan_id:
        return jsonify({'success': True, 'plan_id': plan_id, 'message': 'Plan created successfully'})
    else:
        return jsonify({'success': False, 'error': error}), 400
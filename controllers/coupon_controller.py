# controllers/coupon_controller.py
# Enhanced coupon controller with partner restrictions

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from services.coupon_service import CouponService
from services.plan_service import PlanService
from utils.decorators import owner_required
from datetime import datetime
from models.user import User

coupons_bp = Blueprint('coupons', __name__)

@coupons_bp.route('/')
@login_required
@owner_required
def list():
    page = request.args.get('page', 1, type=int)
    coupon_service = CouponService()
    result = coupon_service.get_all_coupons(page=page)
    return render_template('coupons/list.html', **result)

@coupons_bp.route('/create', methods=['GET', 'POST'])
@login_required
@owner_required
def create():
    if request.method == 'POST':
        coupon_data = {
            'code': request.form.get('code'),
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'discount_type': request.form.get('discount_type'),
            'discount_value': float(request.form.get('discount_value', 0)),
            'min_purchase_amount': float(request.form.get('min_purchase_amount', 0)),
            'usage_limit': int(request.form.get('usage_limit')) if request.form.get('usage_limit') else None,
            'valid_from': request.form.get('valid_from'),
            'valid_until': request.form.get('valid_until'),
            'applicable_plans': request.form.getlist('applicable_plans'),
            'is_active': True
        }
        
        # Handle max discount amount for percentage discounts
        if coupon_data['discount_type'] == 'PERCENTAGE':
            max_discount = request.form.get('max_discount_amount')
            if max_discount:
                coupon_data['max_discount_amount'] = float(max_discount)
        
        coupon_service = CouponService()
        coupon_id, error = coupon_service.create_coupon(coupon_data, current_user.id)
        
        if coupon_id:
            flash('Coupon created successfully.', 'success')
            return redirect(url_for('coupons.list'))
        else:
            flash(error, 'danger')
    
    # Get available plans for coupon restrictions
    plan_service = PlanService()
    plans = plan_service.get_active_plans()
    return render_template('coupons/create.html', plans=plans, datetime=datetime)

@coupons_bp.route('/<coupon_id>/edit', methods=['GET', 'POST'])
@login_required
@owner_required
def edit(coupon_id):
    coupon_service = CouponService()
    coupon = coupon_service.get_coupon_by_id(coupon_id)
    
    if not coupon:
        flash('Coupon not found.', 'danger')
        return redirect(url_for('coupons.list'))
    
    if request.method == 'POST':
        update_data = {
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'discount_type': request.form.get('discount_type'),
            'discount_value': float(request.form.get('discount_value', 0)),
            'min_purchase_amount': float(request.form.get('min_purchase_amount', 0)),
            'usage_limit': int(request.form.get('usage_limit')) if request.form.get('usage_limit') else None,
            'valid_from': request.form.get('valid_from'),
            'valid_until': request.form.get('valid_until'),
            'applicable_plans': request.form.getlist('applicable_plans')
        }
        
        # Handle max discount amount for percentage discounts
        if update_data['discount_type'] == 'PERCENTAGE':
            max_discount = request.form.get('max_discount_amount')
            if max_discount:
                update_data['max_discount_amount'] = float(max_discount)
        
        # Add partner limits to update_data
        from models import get_users_collection
        users = get_users_collection()
        partners = users.find({'role': 'PARTNER'})
        
        for partner in partners:
            partner_id = str(partner['_id'])
            limit_value = request.form.get(f'partner_limit_{partner_id}')
            if limit_value:
                update_data[f'partner_limit_{partner_id}'] = limit_value
        
        success, message = coupon_service.update_coupon(coupon_id, update_data, current_user.id)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('coupons.list'))
        else:
            flash(message, 'danger')
    
    # Get data for form
    plan_service = PlanService()
    plans = plan_service.get_active_plans()
    
    # Get partners for limits
    from models import get_users_collection
    users = get_users_collection()
    partners_data = users.find({'role': 'PARTNER', 'is_active': True})
    partners = [User(p) for p in partners_data]
    
    return render_template('coupons/edit.html', 
                         coupon=coupon, 
                         plans=plans,
                         partners=partners)

@coupons_bp.route('/<coupon_id>/toggle-status', methods=['POST'])
@login_required
@owner_required
def toggle_status(coupon_id):
    coupon_service = CouponService()
    success, message = coupon_service.toggle_coupon_status(coupon_id, current_user.id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('coupons.list'))

# API endpoints
@coupons_bp.route('/api/list')
@login_required
def api_list():
    if not current_user.is_owner():
        return jsonify({'error': 'Unauthorized'}), 403
    
    page = request.args.get('page', 1, type=int)
    coupon_service = CouponService()
    result = coupon_service.get_all_coupons(page=page)
    
    coupons_data = []
    for coupon in result['coupons']:
        coupons_data.append({
            'id': coupon.id,
            'code': coupon.code,
            'name': coupon.name,
            'description': coupon.description,
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value,
            'min_purchase_amount': coupon.min_purchase_amount,
            'max_discount_amount': coupon.max_discount_amount,
            'usage_limit': coupon.usage_limit,
            'used_count': coupon.used_count,
            'valid_from': coupon.valid_from.isoformat() if coupon.valid_from else None,
            'valid_until': coupon.valid_until.isoformat() if coupon.valid_until else None,
            'is_active': coupon.is_active,
            'created_at': coupon.created_at.isoformat() if coupon.created_at else None
        })
    
    return jsonify({
        'success': True,
        'coupons': coupons_data,
        'total': result['total'],
        'page': result['page'],
        'total_pages': result['total_pages']
    })

@coupons_bp.route('/api/validate', methods=['POST'])
@login_required
def api_validate():
    data = request.get_json()
    code = data.get('code')
    amount = data.get('amount', 0)
    plan_id = data.get('plan_id')
    
    if not code:
        return jsonify({'success': False, 'error': 'Coupon code is required'}), 400
    
    coupon_service = CouponService()
    success, message, discount = coupon_service.validate_and_apply_coupon(code, amount, plan_id)
    
    return jsonify({
        'success': success,
        'message': message,
        'discount': discount,
        'final_amount': amount - discount if success else amount
    })
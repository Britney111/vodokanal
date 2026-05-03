# -*- coding: utf-8 -*-
from flask import Blueprint, jsonify, request
from flask_login import login_required
from app import db
from app.models import Product, Stock, Warehouse

api_bp = Blueprint('api', __name__)


@api_bp.route('/barcode/<string:code>')
@login_required
def barcode_lookup(code):
    """Поиск товара по штрихкоду или артикулу — вызывается со сканера"""
    code = code.strip()

    # Ищем сначала по штрихкоду, потом по артикулу
    product = Product.query.filter(
        Product.is_active == True,
        (Product.barcode == code) | (Product.article == code)
    ).first()

    if not product:
        return jsonify({'found': False, 'message': f'Товар со штрихкодом {code} не найден'}), 404

    stocks = Stock.query.filter_by(product_id=product.id).all()
    stock_info = [
        {
            'warehouse_id': s.warehouse_id,
            'warehouse_name': s.warehouse.name,
            'quantity': float(s.quantity),
        }
        for s in stocks
    ]

    return jsonify({
        'found': True,
        'product': {
            'id': product.id,
            'name': product.name,
            'article': product.article or '',
            'barcode': product.barcode or '',
            'category': product.category.name,
            'unit': product.unit.short_name,
            'price': float(product.price),
            'total_stock': float(product.total_stock),
            'min_stock': float(product.min_stock),
            'is_low_stock': product.is_low_stock,
        },
        'stocks': stock_info,
    })


@api_bp.route('/barcode/set', methods=['POST'])
@login_required
def barcode_set():
    """Привязать штрихкод к товару"""
    from flask_login import current_user
    if not current_user.is_manager:
        return jsonify({'error': 'Недостаточно прав'}), 403

    data = request.get_json()
    product_id = data.get('product_id')
    barcode = data.get('barcode', '').strip()

    if not product_id or not barcode:
        return jsonify({'error': 'Укажите товар и штрихкод'}), 400

    # Проверяем уникальность
    existing = Product.query.filter(
        Product.barcode == barcode,
        Product.id != product_id
    ).first()
    if existing:
        return jsonify({'error': f'Штрихкод уже используется товаром «{existing.name}»'}), 409

    product = Product.query.get_or_404(product_id)
    product.barcode = barcode
    db.session.commit()

    return jsonify({'success': True, 'message': f'Штрихкод {barcode} привязан к товару «{product.name}»'})


@login_required
def products_search():
    """AJAX поиск товаров для форм движения"""
    q = request.args.get('q', '')
    warehouse_id = request.args.get('warehouse_id', type=int)

    products = Product.query.filter(
        Product.is_active == True,
        (Product.name.ilike(f'%{q}%')) | (Product.article.ilike(f'%{q}%'))
    ).limit(20).all()

    result = []
    for p in products:
        stock_qty = 0
        if warehouse_id:
            stock = Stock.query.filter_by(product_id=p.id, warehouse_id=warehouse_id).first()
            stock_qty = float(stock.quantity) if stock else 0
        else:
            stock_qty = float(p.total_stock)

        result.append({
            'id': p.id,
            'name': p.name,
            'article': p.article or '',
            'unit': p.unit.short_name,
            'price': float(p.price),
            'stock': stock_qty,
        })

    return jsonify(result)


@api_bp.route('/stock/product/<int:product_id>')
@login_required
def product_stock(product_id):
    """Остатки конкретного товара по складам"""
    stocks = Stock.query.filter_by(product_id=product_id).all()
    return jsonify([{
        'warehouse_id': s.warehouse_id,
        'warehouse_name': s.warehouse.name,
        'quantity': float(s.quantity),
    } for s in stocks if s.quantity > 0])


@api_bp.route('/dashboard/stats')
@login_required
def dashboard_stats():
    """Данные для графиков на дашборде"""
    from app.models import Movement
    from sqlalchemy import func
    from datetime import datetime, timedelta

    # Движения за последние 30 дней по дням
    from_date = datetime.utcnow() - timedelta(days=30)
    daily = db.session.query(
        func.date(Movement.date).label('day'),
        Movement.movement_type,
        func.count(Movement.id).label('count')
    ).filter(
        Movement.date >= from_date,
        Movement.status == 'confirmed'
    ).group_by(func.date(Movement.date), Movement.movement_type).all()

    return jsonify([{
        'day': str(row.day),
        'type': row.movement_type,
        'count': row.count,
    } for row in daily])

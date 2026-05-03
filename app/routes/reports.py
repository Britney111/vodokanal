# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import func
from datetime import datetime
from app import db
from app.models import Product, Stock, Movement, MovementItem, Warehouse, Category

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')


@reports_bp.route('/stock')
@login_required
def stock_report():
    """Отчёт по остаткам на складах"""
    warehouse_id = request.args.get('warehouse_id', type=int)
    category_id = request.args.get('category_id', type=int)
    show_empty = request.args.get('show_empty', False, type=bool)

    query = db.session.query(
        Product, Stock, Warehouse
    ).join(Stock, Stock.product_id == Product.id
    ).join(Warehouse, Warehouse.id == Stock.warehouse_id
    ).filter(Product.is_active == True)

    if warehouse_id:
        query = query.filter(Stock.warehouse_id == warehouse_id)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if not show_empty:
        query = query.filter(Stock.quantity > 0)

    results = query.order_by(Product.name).all()

    warehouses = Warehouse.query.filter_by(is_active=True).all()
    categories = Category.query.order_by(Category.name).all()

    total_value = sum(float(s.quantity) * float(p.price) for p, s, w in results)

    return render_template('reports/stock.html',
        results=results,
        warehouses=warehouses,
        categories=categories,
        warehouse_id=warehouse_id,
        category_id=category_id,
        total_value=total_value,
    )


@reports_bp.route('/movements')
@login_required
def movements_report():
    """Отчёт по движению товаров за период"""
    date_from = request.args.get('date_from', datetime.now().strftime('%Y-%m-01'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    movement_type = request.args.get('movement_type', '')

    query = db.session.query(
        MovementItem, Movement, Product
    ).join(Movement, Movement.id == MovementItem.movement_id
    ).join(Product, Product.id == MovementItem.product_id
    ).filter(
        Movement.status == 'confirmed',
        Movement.date >= datetime.strptime(date_from, '%Y-%m-%d'),
        Movement.date <= datetime.strptime(date_to, '%Y-%m-%d'),
    )

    if movement_type:
        query = query.filter(Movement.movement_type == movement_type)

    results = query.order_by(Movement.date.desc()).all()

    # Сводка по типам
    summary = {}
    for item, movement, product in results:
        t = movement.movement_type
        if t not in summary:
            summary[t] = {'count': 0, 'total': 0}
        summary[t]['count'] += 1
        summary[t]['total'] += float(item.quantity) * float(item.price)

    return render_template('reports/movements.html',
        results=results,
        summary=summary,
        date_from=date_from,
        date_to=date_to,
        movement_type=movement_type,
    )


@reports_bp.route('/low-stock')
@login_required
def low_stock_report():
    """Отчёт по товарам с низким остатком"""
    all_products = Product.query.filter_by(is_active=True).all()
    low_stock = [p for p in all_products if p.is_low_stock]
    return render_template('reports/low_stock.html', products=low_stock)

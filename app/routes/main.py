# -*- coding: utf-8 -*-
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from app import db
from app.models import Product, Movement, Stock, Supplier, Category

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Статистика для дашборда
    total_products = Product.query.filter_by(is_active=True).count()
    total_suppliers = Supplier.query.filter_by(is_active=True).count()
    total_categories = Category.query.count()

    # Товары с низким остатком
    all_products = Product.query.filter_by(is_active=True).all()
    low_stock_products = [p for p in all_products if p.is_low_stock]

    # Последние движения
    recent_movements = Movement.query.order_by(
        Movement.created_at.desc()
    ).limit(10).all()

    # Движения за текущий месяц по типам
    from datetime import datetime
    now = datetime.utcnow()
    month_stats = db.session.query(
        Movement.movement_type,
        func.count(Movement.id).label('count')
    ).filter(
        func.extract('month', Movement.date) == now.month,
        func.extract('year', Movement.date) == now.year,
        Movement.status == 'confirmed'
    ).group_by(Movement.movement_type).all()

    month_data = {row.movement_type: row.count for row in month_stats}

    # Топ-5 товаров по количеству движений (убрано — использовалось некорректное join)

    return render_template('main/dashboard.html',
        total_products=total_products,
        total_suppliers=total_suppliers,
        total_categories=total_categories,
        low_stock_products=low_stock_products,
        recent_movements=recent_movements,
        month_data=month_data,
    )

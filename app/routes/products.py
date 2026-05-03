# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, Unit, Stock, Warehouse
from config import Config

products_bp = Blueprint('products', __name__)


@products_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    low_stock = request.args.get('low_stock', False, type=bool)

    query = Product.query.filter_by(is_active=True)

    if search:
        query = query.filter(
            (Product.name.ilike(f'%{search}%')) |
            (Product.article.ilike(f'%{search}%'))
        )
    if category_id:
        query = query.filter_by(category_id=category_id)

    products = query.order_by(Product.name).paginate(
        page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False
    )
    categories = Category.query.order_by(Category.name).all()

    return render_template('products/index.html',
        products=products, categories=categories,
        search=search, category_id=category_id
    )


@products_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if not current_user.is_manager:
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('products.index'))

    categories = Category.query.order_by(Category.name).all()
    units = Unit.query.order_by(Unit.name).all()

    if request.method == 'POST':
        product = Product(
            name=request.form['name'].strip(),
            article=request.form.get('article', '').strip() or None,
            barcode=request.form.get('barcode', '').strip() or None,
            category_id=request.form['category_id'],
            unit_id=request.form['unit_id'],
            description=request.form.get('description', '').strip(),
            min_stock=float(request.form.get('min_stock', 0)),
            price=float(request.form.get('price', 0)),
        )
        db.session.add(product)
        db.session.flush()  # получаем id

        # Создаём нулевые остатки на всех складах
        for warehouse in Warehouse.query.filter_by(is_active=True).all():
            stock = Stock(product_id=product.id, warehouse_id=warehouse.id, quantity=0)
            db.session.add(stock)

        db.session.commit()
        flash(f'Товар «{product.name}» успешно создан', 'success')
        return redirect(url_for('products.detail', id=product.id))

    return render_template('products/form.html', categories=categories, units=units, product=None)


@products_bp.route('/<int:id>')
@login_required
def detail(id):
    product = Product.query.get_or_404(id)
    stock_by_warehouse = Stock.query.filter_by(product_id=id).all()

    from app.models import MovementItem, Movement
    recent_movements = db.session.query(MovementItem, Movement).join(
        Movement, Movement.id == MovementItem.movement_id
    ).filter(
        MovementItem.product_id == id,
        Movement.status == 'confirmed'
    ).order_by(Movement.date.desc()).limit(20).all()

    return render_template('products/detail.html',
        product=product,
        stock_by_warehouse=stock_by_warehouse,
        recent_movements=recent_movements
    )


@products_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_manager:
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('products.index'))

    product = Product.query.get_or_404(id)
    categories = Category.query.order_by(Category.name).all()
    units = Unit.query.order_by(Unit.name).all()

    if request.method == 'POST':
        product.name = request.form['name'].strip()
        product.article = request.form.get('article', '').strip() or None
        product.barcode = request.form.get('barcode', '').strip() or None
        product.category_id = request.form['category_id']
        product.unit_id = request.form['unit_id']
        product.description = request.form.get('description', '').strip()
        product.min_stock = float(request.form.get('min_stock', 0))
        product.price = float(request.form.get('price', 0))
        db.session.commit()
        flash(f'Товар «{product.name}» обновлён', 'success')
        return redirect(url_for('products.detail', id=product.id))

    return render_template('products/form.html', categories=categories, units=units, product=product)


@products_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if not current_user.is_admin:
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('products.index'))

    product = Product.query.get_or_404(id)
    product.is_active = False  # Мягкое удаление
    db.session.commit()
    flash(f'Товар «{product.name}» деактивирован', 'warning')
    return redirect(url_for('products.index'))

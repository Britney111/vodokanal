# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from decimal import Decimal
from app import db
from app.models import Movement, MovementItem, Product, Warehouse, Supplier, Stock
from config import Config

movements_bp = Blueprint('movements', __name__)


@movements_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    movement_type = request.args.get('type', '')
    status = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Movement.query

    if movement_type:
        query = query.filter_by(movement_type=movement_type)
    if status:
        query = query.filter_by(status=status)
    if date_from:
        query = query.filter(Movement.date >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Movement.date <= datetime.strptime(date_to, '%Y-%m-%d'))

    movements = query.order_by(Movement.date.desc()).paginate(
        page=page, per_page=Config.ITEMS_PER_PAGE, error_out=False
    )

    return render_template('movements/index.html', movements=movements,
        movement_type=movement_type, status=status)


@movements_bp.route('/create/<string:mov_type>', methods=['GET', 'POST'])
@login_required
def create(mov_type):
    if mov_type not in ('receipt', 'expense', 'transfer', 'writeoff'):
        flash('Неверный тип документа', 'danger')
        return redirect(url_for('movements.index'))

    warehouses = Warehouse.query.filter_by(is_active=True).all()
    suppliers = Supplier.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()

    if request.method == 'POST':
        movement = Movement(
            movement_type=mov_type,
            warehouse_from_id=request.form.get('warehouse_from_id') or None,
            warehouse_to_id=request.form.get('warehouse_to_id') or None,
            supplier_id=request.form.get('supplier_id') or None,
            created_by=current_user.id,
            status='draft',
            notes=request.form.get('notes', '').strip(),
            date=datetime.now(),
        )
        movement.document_number = movement.generate_document_number()
        db.session.add(movement)
        db.session.flush()

        # Добавляем строки документа
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')

        for pid, qty, price in zip(product_ids, quantities, prices):
            if pid and qty:
                item = MovementItem(
                    movement_id=movement.id,
                    product_id=int(pid),
                    quantity=Decimal(qty),
                    price=Decimal(price) if price else Decimal(0),
                )
                db.session.add(item)

        db.session.commit()
        flash(f'Документ {movement.document_number} создан как черновик', 'success')
        return redirect(url_for('movements.detail', id=movement.id))

    return render_template('movements/form.html',
        mov_type=mov_type, warehouses=warehouses,
        suppliers=suppliers, products=products
    )


@movements_bp.route('/<int:id>')
@login_required
def detail(id):
    movement = Movement.query.get_or_404(id)
    items = movement.items.all()
    return render_template('movements/detail.html', movement=movement, items=items)


@movements_bp.route('/<int:id>/confirm', methods=['POST'])
@login_required
def confirm(id):
    """Проведение документа — изменяет остатки на складах"""
    if not current_user.is_manager:
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('movements.detail', id=id))

    movement = Movement.query.get_or_404(id)

    if movement.status != 'draft':
        flash('Документ уже проведён или отменён', 'warning')
        return redirect(url_for('movements.detail', id=id))

    # Применяем движение к остаткам
    error = _apply_movement(movement)
    if error:
        flash(error, 'danger')
        return redirect(url_for('movements.detail', id=id))

    movement.status = 'confirmed'
    db.session.commit()
    flash(f'Документ {movement.document_number} успешно проведён', 'success')
    return redirect(url_for('movements.detail', id=id))


@movements_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    """Отмена проведённого документа — откатывает остатки"""
    if not current_user.is_admin:
        flash('Только администратор может отменять документы', 'danger')
        return redirect(url_for('movements.detail', id=id))

    movement = Movement.query.get_or_404(id)

    if movement.status == 'confirmed':
        _rollback_movement(movement)

    movement.status = 'cancelled'
    db.session.commit()
    flash(f'Документ {movement.document_number} отменён', 'warning')
    return redirect(url_for('movements.detail', id=id))


def _get_or_create_stock(product_id, warehouse_id):
    stock = Stock.query.filter_by(
        product_id=product_id, warehouse_id=warehouse_id
    ).first()
    if not stock:
        stock = Stock(product_id=product_id, warehouse_id=warehouse_id, quantity=0)
        db.session.add(stock)
        db.session.flush()
    return stock


def _apply_movement(movement):
    """Основная логика изменения остатков при проведении документа"""
    for item in movement.items:
        qty = item.quantity

        if movement.movement_type == 'receipt':
            # Приход: увеличиваем остаток на складе-получателе
            stock = _get_or_create_stock(item.product_id, movement.warehouse_to_id)
            stock.quantity += qty

        elif movement.movement_type == 'expense':
            # Расход: уменьшаем остаток на складе-источнике
            stock = _get_or_create_stock(item.product_id, movement.warehouse_from_id)
            if stock.quantity < qty:
                product = Product.query.get(item.product_id)
                return f'Недостаточно товара «{product.name}» на складе. Доступно: {stock.quantity}'
            stock.quantity -= qty

        elif movement.movement_type == 'transfer':
            # Перемещение: уменьшаем на одном складе, увеличиваем на другом
            stock_from = _get_or_create_stock(item.product_id, movement.warehouse_from_id)
            if stock_from.quantity < qty:
                product = Product.query.get(item.product_id)
                return f'Недостаточно товара «{product.name}» на складе-источнике'
            stock_from.quantity -= qty
            stock_to = _get_or_create_stock(item.product_id, movement.warehouse_to_id)
            stock_to.quantity += qty

        elif movement.movement_type == 'writeoff':
            # Списание: уменьшаем остаток (фиксируем причину в notes)
            stock = _get_or_create_stock(item.product_id, movement.warehouse_from_id)
            if stock.quantity < qty:
                product = Product.query.get(item.product_id)
                return f'Недостаточно товара «{product.name}» для списания'
            stock.quantity -= qty

    return None  # Нет ошибок


def _rollback_movement(movement):
    """Откат остатков при отмене документа"""
    for item in movement.items:
        qty = item.quantity

        if movement.movement_type == 'receipt':
            stock = _get_or_create_stock(item.product_id, movement.warehouse_to_id)
            stock.quantity -= qty

        elif movement.movement_type in ('expense', 'writeoff'):
            stock = _get_or_create_stock(item.product_id, movement.warehouse_from_id)
            stock.quantity += qty

        elif movement.movement_type == 'transfer':
            stock_from = _get_or_create_stock(item.product_id, movement.warehouse_from_id)
            stock_to = _get_or_create_stock(item.product_id, movement.warehouse_to_id)
            stock_from.quantity += qty
            stock_to.quantity -= qty

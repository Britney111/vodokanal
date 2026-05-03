# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Supplier, Movement

suppliers_bp = Blueprint('suppliers', __name__)


@suppliers_bp.route('/')
@login_required
def index():
    search = request.args.get('search', '')
    query = Supplier.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            (Supplier.name.ilike(f'%{search}%')) |
            (Supplier.inn.ilike(f'%{search}%'))
        )
    suppliers = query.order_by(Supplier.name).all()
    return render_template('suppliers/index.html', suppliers=suppliers, search=search)


@suppliers_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if not current_user.is_manager:
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('suppliers.index'))

    if request.method == 'POST':
        supplier = Supplier(
            name=request.form['name'].strip(),
            inn=request.form.get('inn', '').strip() or None,
            kpp=request.form.get('kpp', '').strip() or None,
            contact_person=request.form.get('contact_person', '').strip(),
            phone=request.form.get('phone', '').strip(),
            email=request.form.get('email', '').strip(),
            address=request.form.get('address', '').strip(),
            notes=request.form.get('notes', '').strip(),
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f'Поставщик «{supplier.name}» добавлен', 'success')
        return redirect(url_for('suppliers.index'))

    return render_template('suppliers/form.html', supplier=None)


@suppliers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if not current_user.is_manager:
        flash('Недостаточно прав', 'danger')
        return redirect(url_for('suppliers.index'))

    supplier = Supplier.query.get_or_404(id)

    if request.method == 'POST':
        supplier.name = request.form['name'].strip()
        supplier.inn = request.form.get('inn', '').strip() or None
        supplier.kpp = request.form.get('kpp', '').strip() or None
        supplier.contact_person = request.form.get('contact_person', '').strip()
        supplier.phone = request.form.get('phone', '').strip()
        supplier.email = request.form.get('email', '').strip()
        supplier.address = request.form.get('address', '').strip()
        supplier.notes = request.form.get('notes', '').strip()
        db.session.commit()
        flash(f'Поставщик «{supplier.name}» обновлён', 'success')
        return redirect(url_for('suppliers.index'))

    return render_template('suppliers/form.html', supplier=supplier)

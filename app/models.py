# -*- coding: utf-8 -*-
"""
МОДЕЛИ БАЗЫ ДАННЫХ — Система учёта товаров на складе МУП «Водоканал» г. Ростов-на-Дону

Структура таблиц:
- users          — пользователи системы (кладовщики, менеджеры, администраторы)
- categories     — категории товаров (трубы, насосы, реагенты, инструменты и т.д.)
- units          — единицы измерения (шт., кг, м, л и т.д.)
- suppliers      — поставщики
- warehouses     — склады / складские помещения
- products       — товарные позиции (номенклатура)
- stock          — текущие остатки (product × warehouse)
- movements      — движение товаров (приход, расход, перемещение, списание)
- movement_items — строки документа движения
- write_offs     — акты списания
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


# ─────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛИ
# ─────────────────────────────────────────────

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='storekeeper')
    # Роли: admin (администратор), manager (менеджер), storekeeper (кладовщик)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Связи
    movements = db.relationship('Movement', backref='created_by_user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_manager(self):
        return self.role in ('admin', 'manager')

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ─────────────────────────────────────────────
# КАТЕГОРИИ ТОВАРОВ
# ─────────────────────────────────────────────

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True)          # Код категории (напр. ТР — трубы)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'))  # Иерархия категорий
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    products = db.relationship('Product', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'


# ─────────────────────────────────────────────
# ЕДИНИЦЫ ИЗМЕРЕНИЯ
# ─────────────────────────────────────────────

class Unit(db.Model):
    __tablename__ = 'units'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)   # Штука, Килограмм, Метр
    short_name = db.Column(db.String(10), unique=True, nullable=False)  # шт., кг, м

    products = db.relationship('Product', backref='unit', lazy='dynamic')

    def __repr__(self):
        return f'<Unit {self.short_name}>'


# ─────────────────────────────────────────────
# ПОСТАВЩИКИ
# ─────────────────────────────────────────────

class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    inn = db.Column(db.String(12), unique=True)           # ИНН
    kpp = db.Column(db.String(9))                         # КПП
    contact_person = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    # Связи
    movements = db.relationship('Movement', backref='supplier', lazy='dynamic')

    def __repr__(self):
        return f'<Supplier {self.name}>'


# ─────────────────────────────────────────────
# СКЛАДЫ
# ─────────────────────────────────────────────

class Warehouse(db.Model):
    __tablename__ = 'warehouses'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True)
    address = db.Column(db.Text)
    responsible_person = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)

    # Связи
    stock = db.relationship('Stock', backref='warehouse', lazy='dynamic')

    def __repr__(self):
        return f'<Warehouse {self.name}>'


# ─────────────────────────────────────────────
# ТОВАРЫ (номенклатура)
# ─────────────────────────────────────────────

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500), nullable=False)
    article = db.Column(db.String(100), unique=True)      # Артикул / номенклатурный номер
    barcode = db.Column(db.String(50), unique=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    description = db.Column(db.Text)
    min_stock = db.Column(db.Numeric(12, 3), default=0)   # Минимальный остаток
    price = db.Column(db.Numeric(12, 2), default=0)       # Учётная цена
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    stock = db.relationship('Stock', backref='product', lazy='dynamic')
    movement_items = db.relationship('MovementItem', backref='product', lazy='dynamic')

    @property
    def total_stock(self):
        """Суммарный остаток по всем складам"""
        from sqlalchemy import func
        result = db.session.query(func.sum(Stock.quantity)).filter(
            Stock.product_id == self.id
        ).scalar()
        return result or 0

    @property
    def is_low_stock(self):
        return self.total_stock <= self.min_stock and self.min_stock > 0

    def __repr__(self):
        return f'<Product {self.article}: {self.name[:50]}>'


# ─────────────────────────────────────────────
# ОСТАТКИ (product × warehouse)
# ─────────────────────────────────────────────

class Stock(db.Model):
    __tablename__ = 'stock'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('product_id', 'warehouse_id', name='uq_stock_product_warehouse'),
    )

    def __repr__(self):
        return f'<Stock product={self.product_id} warehouse={self.warehouse_id} qty={self.quantity}>'


# ─────────────────────────────────────────────
# ДВИЖЕНИЯ ТОВАРОВ (документы)
# ─────────────────────────────────────────────

class Movement(db.Model):
    __tablename__ = 'movements'

    id = db.Column(db.Integer, primary_key=True)
    document_number = db.Column(db.String(50), unique=True, nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)
    # Типы: receipt (приход), expense (расход), transfer (перемещение), writeoff (списание)

    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    warehouse_from_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))  # Откуда
    warehouse_to_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'))    # Куда
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))         # Поставщик (для прихода)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='draft')
    # Статусы: draft (черновик), confirmed (проведён), cancelled (отменён)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    items = db.relationship('MovementItem', backref='movement', lazy='dynamic',
                            cascade='all, delete-orphan')
    warehouse_from = db.relationship('Warehouse', foreign_keys=[warehouse_from_id])
    warehouse_to = db.relationship('Warehouse', foreign_keys=[warehouse_to_id])

    MOVEMENT_TYPES = {
        'receipt': 'Приход',
        'expense': 'Расход',
        'transfer': 'Перемещение',
        'writeoff': 'Списание'
    }

    @property
    def type_name(self):
        return self.MOVEMENT_TYPES.get(self.movement_type, self.movement_type)

    @property
    def total_amount(self):
        return sum(item.total_price for item in self.items)

    def generate_document_number(self):
        """Генерирует номер документа: тип/год/порядковый"""
        prefixes = {'receipt': 'ПРХ', 'expense': 'РСХ', 'transfer': 'ПРМ', 'writeoff': 'СПС'}
        prefix = prefixes.get(self.movement_type, 'ДОК')
        year = datetime.utcnow().year
        count = Movement.query.filter(
            Movement.movement_type == self.movement_type,
            db.extract('year', Movement.date) == year
        ).count() + 1
        return f'{prefix}-{year}-{count:05d}'

    def __repr__(self):
        return f'<Movement {self.document_number} ({self.movement_type})>'


# ─────────────────────────────────────────────
# СТРОКИ ДОКУМЕНТА ДВИЖЕНИЯ
# ─────────────────────────────────────────────

class MovementItem(db.Model):
    __tablename__ = 'movement_items'

    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey('movements.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    price = db.Column(db.Numeric(12, 2), default=0)       # Цена на момент движения
    notes = db.Column(db.String(500))

    @property
    def total_price(self):
        return float(self.quantity) * float(self.price)

    def __repr__(self):
        return f'<MovementItem movement={self.movement_id} product={self.product_id} qty={self.quantity}>'

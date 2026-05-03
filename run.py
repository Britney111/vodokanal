# -*- coding: utf-8 -*-
from app import create_app, db
from app.models import User, Product, Category, Unit, Supplier, Warehouse, Stock, Movement, MovementItem
import click
import os

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 'User': User, 'Product': Product,
        'Category': Category, 'Unit': Unit, 'Supplier': Supplier,
        'Warehouse': Warehouse, 'Stock': Stock,
        'Movement': Movement, 'MovementItem': MovementItem,
    }


@app.cli.command('init-db')
def init_db():
    db.create_all()
    click.echo('Таблицы созданы')


@app.cli.command('seed')
def seed():
    from app.seed import seed_all
    seed_all()


@app.cli.command('create-admin')
@click.argument('username')
@click.argument('password')
def create_admin(username, password):
    user = User(
        username=username,
        email=f'{username}@vodokanal-rostov.ru',
        full_name='Администратор системы',
        role='admin'
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f'Администратор {username} создан')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug, host='0.0.0.0', port=port)

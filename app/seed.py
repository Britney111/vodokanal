# -*- coding: utf-8 -*-
"""
Скрипт заполнения БД тестовыми данными
МУП «Водоканал» г. Ростов-на-Дону

Запуск: flask seed
"""

from datetime import datetime, timedelta
from decimal import Decimal
import random
from app import db
from app.models import User, Category, Unit, Supplier, Warehouse, Product, Stock, Movement, MovementItem


def seed_all():
    print("🌱 Начинаем заполнение базы данных...")

    # ── Пользователи ──────────────────────────────────────
    users_data = [
        ('admin', 'admin@vodokanal-rostov.ru', 'admin123', 'Иванов Алексей Петрович', 'admin'),
        ('manager1', 'petrov@vodokanal-rostov.ru', 'manager123', 'Петров Сергей Николаевич', 'manager'),
        ('storekeeper1', 'sidorova@vodokanal-rostov.ru', 'store123', 'Сидорова Елена Владимировна', 'storekeeper'),
        ('storekeeper2', 'kozlov@vodokanal-rostov.ru', 'store123', 'Козлов Дмитрий Александрович', 'storekeeper'),
    ]
    users = {}
    for username, email, pwd, full_name, role in users_data:
        if not User.query.filter_by(username=username).first():
            u = User(username=username, email=email, full_name=full_name, role=role)
            u.set_password(pwd)
            db.session.add(u)
            users[username] = u
    db.session.flush()
    admin = User.query.filter_by(username='admin').first()
    print(f"  ✓ Пользователи созданы")

    # ── Единицы измерения ──────────────────────────────────
    units_data = [
        ('Штука', 'шт.'), ('Килограмм', 'кг'), ('Грамм', 'г'),
        ('Метр', 'м'), ('Метр квадратный', 'м²'), ('Литр', 'л'),
        ('Упаковка', 'уп.'), ('Комплект', 'компл.'), ('Тонна', 'т'),
        ('Пара', 'пар'), ('Рулон', 'рул.'),
    ]
    units = {}
    for name, short in units_data:
        if not Unit.query.filter_by(short_name=short).first():
            u = Unit(name=name, short_name=short)
            db.session.add(u)
            units[short] = u
    db.session.flush()
    units = {u.short_name: u for u in Unit.query.all()}
    print(f"  ✓ Единицы измерения созданы")

    # ── Категории ──────────────────────────────────────────
    categories_data = [
        ('Трубопроводная арматура', 'ТА', 'Задвижки, краны, вентили, клапаны'),
        ('Трубы и фитинги', 'ТФ', 'Трубы ПВХ, ВЧШГ, стальные; фитинги'),
        ('Насосное оборудование', 'НО', 'Насосы, насосные агрегаты, запчасти к насосам'),
        ('Электрооборудование', 'ЭО', 'Кабели, щиты управления, двигатели, частотные преобразователи'),
        ('Реагенты и химикаты', 'РХ', 'Хлор, коагулянты, флокулянты, антискаланты'),
        ('Средства защиты (СИЗ)', 'СИЗ', 'Каски, перчатки, комбинезоны, маски, ботинки'),
        ('Инструмент', 'ИНС', 'Ручной и электроинструмент, измерительные приборы'),
        ('Расходные материалы', 'РМ', 'Прокладки, болты, гайки, шайбы, уплотнители'),
        ('Спецодежда', 'СО', 'Рабочие костюмы, куртки, жилеты, рукавицы'),
        ('КИПиА', 'КИП', 'Датчики давления, расходомеры, манометры, контроллеры'),
    ]
    categories = {}
    for name, code, desc in categories_data:
        if not Category.query.filter_by(code=code).first():
            c = Category(name=name, code=code, description=desc)
            db.session.add(c)
    db.session.flush()
    categories = {c.code: c for c in Category.query.all()}
    print(f"  ✓ Категории созданы")

    # ── Поставщики ─────────────────────────────────────────
    suppliers_data = [
        ('ООО «РостовСпецТрейд»', '6163123456', '616301001', 'Мороз Андрей Викторович', '+7-863-200-11-22', 'g.Rostov-na-Donu, ul.Lenina 45'),
        ('АО «Водопроводные технологии»', '7707654321', '770701001', 'Климова Ирина Сергеевна', '+7-495-300-44-55', 'g.Moskva, Varshavskoe sh. 78'),
        ('ООО «ЮгХимПром»', '6155789012', '615501001', 'Зайцев Олег Михайлович', '+7-863-250-66-77', 'g.Rostov-na-Donu, pr.Sholokhova 122'),
        ('ООО «ЭлектроДон»', '6140890123', '614001001', 'Баранов Павел Олегович', '+7-863-210-88-99', 'g.Rostov-na-Donu, ul.Bol\'shaya Sadovaya 171'),
        ('ЗАО «НасосМаш»', '7812012345', '781201001', 'Соколов Игорь Дмитриевич', '+7-812-400-22-33', 'g.Sankt-Peterburg, Moskovskiy pr. 212'),
        ('ООО «РегионСнаб»', '6163555666', '616301002', 'Фролова Наталья Ивановна', '+7-863-280-00-11', 'g.Rostov-na-Donu, ul.Tekucheva 101'),
    ]
    suppliers = []
    for name, inn, kpp, contact, phone, addr in suppliers_data:
        if not Supplier.query.filter_by(inn=inn).first():
            s = Supplier(name=name, inn=inn, kpp=kpp, contact_person=contact, phone=phone, address=addr)
            db.session.add(s)
    db.session.flush()
    suppliers = Supplier.query.all()
    print(f"  ✓ Поставщики созданы")

    # ── Склады ─────────────────────────────────────────────
    warehouses_data = [
        ('Центральный склад', 'ЦС-01', 'г. Ростов-на-Дону, ул. Береговая, 24', 'Козлов Д.А.'),
        ('Склад реагентов', 'РХ-01', 'г. Ростов-на-Дону, ул. Береговая, 24 (корп. 2)', 'Сидорова Е.В.'),
        ('Склад насосной станции №1', 'НС-01', 'г. Ростов-на-Дону, пр. Ленина, 88', 'Козлов Д.А.'),
        ('Склад аварийного запаса', 'АЗ-01', 'г. Ростов-на-Дону, ул. Береговая, 26', 'Петров С.Н.'),
    ]
    for name, code, addr, resp in warehouses_data:
        if not Warehouse.query.filter_by(code=code).first():
            w = Warehouse(name=name, code=code, address=addr, responsible_person=resp)
            db.session.add(w)
    db.session.flush()
    warehouses = Warehouse.query.all()
    wh_main = Warehouse.query.filter_by(code='ЦС-01').first()
    wh_chem = Warehouse.query.filter_by(code='РХ-01').first()
    print(f"  ✓ Склады созданы")

    # ── Товары ─────────────────────────────────────────────
    products_data = [
        # (name, article, category_code, unit_short, min_stock, price)
        ('Задвижка клиновая Ду100 Ру16', 'ЗКЛ-100-16', 'ТА', 'шт.', 5, 4800),
        ('Задвижка клиновая Ду150 Ру16', 'ЗКЛ-150-16', 'ТА', 'шт.', 3, 7200),
        ('Кран шаровой Ду25 Ру40', 'КШ-25-40', 'ТА', 'шт.', 10, 650),
        ('Вентиль запорный Ду50 Ру16', 'ВЗ-50-16', 'ТА', 'шт.', 8, 1100),
        ('Клапан обратный Ду100 Ру16', 'КО-100-16', 'ТА', 'шт.', 4, 3200),
        ('Труба ПВХ Ду110 SDR26 (м)', 'ТПВ-110', 'ТФ', 'м', 50, 280),
        ('Труба ВЧШГ Ду100 L=6м', 'ТВЧ-100-6', 'ТФ', 'шт.', 20, 4100),
        ('Отвод ПВХ Ду110 90°', 'ОТВ-110-90', 'ТФ', 'шт.', 30, 180),
        ('Тройник ПВХ Ду110', 'ТРЙ-110', 'ТФ', 'шт.', 20, 220),
        ('Муфта ремонтная Ду100', 'МР-100', 'ТФ', 'шт.', 15, 890),
        ('Насос центробежный KSB ETA 65-315', 'НЦ-KSB-65', 'НО', 'шт.', 1, 125000),
        ('Насос погружной Grundfos SP 3-18', 'НП-GF-SP3', 'НО', 'шт.', 2, 48000),
        ('Уплотнение торцевое DN65', 'УТ-65', 'НО', 'шт.', 5, 2400),
        ('Рабочее колесо насоса KSB Ø250', 'РК-KSB-250', 'НО', 'шт.', 2, 15000),
        ('Гипохлорит натрия 15% (1 т МКР)', 'ГХН-15-1Т', 'РХ', 'т', 5, 18500),
        ('Полиакриламид (ПАА) 25 кг', 'ПАА-25', 'РХ', 'уп.', 10, 3200),
        ('Сульфат алюминия 25 кг', 'СА-25', 'РХ', 'уп.', 20, 1400),
        ('Известь хлорная 25 кг', 'ИХ-25', 'РХ', 'уп.', 15, 850),
        ('Каска строительная UVEX белая', 'КСТ-БЕЛ', 'СИЗ', 'шт.', 20, 450),
        ('Перчатки КЩС тип 2 (пара)', 'ПКЩС-2', 'СИЗ', 'пар', 50, 320),
        ('Очки защитные закрытые', 'ОЗЗ-01', 'СИЗ', 'шт.', 20, 180),
        ('Костюм сварщика брезентовый р.52-54', 'КСВ-52', 'СО', 'шт.', 5, 3800),
        ('Жилет сигнальный 2 кл. р.L', 'ЖС-2-L', 'СО', 'шт.', 15, 350),
        ('Датчик давления ОВЕН ПД100-ДИ', 'ДД-ОВЕН-ДИ', 'КИП', 'шт.', 3, 8500),
        ('Расходомер электромагнитный Ду100', 'РЭМ-100', 'КИП', 'шт.', 1, 42000),
        ('Кабель ВВГнг 3х2.5 (м)', 'КБ-ВВГ-3х2.5', 'ЭО', 'м', 100, 95),
        ('Автомат АВВ SH203 C16', 'АВТ-SH203-16', 'ЭО', 'шт.', 10, 480),
        ('Ключ разводной 300мм', 'КЛ-РАЗ-300', 'ИНС', 'шт.', 5, 650),
        ('Прокладка паронитовая Ду100 (уп.10шт)', 'ПР-ПАР-100', 'РМ', 'уп.', 5, 280),
        ('Болт М16х60 DIN933 (уп.50шт)', 'БЛТ-М16-60', 'РМ', 'уп.', 10, 420),
    ]

    created_products = []
    for name, article, cat_code, unit_sh, min_st, price in products_data:
        if not Product.query.filter_by(article=article).first():
            cat = categories.get(cat_code)
            unit = units.get(unit_sh)
            if cat and unit:
                p = Product(
                    name=name, article=article,
                    category_id=cat.id, unit_id=unit.id,
                    min_stock=min_st, price=price
                )
                db.session.add(p)
                created_products.append(p)
    db.session.flush()
    all_products = Product.query.all()
    print(f"  ✓ Товары созданы ({len(all_products)} позиций)")

    # ── Остатки ────────────────────────────────────────────
    for product in all_products:
        for warehouse in warehouses:
            if not Stock.query.filter_by(product_id=product.id, warehouse_id=warehouse.id).first():
                # Центральный склад — основные остатки
                if warehouse.code == 'ЦС-01':
                    qty = random.randint(int(product.min_stock), int(product.min_stock) * 5 + 20)
                elif warehouse.code == 'АЗ-01':
                    qty = random.randint(0, int(product.min_stock) + 5)
                else:
                    qty = random.randint(0, 10)
                s = Stock(product_id=product.id, warehouse_id=warehouse.id, quantity=qty)
                db.session.add(s)
    db.session.flush()
    print(f"  ✓ Остатки на складах заполнены")

    # ── Документы движения ─────────────────────────────────
    mov_count = 0
    for i in range(20):
        days_ago = random.randint(1, 60)
        mov_date = datetime.utcnow() - timedelta(days=days_ago)
        mov_type = random.choice(['receipt', 'expense', 'writeoff'])

        movement = Movement(
            movement_type=mov_type,
            date=mov_date,
            created_by=admin.id,
            status='confirmed',
            notes=f'Тестовый документ #{i+1}',
        )
        if mov_type == 'receipt':
            movement.warehouse_to_id = wh_main.id
            movement.supplier_id = random.choice(suppliers).id
        else:
            movement.warehouse_from_id = wh_main.id

        movement.document_number = f'{"ПРХ" if mov_type=="receipt" else "РСХ" if mov_type=="expense" else "СПС"}-2024-{i+1:05d}'
        db.session.add(movement)
        db.session.flush()

        # Добавляем 1-5 строк
        sample_products = random.sample(all_products, min(random.randint(1, 5), len(all_products)))
        for prod in sample_products:
            qty = random.randint(1, 10)
            item = MovementItem(
                movement_id=movement.id,
                product_id=prod.id,
                quantity=qty,
                price=prod.price,
            )
            db.session.add(item)
        mov_count += 1

    db.session.commit()
    print(f"  ✓ Документы движения созданы ({mov_count} документов)")
    print("\n✅ База данных успешно заполнена!")
    print("\n📋 Учётные данные:")
    print("   Администратор: admin / admin123")
    print("   Менеджер:      manager1 / manager123")
    print("   Кладовщик:     storekeeper1 / store123")

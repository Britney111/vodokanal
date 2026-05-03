-- ============================================================
-- СИСТЕМА УЧЁТА ТОВАРОВ НА СКЛАДЕ
-- МУП «Водоканал» г. Ростов-на-Дону
-- ============================================================
-- Автор: Дипломная работа, 2024
-- СУБД: PostgreSQL 15+
-- Исполнить в pgAdmin: Tools → Query Tool → запустить этот файл
-- ============================================================

-- Очистка (осторожно на продакшене!)
DROP TABLE IF EXISTS movement_items CASCADE;
DROP TABLE IF EXISTS movements CASCADE;
DROP TABLE IF EXISTS stock CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;
DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS units CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ─────────────────────────────────────────────
-- 1. ПОЛЬЗОВАТЕЛИ СИСТЕМЫ
-- ─────────────────────────────────────────────
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64)  UNIQUE NOT NULL,
    email         VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    full_name     VARCHAR(200) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'storekeeper'
                  CHECK (role IN ('admin', 'manager', 'storekeeper')),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT NOW(),
    last_login    TIMESTAMP
);

COMMENT ON TABLE  users             IS 'Пользователи системы учёта';
COMMENT ON COLUMN users.role        IS 'admin — администратор, manager — менеджер, storekeeper — кладовщик';
COMMENT ON COLUMN users.is_active   IS 'Мягкое удаление: FALSE = деактивирован';

-- ─────────────────────────────────────────────
-- 2. КАТЕГОРИИ ТОВАРОВ (иерархия)
-- ─────────────────────────────────────────────
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) UNIQUE NOT NULL,
    code        VARCHAR(20)  UNIQUE,
    description TEXT,
    parent_id   INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE  categories           IS 'Категории номенклатуры (поддерживает иерархию)';
COMMENT ON COLUMN categories.code      IS 'Краткий код: ТА — трубопроводная арматура, НО — насосное оборудование и т.д.';
COMMENT ON COLUMN categories.parent_id IS 'Ссылка на родительскую категорию (для подкатегорий)';

-- ─────────────────────────────────────────────
-- 3. ЕДИНИЦЫ ИЗМЕРЕНИЯ
-- ─────────────────────────────────────────────
CREATE TABLE units (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(50) UNIQUE NOT NULL,
    short_name VARCHAR(10) UNIQUE NOT NULL
);

COMMENT ON TABLE  units            IS 'Единицы измерения товаров';
COMMENT ON COLUMN units.short_name IS 'Сокращение для отображения в таблицах: шт., кг, м, л и т.д.';

-- ─────────────────────────────────────────────
-- 4. ПОСТАВЩИКИ
-- ─────────────────────────────────────────────
CREATE TABLE suppliers (
    id             SERIAL PRIMARY KEY,
    name           VARCHAR(300) NOT NULL,
    inn            VARCHAR(12)  UNIQUE,
    kpp            VARCHAR(9),
    contact_person VARCHAR(200),
    phone          VARCHAR(20),
    email          VARCHAR(120),
    address        TEXT,
    is_active      BOOLEAN NOT NULL DEFAULT TRUE,
    notes          TEXT,
    created_at     TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE  suppliers           IS 'Поставщики материально-технических ресурсов';
COMMENT ON COLUMN suppliers.inn       IS 'ИНН — 10 цифр для юрлиц, 12 для ИП';
COMMENT ON COLUMN suppliers.kpp       IS 'КПП — 9 цифр, только для юридических лиц';
COMMENT ON COLUMN suppliers.is_active IS 'Мягкое удаление';

-- ─────────────────────────────────────────────
-- 5. СКЛАДЫ / СКЛАДСКИЕ ПОМЕЩЕНИЯ
-- ─────────────────────────────────────────────
CREATE TABLE warehouses (
    id                 SERIAL PRIMARY KEY,
    name               VARCHAR(200) NOT NULL,
    code               VARCHAR(20)  UNIQUE,
    address            TEXT,
    responsible_person VARCHAR(200),
    is_active          BOOLEAN NOT NULL DEFAULT TRUE
);

COMMENT ON TABLE  warehouses                    IS 'Склады предприятия';
COMMENT ON COLUMN warehouses.code               IS 'Короткий код склада: ЦС-01, НС-01 и т.д.';
COMMENT ON COLUMN warehouses.responsible_person IS 'ФИО материально ответственного лица';

-- ─────────────────────────────────────────────
-- 6. ТОВАРЫ (номенклатура)
-- ─────────────────────────────────────────────
CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(500) NOT NULL,
    article     VARCHAR(100) UNIQUE,
    barcode     VARCHAR(50)  UNIQUE,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    unit_id     INTEGER NOT NULL REFERENCES units(id),
    description TEXT,
    min_stock   NUMERIC(12,3) NOT NULL DEFAULT 0,
    price       NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE  products           IS 'Номенклатура товарно-материальных ценностей';
COMMENT ON COLUMN products.article   IS 'Артикул / номенклатурный номер';
COMMENT ON COLUMN products.min_stock IS 'Минимальный страховой запас — при достижении система сигнализирует';
COMMENT ON COLUMN products.price     IS 'Учётная цена за единицу измерения';
COMMENT ON COLUMN products.is_active IS 'Мягкое удаление: деактивированные позиции не отображаются';

-- Индексы для ускорения поиска
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_name ON products USING GIN (to_tsvector('russian', name));

-- ─────────────────────────────────────────────
-- 7. ОСТАТКИ (product × warehouse)
-- ─────────────────────────────────────────────
CREATE TABLE stock (
    id           SERIAL PRIMARY KEY,
    product_id   INTEGER NOT NULL REFERENCES products(id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
    quantity     NUMERIC(12,3) NOT NULL DEFAULT 0,
    updated_at   TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_stock_product_warehouse UNIQUE (product_id, warehouse_id)
);

COMMENT ON TABLE  stock              IS 'Текущие складские остатки — срез на текущий момент';
COMMENT ON COLUMN stock.quantity     IS 'Текущий остаток. Изменяется при проведении документов';

CREATE INDEX idx_stock_product ON stock(product_id);
CREATE INDEX idx_stock_warehouse ON stock(warehouse_id);

-- ─────────────────────────────────────────────
-- 8. ДВИЖЕНИЯ ТОВАРОВ (заголовки документов)
-- ─────────────────────────────────────────────
CREATE TABLE movements (
    id               SERIAL PRIMARY KEY,
    document_number  VARCHAR(50) UNIQUE NOT NULL,
    movement_type    VARCHAR(20) NOT NULL
                     CHECK (movement_type IN ('receipt','expense','transfer','writeoff')),
    date             TIMESTAMP NOT NULL DEFAULT NOW(),
    warehouse_from_id INTEGER REFERENCES warehouses(id),
    warehouse_to_id   INTEGER REFERENCES warehouses(id),
    supplier_id       INTEGER REFERENCES suppliers(id),
    created_by        INTEGER NOT NULL REFERENCES users(id),
    status            VARCHAR(20) NOT NULL DEFAULT 'draft'
                      CHECK (status IN ('draft','confirmed','cancelled')),
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE  movements                  IS 'Документы движения ТМЦ';
COMMENT ON COLUMN movements.movement_type    IS 'receipt=приход, expense=расход, transfer=перемещение, writeoff=списание';
COMMENT ON COLUMN movements.status           IS 'draft=черновик (не влияет на остатки), confirmed=проведён, cancelled=отменён';
COMMENT ON COLUMN movements.warehouse_from_id IS 'Склад-источник (расход, перемещение, списание)';
COMMENT ON COLUMN movements.warehouse_to_id   IS 'Склад-получатель (приход, перемещение)';

CREATE INDEX idx_movements_type   ON movements(movement_type);
CREATE INDEX idx_movements_date   ON movements(date DESC);
CREATE INDEX idx_movements_status ON movements(status);

-- ─────────────────────────────────────────────
-- 9. СТРОКИ ДОКУМЕНТОВ ДВИЖЕНИЯ
-- ─────────────────────────────────────────────
CREATE TABLE movement_items (
    id          SERIAL PRIMARY KEY,
    movement_id INTEGER       NOT NULL REFERENCES movements(id) ON DELETE CASCADE,
    product_id  INTEGER       NOT NULL REFERENCES products(id),
    quantity    NUMERIC(12,3) NOT NULL CHECK (quantity > 0),
    price       NUMERIC(12,2) NOT NULL DEFAULT 0,
    notes       VARCHAR(500)
);

COMMENT ON TABLE  movement_items         IS 'Позиции (строки) документов движения';
COMMENT ON COLUMN movement_items.price   IS 'Цена на момент проведения документа (фиксируется исторически)';
COMMENT ON COLUMN movement_items.quantity IS 'Количество: строго больше 0';

CREATE INDEX idx_movement_items_movement ON movement_items(movement_id);
CREATE INDEX idx_movement_items_product  ON movement_items(product_id);

-- ─────────────────────────────────────────────
-- ПРЕДСТАВЛЕНИЯ (для отчётов в pgAdmin)
-- ─────────────────────────────────────────────

-- Остатки с расшифровкой
CREATE VIEW v_stock_full AS
SELECT
    p.article,
    p.name AS product_name,
    c.name AS category,
    u.short_name AS unit,
    w.name AS warehouse,
    s.quantity,
    p.min_stock,
    p.price,
    s.quantity * p.price AS total_value,
    CASE WHEN s.quantity <= p.min_stock AND p.min_stock > 0 THEN 'ДЕФИЦИТ' ELSE 'НОРМА' END AS stock_status,
    s.updated_at
FROM stock s
JOIN products   p ON p.id = s.product_id
JOIN categories c ON c.id = p.category_id
JOIN units      u ON u.id = p.unit_id
JOIN warehouses w ON w.id = s.warehouse_id
WHERE p.is_active = TRUE
ORDER BY c.name, p.name;

COMMENT ON VIEW v_stock_full IS 'Полный отчёт по остаткам с расшифровкой — удобно смотреть в pgAdmin';

-- Оборотная ведомость
CREATE VIEW v_turnover AS
SELECT
    p.name AS product_name,
    p.article,
    m.movement_type,
    SUM(mi.quantity) AS total_quantity,
    SUM(mi.quantity * mi.price) AS total_amount,
    COUNT(DISTINCT m.id) AS doc_count,
    DATE_TRUNC('month', m.date) AS month
FROM movement_items mi
JOIN movements m ON m.id = mi.movement_id
JOIN products  p ON p.id = mi.product_id
WHERE m.status = 'confirmed'
GROUP BY p.id, p.name, p.article, m.movement_type, DATE_TRUNC('month', m.date)
ORDER BY month DESC, total_amount DESC;

COMMENT ON VIEW v_turnover IS 'Оборотная ведомость по товарам — движение по месяцам';

-- Сводка по складам
CREATE VIEW v_warehouse_summary AS
SELECT
    w.name AS warehouse,
    w.code,
    COUNT(DISTINCT s.product_id) AS product_count,
    SUM(s.quantity * p.price) AS total_value
FROM stock s
JOIN warehouses w ON w.id = s.warehouse_id
JOIN products   p ON p.id = s.product_id
WHERE s.quantity > 0 AND p.is_active = TRUE
GROUP BY w.id, w.name, w.code
ORDER BY total_value DESC;

COMMENT ON VIEW v_warehouse_summary IS 'Сводка по складам: количество позиций и общая стоимость';

-- ─────────────────────────────────────────────
-- ТРИГГЕР: автообновление updated_at у products
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_products_updated
BEFORE UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_stock_updated
BEFORE UPDATE ON stock
FOR EACH ROW EXECUTE FUNCTION update_timestamp();

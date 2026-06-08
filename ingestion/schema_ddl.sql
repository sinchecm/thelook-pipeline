-- ─────────────────────────────────────────────────────────────────
--  TheLook pipeline — raw schema DDL
--  Run once in Supabase SQL editor (or via psql) before ingestion.
--  These tables are 1:1 mirrors of the BigQuery source columns.
-- ─────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS marts;

GRANT ALL ON SCHEMA raw, staging, intermediate, marts TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA raw          GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging      GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA intermediate GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts        GRANT ALL ON TABLES TO postgres;

-- ── raw.orders ────────────────────────────────────────────────────
DROP TABLE IF EXISTS raw.orders;
CREATE TABLE raw.orders (
    order_id        BIGINT,
    user_id         BIGINT,
    status          TEXT,
    gender          TEXT,
    created_at      TIMESTAMP,
    returned_at     TIMESTAMP,
    shipped_at      TIMESTAMP,
    delivered_at    TIMESTAMP,
    num_of_item     INT
);

-- ── raw.order_items ───────────────────────────────────────────────
DROP TABLE IF EXISTS raw.order_items;
CREATE TABLE raw.order_items (
    id                  BIGINT,
    order_id            BIGINT,
    user_id             BIGINT,
    product_id          BIGINT,
    inventory_item_id   BIGINT,
    status              TEXT,
    created_at          TIMESTAMP,
    shipped_at          TIMESTAMP,
    delivered_at        TIMESTAMP,
    returned_at         TIMESTAMP,
    sale_price          NUMERIC(10,2)
);

-- ── raw.users ─────────────────────────────────────────────────────
DROP TABLE IF EXISTS raw.users;
CREATE TABLE raw.users (
    id              BIGINT,
    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    age             INT,
    gender          TEXT,
    state           TEXT,
    street_address  TEXT,
    postal_code     TEXT,
    city            TEXT,
    country         TEXT,
    latitude        NUMERIC(10,6),
    longitude       NUMERIC(10,6),
    traffic_source  TEXT,
    created_at      TIMESTAMP
);

-- ── raw.products ──────────────────────────────────────────────────
DROP TABLE IF EXISTS raw.products;
CREATE TABLE raw.products (
    id                      BIGINT,
    cost                    NUMERIC(10,2),
    category                TEXT,
    name                    TEXT,
    brand                   TEXT,
    retail_price            NUMERIC(10,2),
    department              TEXT,
    sku                     TEXT,
    distribution_center_id  BIGINT
);

-- ── raw.inventory_items ───────────────────────────────────────────
DROP TABLE IF EXISTS raw.inventory_items;
CREATE TABLE raw.inventory_items (
    id                              BIGINT,
    product_id                      BIGINT,
    created_at                      TIMESTAMP,
    sold_at                         TIMESTAMP,
    cost                            NUMERIC(10,2),
    product_category                TEXT,
    product_name                    TEXT,
    product_brand                   TEXT,
    product_retail_price            NUMERIC(10,2),
    product_department              TEXT,
    product_sku                     TEXT,
    product_distribution_center_id  BIGINT
);

-- ── raw.events ────────────────────────────────────────────────────
DROP TABLE IF EXISTS raw.events;
CREATE TABLE raw.events (
    id              BIGINT,
    user_id         BIGINT,
    sequence_number INT,
    session_id      TEXT,
    created_at      TIMESTAMP,
    ip_address      TEXT,
    city            TEXT,
    state           TEXT,
    postal_code     TEXT,
    browser         TEXT,
    traffic_source  TEXT,
    uri             TEXT,
    event_type      TEXT
);

-- ── raw.distribution_centers ──────────────────────────────────────
DROP TABLE IF EXISTS raw.distribution_centers;
CREATE TABLE raw.distribution_centers (
    id          BIGINT,
    name        TEXT,
    latitude    NUMERIC(10,6),
    longitude   NUMERIC(10,6)
);

-- ── Verify ────────────────────────────────────────────────────────
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('raw','staging','intermediate','marts')
ORDER BY schema_name;

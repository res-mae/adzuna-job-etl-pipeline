
CREATE TABLE jobs (
    id                  TEXT PRIMARY KEY,
    title               TEXT,
    company_name        TEXT,
    location_name       TEXT,
    category_label      TEXT,
    category_tag        TEXT,
    contract_time       TEXT NOT NULL,
    contract_type       TEXT NOT NULL,
    salary_min          NUMERIC NOT NULL,
    salary_max          NUMERIC NOT NULL,
    salary_is_predicted BOOLEAN NOT NULL,
    created             TIMESTAMPTZ NOT NULL,
    redirect_url        TEXT,
    description         TEXT
);
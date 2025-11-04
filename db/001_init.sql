BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_name TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email CITEXT NOT NULL UNIQUE,
    contact_phone TEXT,
    segment TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'NEW',
    drive_folder_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS doc_requirements (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    doc_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    upload_url TEXT,
    drive_file_id TEXT,
    last_chased_at TIMESTAMPTZ,
    meta JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS doc_requirements_client_doc_type_idx
    ON doc_requirements(client_id, doc_type);

CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    scheduled_at TIMESTAMPTZ,
    duration_minutes INTEGER DEFAULT 60,
    platform TEXT,
    calendar_event_id TEXT,
    status TEXT NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS sessions_client_id_idx ON sessions(client_id);
CREATE INDEX IF NOT EXISTS sessions_calendar_event_id_idx ON sessions(calendar_event_id);

CREATE TABLE IF NOT EXISTS events_audit (
    id BIGSERIAL PRIMARY KEY,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    actor TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS events_audit_idempotency_idx
    ON events_audit(client_id, event_type, (payload->>'id'))
    WHERE payload ? 'id';

CREATE INDEX IF NOT EXISTS events_audit_client_id_idx ON events_audit(client_id);
CREATE INDEX IF NOT EXISTS doc_requirements_status_idx ON doc_requirements(status);
CREATE INDEX IF NOT EXISTS clients_status_idx ON clients(status);

COMMIT;

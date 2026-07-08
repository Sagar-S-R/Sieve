-- Database initialization script for Sieve
-- Tasks are either group tasks (group_id set) or personal tasks (user_id set).
-- CHECK constraint ensures at least one is present.

CREATE TABLE IF NOT EXISTS group_subscriptions (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    subscriber_id BIGINT NOT NULL,
    subscribed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(group_id, subscriber_id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    group_id BIGINT,                          -- NULL for personal tasks
    user_id BIGINT,                           -- NULL for group tasks
    message_sender_id BIGINT,
    title VARCHAR(500) NOT NULL,
    action_required TEXT,
    deadline TIMESTAMPTZ,
    reminder_level INTEGER DEFAULT 0,
    source_message_text TEXT,
    message_type VARCHAR(50) DEFAULT 'deadline',
    applies_at TIMESTAMPTZ,
    location TEXT,
    form_url TEXT,
    reminder_strategy VARCHAR(20) DEFAULT 'standard',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_task_owner CHECK (
        user_id IS NOT NULL OR group_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_tasks_group_id ON tasks(group_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline) WHERE reminder_level < 3;
CREATE INDEX IF NOT EXISTS idx_tasks_group_deadline ON tasks(group_id, deadline);
CREATE INDEX IF NOT EXISTS idx_tasks_user_deadline ON tasks(user_id, deadline);
CREATE INDEX IF NOT EXISTS idx_subscriptions_group ON group_subscriptions(group_id);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

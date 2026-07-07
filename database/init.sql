-- Database initialization script for Sieve
-- Creates tasks table with indexes for query performance

-- Create group_subscriptions table (many-to-many: groups <-> subscribers)
CREATE TABLE IF NOT EXISTS group_subscriptions (
    id SERIAL PRIMARY KEY,
    group_id BIGINT NOT NULL,
    subscriber_id BIGINT NOT NULL,
    subscribed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, subscriber_id)  -- Prevent duplicate subscriptions
);

-- Create index on group_id for fast subscriber lookups
CREATE INDEX IF NOT EXISTS idx_subscriptions_group_id ON group_subscriptions(group_id);

-- Create index on subscriber_id for user's subscription list
CREATE INDEX IF NOT EXISTS idx_subscriptions_subscriber_id ON group_subscriptions(subscriber_id);

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
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
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on group_id for efficient filtering by group
CREATE INDEX IF NOT EXISTS idx_tasks_group_id ON tasks(group_id);

-- Create index on created_at for efficient ordering by recency
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- Create composite index on group_id and created_at for optimized recent task queries
CREATE INDEX IF NOT EXISTS idx_tasks_group_created ON tasks(group_id, created_at DESC);

-- Create index on deadline and reminder_level for cron_notifier queries
CREATE INDEX IF NOT EXISTS idx_tasks_deadline_reminder ON tasks(deadline, reminder_level) WHERE reminder_level < 3;

-- Create index on user_id for task management commands (list user's tasks)
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);

-- Create index on group_id and title for group update detection (fuzzy matching)
CREATE INDEX IF NOT EXISTS idx_tasks_group_title ON tasks(group_id, LOWER(title));

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at on row updates
CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

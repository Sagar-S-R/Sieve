-- Database initialization script for Sieve
-- Creates tasks table with indexes for query performance

-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    action_required TEXT NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE,
    is_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on group_id for efficient filtering by group
CREATE INDEX IF NOT EXISTS idx_tasks_group_id ON tasks(group_id);

-- Create index on created_at for efficient ordering by recency
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);

-- Create composite index on group_id and created_at for optimized recent task queries
CREATE INDEX IF NOT EXISTS idx_tasks_group_created ON tasks(group_id, created_at DESC);

-- Create index on deadline and is_sent for cron_notifier queries
CREATE INDEX IF NOT EXISTS idx_tasks_deadline_sent ON tasks(deadline, is_sent) WHERE is_sent = FALSE;

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

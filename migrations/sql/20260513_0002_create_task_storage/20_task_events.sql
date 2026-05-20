-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- task_events
CREATE TABLE task_events (
    event_id uuid PRIMARY KEY,
    task_id uuid NOT NULL,
    job_id uuid,
    event_type text NOT NULL CHECK (
        event_type IN (
            'created',
            'decision_requested',
            'decision_received',
            'clarification_requested',
            'host_action_ready',
            'host_action_recorded',
            'host_action_retry_scheduled',
            'host_action_skipped',
            'completed',
            'failed',
            'rejected'
        )
    ),
    message text NOT NULL CHECK (length(btrim(message)) > 0),
    data_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(data_json) = 'object'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (task_id)
        REFERENCES tasks (task_id)
        ON DELETE CASCADE,
    FOREIGN KEY (task_id, job_id)
        REFERENCES task_jobs (task_id, job_id)
        ON DELETE SET NULL (job_id)
);

-- task_events_task_created_idx
CREATE INDEX task_events_task_created_idx
ON task_events (task_id, created_at);

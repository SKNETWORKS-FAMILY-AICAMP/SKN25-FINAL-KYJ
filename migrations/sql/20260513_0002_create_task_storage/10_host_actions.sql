-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- host_actions
CREATE TABLE host_actions (
    action_id uuid PRIMARY KEY,
    task_id uuid NOT NULL,
    job_id uuid,
    position integer NOT NULL CHECK (position >= 0),
    action_type text NOT NULL CHECK (
        action_type IN (
            'create_folder',
            'create_document',
            'update_document',
            'move_document',
            'link_documents'
        )
    ),
    summary text NOT NULL CHECK (length(btrim(summary)) > 0),
    reason text NOT NULL DEFAULT '',
    status text NOT NULL CHECK (
        status IN ('proposed', 'ready', 'succeeded', 'failed', 'skipped')
    ),
    attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    policy_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(policy_json) = 'object'
    ),
    input_json jsonb NOT NULL CHECK (jsonb_typeof(input_json) = 'object'),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(metadata) = 'object'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (task_id, position),
    UNIQUE (task_id, action_id),
    FOREIGN KEY (task_id)
        REFERENCES tasks (task_id)
        ON DELETE CASCADE,
    FOREIGN KEY (task_id, job_id)
        REFERENCES task_jobs (task_id, job_id)
        ON DELETE SET NULL (job_id)
);

-- tasks_current_action_id_fk
ALTER TABLE tasks
ADD CONSTRAINT tasks_current_action_id_fk
FOREIGN KEY (task_id, current_action_id)
    REFERENCES host_actions (task_id, action_id)
    DEFERRABLE INITIALLY DEFERRED;

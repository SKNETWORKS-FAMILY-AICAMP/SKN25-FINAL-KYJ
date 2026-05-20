-- This file is executed by its Alembic revision. Keep statements in dependency order.

-- tasks
CREATE TABLE tasks (
    task_id uuid PRIMARY KEY,
    tenant text NOT NULL
        REFERENCES tenant_storage_scopes (tenant_id)
        ON DELETE CASCADE
        CHECK (length(btrim(tenant)) > 0),
    request_text text NOT NULL DEFAULT '',
    context_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(context_json) = 'object'
    ),
    status text NOT NULL CHECK (
        status IN (
            'clarification_required',
            'awaiting_decision',
            'ready_for_host_action',
            'completed',
            'failed',
            'rejected'
        )
    ),
    analysis_message text NOT NULL CHECK (length(btrim(analysis_message)) > 0),
    result_type text CHECK (
        result_type IS NULL OR result_type IN (
            'clarification',
            'document_recommendation',
            'document_search_result',
            'folder_recommendation',
            'related_recommendation',
            'answer',
            'summary',
            'draft',
            'ideas',
            'action_plan'
        )
    ),
    result_json jsonb CHECK (
        result_json IS NULL OR jsonb_typeof(result_json) = 'object'
    ),
    result_title text,
    result_metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(result_metadata) = 'object'
    ),
    current_action_id uuid,
    error_json jsonb CHECK (
        error_json IS NULL OR jsonb_typeof(error_json) = 'object'
    ),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(metadata) = 'object'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    CHECK (
        (result_type IS NULL AND result_json IS NULL)
        OR (result_type IS NOT NULL AND result_json IS NOT NULL)
    ),
    CHECK (
        completed_at IS NULL
        OR status IN ('completed', 'failed', 'rejected')
    )
);

-- task_inputs
CREATE TABLE task_inputs (
    task_input_id uuid PRIMARY KEY,
    task_id uuid NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    input_text text NOT NULL CHECK (length(btrim(input_text)) > 0),
    context_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(context_json) = 'object'
    ),
    status text NOT NULL CHECK (status IN ('active', 'removed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    UNIQUE (task_id, position),
    FOREIGN KEY (task_id)
        REFERENCES tasks (task_id)
        ON DELETE CASCADE,
    CHECK (
        (
            status = 'active'
            AND deleted_at IS NULL
        )
        OR (
            status = 'removed'
            AND deleted_at IS NOT NULL
        )
    )
);

-- task_jobs
CREATE TABLE task_jobs (
    job_id uuid PRIMARY KEY,
    task_id uuid NOT NULL,
    round_index integer NOT NULL CHECK (round_index >= 0),
    position integer NOT NULL CHECK (position >= 0),
    job_type text NOT NULL CHECK (length(btrim(job_type)) > 0),
    status text NOT NULL CHECK (
        status IN ('planned', 'running', 'succeeded', 'failed', 'skipped')
    ),
    reason text NOT NULL DEFAULT '',
    input_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(input_json) = 'object'
    ),
    started_at timestamptz,
    finished_at timestamptz,
    error_json jsonb CHECK (
        error_json IS NULL OR jsonb_typeof(error_json) = 'object'
    ),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(metadata) = 'object'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (task_id, job_id),
    UNIQUE (task_id, round_index, position),
    FOREIGN KEY (task_id)
        REFERENCES tasks (task_id)
        ON DELETE CASCADE,
    CHECK (
        (
            status = 'planned'
            AND started_at IS NULL
            AND finished_at IS NULL
            AND error_json IS NULL
        )
        OR (
            status = 'running'
            AND started_at IS NOT NULL
            AND finished_at IS NULL
            AND error_json IS NULL
        )
        OR (
            status = 'succeeded'
            AND started_at IS NOT NULL
            AND finished_at IS NOT NULL
            AND error_json IS NULL
        )
        OR (
            status = 'failed'
            AND started_at IS NOT NULL
            AND finished_at IS NOT NULL
            AND error_json IS NOT NULL
        )
        OR (
            status = 'skipped'
            AND started_at IS NULL
            AND finished_at IS NOT NULL
            AND error_json IS NULL
        )
    )
);

-- task_job_results
CREATE TABLE task_job_results (
    job_result_id uuid PRIMARY KEY,
    job_id uuid NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    result_type text NOT NULL CHECK (length(btrim(result_type)) > 0),
    result_json jsonb NOT NULL CHECK (jsonb_typeof(result_json) = 'object'),
    summary_json jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(summary_json) = 'object'
    ),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
        jsonb_typeof(metadata) = 'object'
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (job_id, position),
    FOREIGN KEY (job_id)
        REFERENCES task_jobs (job_id)
        ON DELETE CASCADE
);

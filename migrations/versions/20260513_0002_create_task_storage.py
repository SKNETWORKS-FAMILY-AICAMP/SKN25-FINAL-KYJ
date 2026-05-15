"""create normalized task storage

Revision ID: 20260513_0002
Revises: 20260513_0001
Create Date: 2026-05-13
"""

from __future__ import annotations

from alembic import op

revision = "20260513_0002"
down_revision = "20260513_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tasks (
            task_id uuid PRIMARY KEY,
            tenant text NOT NULL CHECK (length(btrim(tenant)) > 0),
            request_text text NOT NULL DEFAULT '',
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
            current_action_id uuid,
            error_json jsonb CHECK (
                error_json IS NULL OR jsonb_typeof(error_json) = 'object'
            ),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
                jsonb_typeof(metadata) = 'object'
            ),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz
        )
        """
    )
    op.execute(
        """
        CREATE TABLE task_requests (
            task_request_id uuid PRIMARY KEY,
            task_id uuid NOT NULL,
            position integer NOT NULL CHECK (position >= 0),
            request text NOT NULL CHECK (length(btrim(request)) > 0),
            status text NOT NULL CHECK (status IN ('active', 'removed')),
            created_at timestamptz NOT NULL DEFAULT now(),
            removed_at timestamptz,
            UNIQUE (task_id, position),
            FOREIGN KEY (task_id)
                REFERENCES tasks (task_id)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE task_outputs (
            output_id uuid PRIMARY KEY,
            task_id uuid NOT NULL,
            position integer NOT NULL CHECK (position >= 0),
            output_type text NOT NULL CHECK (
                output_type IN (
                    'clarification',
                    'document_recommendation',
                    'folder_recommendation',
                    'related_recommendation',
                    'answer',
                    'summary',
                    'draft',
                    'ideas',
                    'action_plan'
                )
            ),
            title text,
            result_json jsonb NOT NULL CHECK (jsonb_typeof(result_json) = 'object'),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
                jsonb_typeof(metadata) = 'object'
            ),
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (task_id, position),
            FOREIGN KEY (task_id)
                REFERENCES tasks (task_id)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE host_actions (
            action_id uuid PRIMARY KEY,
            task_id uuid NOT NULL,
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
            result_json jsonb CHECK (
                result_json IS NULL OR jsonb_typeof(result_json) = 'object'
            ),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (
                jsonb_typeof(metadata) = 'object'
            ),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (task_id, position),
            UNIQUE (task_id, action_id),
            FOREIGN KEY (task_id)
                REFERENCES tasks (task_id)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        ALTER TABLE tasks
        ADD CONSTRAINT tasks_current_action_id_fk
        FOREIGN KEY (current_action_id)
            REFERENCES host_actions (action_id)
            DEFERRABLE INITIALLY DEFERRED
        """
    )
    op.execute(
        """
        CREATE TABLE host_action_dependencies (
            task_id uuid NOT NULL,
            action_id uuid NOT NULL,
            depends_on_action_id uuid NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (action_id, depends_on_action_id),
            CHECK (action_id <> depends_on_action_id),
            FOREIGN KEY (task_id, action_id)
                REFERENCES host_actions (task_id, action_id)
                ON DELETE CASCADE,
            FOREIGN KEY (task_id, depends_on_action_id)
                REFERENCES host_actions (task_id, action_id)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE TABLE task_events (
            event_id uuid PRIMARY KEY,
            task_id uuid NOT NULL,
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
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX task_events_task_created_idx
        ON task_events (task_id, created_at)
        """
    )


def downgrade() -> None:
    for table_name in (
        "host_action_dependencies",
        "host_actions",
        "task_outputs",
        "task_events",
        "task_requests",
        "tasks",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")

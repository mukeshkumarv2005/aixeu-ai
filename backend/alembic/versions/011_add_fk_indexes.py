"""Add missing foreign key indexes.

Revision ID: 011_add_fk_indexes
Revises: 71e37dd2f7b3
Create Date: 2026-07-04
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

revision: str = "011_add_fk_indexes"
down_revision: Union[str, None] = "71e37dd2f7b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    def create_idx_if_not_exists(table: str, col: str, idx_name: str):
        # check if index already exists
        indexes = inspector.get_indexes(table)
        idx_names = [idx['name'] for idx in indexes]
        if idx_name not in idx_names:
            op.create_index(idx_name, table, [col])

    # Add indexes for foreign keys
    create_idx_if_not_exists("refresh_tokens", "user_id", "ix_refresh_tokens_user_id")
    create_idx_if_not_exists("files", "user_id", "ix_files_user_id")
    create_idx_if_not_exists("conversations", "user_id", "ix_conversations_user_id")
    create_idx_if_not_exists("messages", "conversation_id", "ix_messages_conversation_id")
    create_idx_if_not_exists("knowledge_bases", "user_id", "ix_knowledge_bases_user_id")
    
    create_idx_if_not_exists("kb_documents", "knowledge_base_id", "ix_kb_documents_knowledge_base_id")
    create_idx_if_not_exists("kb_documents", "file_id", "ix_kb_documents_file_id")
    
    create_idx_if_not_exists("kb_embeddings", "kb_document_id", "ix_kb_embeddings_kb_document_id")
    create_idx_if_not_exists("kb_embeddings", "knowledge_base_id", "ix_kb_embeddings_knowledge_base_id")

    create_idx_if_not_exists("tasks", "owner_id", "ix_tasks_owner_id")
    create_idx_if_not_exists("tasks", "uploaded_document_id", "ix_tasks_uploaded_document_id")
    create_idx_if_not_exists("tasks", "chat_conversation_id", "ix_tasks_chat_conversation_id")
    create_idx_if_not_exists("tasks", "kb_document_id", "ix_tasks_kb_document_id")

    create_idx_if_not_exists("task_labels", "task_id", "ix_task_labels_task_id")
    create_idx_if_not_exists("task_labels", "user_id", "ix_task_labels_user_id")

    create_idx_if_not_exists("task_attachments", "task_id", "ix_task_attachments_task_id")
    create_idx_if_not_exists("task_attachments", "file_id", "ix_task_attachments_file_id")

    create_idx_if_not_exists("task_comments", "task_id", "ix_task_comments_task_id")
    create_idx_if_not_exists("task_comments", "file_id", "ix_task_comments_file_id")
    create_idx_if_not_exists("task_comments", "user_id", "ix_task_comments_user_id")

    create_idx_if_not_exists("recent_searches", "user_id", "ix_recent_searches_user_id")
    create_idx_if_not_exists("saved_searches", "user_id", "ix_saved_searches_user_id")

    create_idx_if_not_exists("agents", "owner_id", "ix_agents_owner_id")
    create_idx_if_not_exists("agent_runs", "agent_id", "ix_agent_runs_agent_id")
    create_idx_if_not_exists("agent_runs", "owner_id", "ix_agent_runs_owner_id")
    create_idx_if_not_exists("agent_memories", "agent_id", "ix_agent_memories_agent_id")
    create_idx_if_not_exists("agent_memories", "run_id", "ix_agent_memories_run_id")
    create_idx_if_not_exists("agent_tools", "agent_id", "ix_agent_tools_agent_id")

    create_idx_if_not_exists("user_settings", "user_id", "ix_user_settings_user_id")


def downgrade() -> None:
    pass

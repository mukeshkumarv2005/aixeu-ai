"""Unit tests for Agent Memory Service and Builtin Agent Tools."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.exceptions import AppException
from app.models.agent import Agent, AgentMemory
from app.services.agent.memory import AgentMemoryService, AgentNotFound, MemoryNotFound
from app.services.agent.tools import ToolContext, ToolResult
from app.services.agent.tools.builtins import (
    CalculatorTool,
    CurrentTimeTool,
    KnowledgeSearchTool,
    TaskManagerTool,
)
from tests.conftest import create_user


@pytest.fixture
async def sample_agent(db_session) -> Agent:
    user = await create_user(db_session)
    agent = Agent(
        owner_id=user.id,
        name="Memory Test Agent",
        system_prompt="You are a helpful agent.",
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


# ── Agent Memory Service Tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_memory_success(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    mem = await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Test memory content",
        importance=0.8,
    )

    assert mem.id is not None
    assert mem.content == "Test memory content"
    assert mem.importance == 0.8
    assert mem.memory_type == "short_term"


@pytest.mark.asyncio
async def test_add_memory_agent_not_found(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    with pytest.raises(AgentNotFound):
        await service.add_memory(
            agent_id=uuid.uuid4(),
            user_id=sample_agent.owner_id,
            content="Text",
        )


@pytest.mark.asyncio
async def test_add_conversation_turn(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    mem = await service.add_conversation_turn(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        role="user",
        content="User prompt",
    )
    assert mem.memory_type == "conversation"
    assert mem.role == "user"


@pytest.mark.asyncio
async def test_get_memory_success(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    mem = await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Retrieve me",
    )
    retrieved = await service.get_memory(mem.id, sample_agent.owner_id)
    assert retrieved.id == mem.id


@pytest.mark.asyncio
async def test_get_memory_not_found(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    with pytest.raises(MemoryNotFound):
        await service.get_memory(uuid.uuid4(), sample_agent.owner_id)


@pytest.mark.asyncio
async def test_list_memories(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Item 1",
        memory_type="long_term",
    )
    await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Item 2",
        memory_type="short_term",
    )

    items, total = await service.list_memories(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        memory_type="long_term",
    )
    assert total == 1
    assert items[0].content == "Item 1"


@pytest.mark.asyncio
async def test_get_conversation_history(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    run_id = uuid.uuid4()
    await service.add_conversation_turn(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        role="user",
        content="Hello!",
        run_id=run_id,
    )
    await service.add_conversation_turn(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        role="assistant",
        content="Hi there!",
        run_id=run_id,
    )

    history = await service.get_conversation_history(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        run_id=run_id,
    )
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_search_memories(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Deep learning optimization guide.",
        importance=0.9,
    )
    await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Breakfast recipes.",
        importance=0.2,
    )

    results = await service.search_memories(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        query="learning",
    )
    assert len(results) == 1
    assert "learning" in results[0].content


@pytest.mark.asyncio
async def test_update_and_delete_memory(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    mem = await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Original Content",
        importance=0.5,
    )

    # Update
    updated = await service.update_memory(
        memory_id=mem.id,
        user_id=sample_agent.owner_id,
        content="Updated Content",
        importance=0.95,
        metadata={"source": "api"},
    )
    assert updated.content == "Updated Content"
    assert updated.importance == 0.95
    assert updated.memory_metadata == {"source": "api"}

    # Delete
    await service.delete_memory(mem.id, sample_agent.owner_id)
    with pytest.raises(MemoryNotFound):
        await service.get_memory(mem.id, sample_agent.owner_id)


@pytest.mark.asyncio
async def test_clear_agent_memories(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="S1",
        memory_type="short_term",
    )
    await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="L1",
        memory_type="long_term",
    )

    deleted_count = await service.clear_agent_memories(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        memory_type="short_term",
    )
    assert deleted_count == 1

    stats = await service.memory_stats(sample_agent.id, sample_agent.owner_id)
    assert stats["short_term"] == 0
    assert stats["long_term"] == 1


@pytest.mark.asyncio
async def test_prune_expired_and_short_term(db_session, sample_agent):
    service = AgentMemoryService(db_session)
    # Expired prune
    mem_expired = await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Expired memory",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        memory_type="long_term",
    )
    mem_alive = await service.add_memory(
        agent_id=sample_agent.id,
        user_id=sample_agent.owner_id,
        content="Alive memory",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        memory_type="long_term",
    )

    pruned = await service.prune_expired()
    assert pruned == 1

    # Prune short term limit
    for i in range(52):
        await service.add_memory(
            agent_id=sample_agent.id,
            user_id=sample_agent.owner_id,
            content=f"ST {i}",
            memory_type="short_term",
            importance=0.1 + (i / 1000.0),
        )

    pruned_st = await service.prune_short_term(sample_agent.id, sample_agent.owner_id)
    assert pruned_st == 2


# ── Builtin Agent Tools Tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculator_tool():
    tool = CalculatorTool()
    ctx = ToolContext(db_session=MagicMock(), user_id=uuid.uuid4(), agent_id=uuid.uuid4(), run_id=uuid.uuid4())

    # Basic calculations
    res = await tool.execute(ctx, expression="2 + 3 * 4")
    assert res.success is True
    assert res.output == "14"

    # Math functions
    res = await tool.execute(ctx, expression="pow(2, 3)")
    assert res.success is True
    assert res.output == "8"

    # Missing expression
    res = await tool.execute(ctx, expression=None)
    assert res.success is False
    assert "No expression provided" in res.output

    # Zero Division
    res = await tool.execute(ctx, expression="1 / 0")
    assert res.success is False
    assert "failed" in res.output


@pytest.mark.asyncio
async def test_current_time_tool():
    tool = CurrentTimeTool()
    ctx = ToolContext(db_session=MagicMock(), user_id=uuid.uuid4(), agent_id=uuid.uuid4(), run_id=uuid.uuid4())

    # ISO
    res = await tool.execute(ctx, format="iso")
    assert res.success is True
    assert "T" in res.output

    # Unix
    res = await tool.execute(ctx, format="unix")
    assert res.success is True
    assert float(res.output) > 0

    # Date
    res = await tool.execute(ctx, format="date")
    assert res.success is True
    assert len(res.output) == 10  # YYYY-MM-DD

    # Time
    res = await tool.execute(ctx, format="time")
    assert res.success is True
    assert "UTC" in res.output


@pytest.mark.asyncio
async def test_knowledge_search_tool():
    tool = KnowledgeSearchTool()
    ctx = ToolContext(db_session=MagicMock(), user_id=uuid.uuid4(), agent_id=uuid.uuid4(), run_id=uuid.uuid4())

    # Missing query
    res = await tool.execute(ctx, query="")
    assert res.success is False

    # Successful search
    mock_hit = MagicMock()
    mock_hit.entity_type = "kb_document"
    mock_hit.title = "Title of Doc"
    mock_hit.snippet = "This is a hit snippet"

    mock_search_resp = MagicMock()
    mock_search_resp.results = [mock_hit]

    mock_search_svc = MagicMock()
    mock_search_svc.search = AsyncMock(return_value=mock_search_resp)
    
    mock_search_cls = MagicMock(return_value=mock_search_svc)
    with patch.object(tool, "_search_service_cls", mock_search_cls):
        res = await tool.execute(ctx, query="test query")
        assert res.success is True
        assert "[kb_document] Title of Doc" in res.output


@pytest.mark.asyncio
async def test_task_manager_tool():
    tool = TaskManagerTool()
    ctx = ToolContext(db_session=MagicMock(), user_id=uuid.uuid4(), agent_id=uuid.uuid4(), run_id=uuid.uuid4())

    # List action
    mock_task = MagicMock()
    mock_task.title = "My Task"
    mock_task.status = "todo"
    mock_task.priority = "high"

    mock_list_result = MagicMock()
    mock_list_result.items = [mock_task]

    mock_task_svc = MagicMock()
    mock_task_svc.list_tasks = AsyncMock(return_value=mock_list_result)

    mock_task_cls = MagicMock(return_value=mock_task_svc)
    with patch.object(tool, "_task_service_cls", mock_task_cls):
        res = await tool.execute(ctx, action="list")
        assert res.success is True
        assert "My Task" in res.output

        # Create action without title
        res_err = await tool.execute(ctx, action="create")
        assert res_err.success is False

        # Create action success
        mock_new_task = MagicMock()
        mock_new_task.title = "New Task"
        mock_new_task.id = uuid.uuid4()
        mock_task_svc.create_task = AsyncMock(return_value=mock_new_task)
        res_create = await tool.execute(ctx, action="create", title="New Task")
        assert res_create.success is True

        # Get action missing task_id
        res_get_err = await tool.execute(ctx, action="get")
        assert res_get_err.success is False

        # Get action success
        mock_task_svc.get_task = AsyncMock(return_value=mock_task)
        res_get = await tool.execute(ctx, action="get", task_id=str(uuid.uuid4()))
        assert res_get.success is True

        # Unknown action
        res_unknown = await tool.execute(ctx, action="unknown")
        assert res_unknown.success is False

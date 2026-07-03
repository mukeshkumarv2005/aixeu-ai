"""Comprehensive AI Agent integration tests.

Covers CRUD for agents, runs, tools, templates, execution, cancellation,
ownership isolation, built-in template protection, validation, pagination,
and all edge cases.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent, AgentRun, AgentTemplate, AgentTool
from app.schemas.agent import TEMPLATE_CATEGORIES, TOOL_TYPES
from tests.conftest import auth_header, create_user


# ── Factory helpers ──────────────────────────────────────────────────────────────


async def create_agent(
    db_session: AsyncSession,
    user_id: UUID,
    **kwargs: Any,
) -> Agent:
    """Factory: create an agent directly in the DB and return the ORM object."""
    agent = Agent(
        owner_id=user_id,
        name=kwargs.pop("name", "Test agent"),
        description=kwargs.pop("description", None),
        system_prompt=kwargs.pop("system_prompt", None),
        model=kwargs.pop("model", "gpt-4o"),
        temperature=kwargs.pop("temperature", 0.7),
        max_tokens=kwargs.pop("max_tokens", None),
        enabled=kwargs.pop("enabled", True),
        **kwargs,
    )
    db_session.add(agent)
    await db_session.flush()
    return agent


async def create_run(
    db_session: AsyncSession,
    user_id: UUID,
    agent_id: UUID,
    **kwargs: Any,
) -> AgentRun:
    """Factory: create an agent run directly in the DB."""
    run = AgentRun(
        agent_id=agent_id,
        owner_id=user_id,
        status=kwargs.pop("status", "completed"),
        input_text=kwargs.pop("input_text", "Test input"),
        result=kwargs.pop("result", "Test result"),
        **kwargs,
    )
    db_session.add(run)
    await db_session.flush()
    return run


async def create_tool(
    db_session: AsyncSession,
    agent_id: UUID,
    **kwargs: Any,
) -> AgentTool:
    """Factory: create a tool for an agent directly in the DB."""
    tool = AgentTool(
        agent_id=agent_id,
        tool_type=kwargs.pop("tool_type", "calculator"),
        name=kwargs.pop("name", "Calculator"),
        description=kwargs.pop("description", "A simple calculator"),
        config=kwargs.pop("config", {}),
        enabled=kwargs.pop("enabled", True),
        **kwargs,
    )
    db_session.add(tool)
    await db_session.flush()
    return tool


async def create_template(  # noqa: PLR0913
    db_session: AsyncSession,
    user_id: UUID | None = None,
    **kwargs: Any,
) -> AgentTemplate:
    """Factory: create an agent template directly in the DB.

    Set ``is_builtin=True`` and ``user_id=None`` for built-in templates.
    """
    tpl = AgentTemplate(
        owner_id=kwargs.pop("owner_id", user_id),
        name=kwargs.pop("name", "Test template"),
        description=kwargs.pop("description", None),
        category=kwargs.pop("category", "general"),
        system_prompt=kwargs.pop("system_prompt", None),
        model=kwargs.pop("model", "gpt-4o"),
        temperature=kwargs.pop("temperature", 0.7),
        default_tools=kwargs.pop("default_tools", None),
        is_builtin=kwargs.pop("is_builtin", False),
        is_active=kwargs.pop("is_active", True),
        **kwargs,
    )
    db_session.add(tpl)
    await db_session.flush()
    return tpl


# ── Util helpers ─────────────────────────────────────────────────────────────────


VALID_TOOL_TYPES = sorted(TOOL_TYPES)
VALID_CATEGORIES = sorted(TEMPLATE_CATEGORIES)


# ── Test classes ─────────────────────────────────────────────────────────────────


class TestCreateAgent:
    """POST /api/v1/agents"""

    async def test_create_basic(self, client: AsyncClient, user_id: UUID):
        """Minimal creation succeeds with defaults."""
        resp = await client.post(
            "/api/v1/agents",
            json={"name": "My agent"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My agent"
        assert data["model"] == "gpt-4o"
        assert data["temperature"] == 0.7
        assert data["enabled"] is True
        assert data["owner_id"] == str(user_id)
        assert UUID(data["id"])

    async def test_create_with_all_fields(self, client: AsyncClient, user_id: UUID):
        """All optional fields are accepted."""
        payload = {
            "name": "Research assistant",
            "description": "Helps with research tasks",
            "system_prompt": "You are a research assistant.",
            "model": "claude-sonnet-5",
            "temperature": 0.3,
            "max_tokens": 4096,
            "enabled": False,
        }
        resp = await client.post(
            "/api/v1/agents", json=payload, headers=auth_header(str(user_id))
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Research assistant"
        assert data["description"] == "Helps with research tasks"
        assert data["system_prompt"] == "You are a research assistant."
        assert data["model"] == "claude-sonnet-5"
        assert data["temperature"] == 0.3
        assert data["max_tokens"] == 4096
        assert data["enabled"] is False

    async def test_create_unauthenticated(self, client: AsyncClient):
        """Missing auth token returns 401."""
        resp = await client.post("/api/v1/agents", json={"name": "X"})
        assert resp.status_code == 401


class TestListAgents:
    """GET /api/v1/agents"""

    async def test_list_empty(self, client: AsyncClient, user_id: UUID):
        """No agents returns empty list."""
        resp = await client.get("/api/v1/agents", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_pagination(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Pagination returns correct slice."""
        for i in range(5):
            await create_agent(db_session, user_id, name=f"Agent {i}")
        resp = await client.get(
            "/api/v1/agents?offset=0&limit=2", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["offset"] == 0
        assert data["limit"] == 2

    async def test_list_search(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Search matches name and description."""
        await create_agent(db_session, user_id, name="Alpha", description="Document analysis")
        await create_agent(db_session, user_id, name="Beta")
        resp = await client.get(
            "/api/v1/agents?search=analysis", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Alpha"

    async def test_list_ownership_isolation(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Only the current user's agents are returned."""
        other = await create_user(db_session, email="other@example.com", username="other")
        await create_agent(db_session, user_id, name="Mine")
        await create_agent(db_session, other.id, name="Theirs")
        resp = await client.get("/api/v1/agents", headers=auth_header(str(user_id)))
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Mine"


class TestGetAgent:
    """GET /api/v1/agents/{agent_id}"""

    async def test_get_own_agent(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting own agent returns it."""
        agent = await create_agent(db_session, user_id)
        resp = await client.get(
            f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(agent.id)

    async def test_get_other_user_agent_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        resp = await client.get(
            f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 404

    async def test_get_nonexistent(self, client: AsyncClient, user_id: UUID):
        """Getting a non-existent agent returns 404."""
        resp = await client.get(
            "/api/v1/agents/00000000-0000-0000-0000-000000000000",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestUpdateAgent:
    """PATCH /api/v1/agents/{agent_id}"""

    async def test_update_basic(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Partial update changes only the provided field."""
        agent = await create_agent(db_session, user_id)
        resp = await client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"name": "Updated agent"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated agent"
        # Other fields unchanged
        assert resp.json()["enabled"] is True
        assert resp.json()["model"] == "gpt-4o"

    async def test_update_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Updating another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        resp = await client.patch(
            f"/api/v1/agents/{agent.id}",
            json={"name": "Hacked"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestDeleteAgent:
    """DELETE /api/v1/agents/{agent_id}"""

    async def test_delete_own(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting own agent returns 204."""
        agent = await create_agent(db_session, user_id)
        resp = await client.delete(
            f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 204

    async def test_delete_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        resp = await client.delete(
            f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 404

    async def test_delete_cascades_runs(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting an agent cascades to its runs."""
        agent = await create_agent(db_session, user_id)
        await create_run(db_session, user_id, agent.id)
        resp = await client.delete(
            f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 204


class TestExecuteAgent:
    """POST /api/v1/agents/{agent_id}/execute"""

    async def test_execute_enabled_agent(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Executing an enabled agent with MockAIProvider returns a result."""
        agent = await create_agent(db_session, user_id, enabled=True)
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/execute",
            json={"input_text": "Hello"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert UUID(data["run_id"])
        # MockAIProvider returns a canned response
        assert data["result"] is not None
        assert "mock response" in data["result"].lower()
        assert data["token_usage"] is not None

    async def test_execute_disabled_agent_400(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Executing a disabled agent returns 400."""
        agent = await create_agent(db_session, user_id, enabled=False)
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/execute",
            json={"input_text": "Hello"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 400
        assert "disabled" in resp.json()["detail"].lower()

    async def test_execute_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Executing another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id, enabled=True)
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/execute",
            json={"input_text": "Hello"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestListRuns:
    """GET /api/v1/agents/{agent_id}/runs"""

    async def test_list_empty(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """No runs returns empty list."""
        agent = await create_agent(db_session, user_id)
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/runs", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_pagination(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Pagination returns correct slice."""
        agent = await create_agent(db_session, user_id)
        for i in range(5):
            await create_run(db_session, user_id, agent.id, input_text=f"Run {i}")
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/runs?offset=0&limit=2",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_filter_by_status(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Filtering by status returns only matching runs."""
        agent = await create_agent(db_session, user_id)
        await create_run(db_session, user_id, agent.id, status="completed")
        await create_run(db_session, user_id, agent.id, status="failed")
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/runs?status=completed",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "completed"

    async def test_list_other_user_agent_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Listing runs on another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/runs", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 404


class TestGetRun:
    """GET /api/v1/agents/runs/{run_id}"""

    async def test_get_own_run(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting own run returns it."""
        agent = await create_agent(db_session, user_id)
        run = await create_run(db_session, user_id, agent.id)
        resp = await client.get(
            f"/api/v1/agents/runs/{run.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(run.id)
        assert resp.json()["agent_id"] == str(agent.id)

    async def test_get_other_user_run_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting another user's run returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        run = await create_run(db_session, other.id, agent.id)
        resp = await client.get(
            f"/api/v1/agents/runs/{run.id}", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 404

    async def test_get_nonexistent(self, client: AsyncClient, user_id: UUID):
        """Getting a non-existent run returns 404."""
        resp = await client.get(
            "/api/v1/agents/runs/00000000-0000-0000-0000-000000000000",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestCancelRun:
    """POST /api/v1/agents/runs/{run_id}/cancel"""

    async def test_cancel_queued_run(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Cancelling a queued run succeeds and updates status."""
        agent = await create_agent(db_session, user_id)
        run = await create_run(db_session, user_id, agent.id, status="queued")
        resp = await client.post(
            f"/api/v1/agents/runs/{run.id}/cancel",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_cancel_running_run(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Cancelling a running run succeeds."""
        agent = await create_agent(db_session, user_id)
        run = await create_run(db_session, user_id, agent.id, status="running")
        resp = await client.post(
            f"/api/v1/agents/runs/{run.id}/cancel",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    async def test_cancel_completed_run_400(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Cancelling a completed run returns 400."""
        agent = await create_agent(db_session, user_id)
        run = await create_run(db_session, user_id, agent.id, status="completed")
        resp = await client.post(
            f"/api/v1/agents/runs/{run.id}/cancel",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 400
        assert "not in a running" in resp.json()["detail"].lower()

    async def test_cancel_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Cancelling another user's run returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        run = await create_run(db_session, other.id, agent.id, status="queued")
        resp = await client.post(
            f"/api/v1/agents/runs/{run.id}/cancel",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_cancel_nonexistent_404(self, client: AsyncClient, user_id: UUID):
        """Cancelling a non-existent run returns 404."""
        resp = await client.post(
            "/api/v1/agents/runs/00000000-0000-0000-0000-000000000000/cancel",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestAddTool:
    """POST /api/v1/agents/{agent_id}/tools"""

    async def test_add_tool(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Adding a valid tool succeeds."""
        agent = await create_agent(db_session, user_id)
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={
                "tool_type": "calculator",
                "name": "Calc",
                "description": "Does math",
                "config": {"precision": 2},
            },
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["tool_type"] == "calculator"
        assert data["name"] == "Calc"
        assert data["description"] == "Does math"
        assert data["config"] == {"precision": 2}
        assert data["enabled"] is True
        assert data["agent_id"] == str(agent.id)

    async def test_add_tool_invalid_type_422(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Invalid tool_type returns 422."""
        agent = await create_agent(db_session, user_id)
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_type": "invalid_tool", "name": "Bad"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_add_tool_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Adding a tool to another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_type": "calculator", "name": "Calc"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestListTools:
    """GET /api/v1/agents/{agent_id}/tools"""

    async def test_list_tools(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Listing tools returns all tools for the agent."""
        agent = await create_agent(db_session, user_id)
        await create_tool(db_session, agent.id, name="Tool A")
        await create_tool(db_session, agent.id, name="Tool B")
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/tools",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {t["name"] for t in data}
        assert names == {"Tool A", "Tool B"}

    async def test_list_tools_empty(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """No tools returns empty list."""
        agent = await create_agent(db_session, user_id)
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/tools",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_tools_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Listing tools on another user's agent returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        resp = await client.get(
            f"/api/v1/agents/{agent.id}/tools",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestUpdateTool:
    """PATCH /api/v1/agents/tools/{tool_id}"""

    async def test_update_tool(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Updating a tool's name and enabled status works."""
        agent = await create_agent(db_session, user_id)
        tool = await create_tool(db_session, agent.id)
        resp = await client.patch(
            f"/api/v1/agents/tools/{tool.id}",
            json={"name": "Updated", "enabled": False},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["enabled"] is False

    async def test_update_tool_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Updating another user's tool returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        tool = await create_tool(db_session, agent.id)
        resp = await client.patch(
            f"/api/v1/agents/tools/{tool.id}",
            json={"name": "Hacked"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestRemoveTool:
    """DELETE /api/v1/agents/tools/{tool_id}"""

    async def test_remove_tool(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Removing a tool returns 204."""
        agent = await create_agent(db_session, user_id)
        tool = await create_tool(db_session, agent.id)
        resp = await client.delete(
            f"/api/v1/agents/tools/{tool.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 204

    async def test_remove_tool_other_user_404(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Removing another user's tool returns 404."""
        other = await create_user(db_session, email="other@example.com", username="other")
        agent = await create_agent(db_session, other.id)
        tool = await create_tool(db_session, agent.id)
        resp = await client.delete(
            f"/api/v1/agents/tools/{tool.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestCreateTemplate:
    """POST /api/v1/agents/templates"""

    async def test_create_template(self, client: AsyncClient, user_id: UUID):
        """Creating a template succeeds."""
        resp = await client.post(
            "/api/v1/agents/templates",
            json={
                "name": "My template",
                "description": "A custom template",
                "category": "coding",
                "system_prompt": "You are a coding assistant.",
                "model": "claude-sonnet-5",
                "temperature": 0.2,
            },
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My template"
        assert data["category"] == "coding"
        assert data["model"] == "claude-sonnet-5"
        assert data["temperature"] == 0.2
        assert data["is_builtin"] is False
        assert data["owner_id"] == str(user_id)

    async def test_create_template_invalid_category_422(self, client: AsyncClient, user_id: UUID):
        """Invalid category returns 422."""
        resp = await client.post(
            "/api/v1/agents/templates",
            json={"name": "Bad", "category": "nonexistent"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_create_template_with_default_tools(self, client: AsyncClient, user_id: UUID):
        """Creating a template with default tools succeeds."""
        resp = await client.post(
            "/api/v1/agents/templates",
            json={
                "name": "Tooled template",
                "category": "general",
                "default_tools": [
                    {"tool_type": "calculator", "name": "Calc"},
                    {"tool_type": "current_time", "name": "Clock"},
                ],
            },
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Tooled template"


class TestListTemplates:
    """GET /api/v1/agents/templates"""

    async def test_list_empty(self, client: AsyncClient, user_id: UUID):
        """No user-created templates returns only built-in (none seeded) so list is empty."""
        resp = await client.get(
            "/api/v1/agents/templates", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        # No built-in templates are seeded by default
        assert isinstance(resp.json()["items"], list)

    async def test_list_shows_own_templates(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """User-created templates appear in the list."""
        await create_template(db_session, user_id, name="My template")
        resp = await client.get(
            "/api/v1/agents/templates", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        data = resp.json()
        names = [t["name"] for t in data["items"]]
        assert "My template" in names

    async def test_list_filter_by_category(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Filtering by category works."""
        await create_template(db_session, user_id, name="Research", category="research")
        await create_template(db_session, user_id, name="Writing", category="writing")
        resp = await client.get(
            "/api/v1/agents/templates?category=research",
            headers=auth_header(str(user_id)),
        )
        data = resp.json()
        names = [t["name"] for t in data["items"]]
        assert "Research" in names
        assert "Writing" not in names

    async def test_list_exclude_builtin(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Built-in templates can be excluded."""
        await create_template(db_session, user_id=None, name="Built-in", is_builtin=True)
        await create_template(db_session, user_id, name="User template")
        resp = await client.get(
            "/api/v1/agents/templates?include_builtin=false",
            headers=auth_header(str(user_id)),
        )
        data = resp.json()
        names = [t["name"] for t in data["items"]]
        assert "User template" in names
        assert "Built-in" not in names


class TestGetTemplate:
    """GET /api/v1/agents/templates/{template_id}"""

    async def test_get_template(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting own template returns it."""
        tpl = await create_template(db_session, user_id)
        resp = await client.get(
            f"/api/v1/agents/templates/{tpl.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(tpl.id)

    async def test_get_builtin_template(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Getting a built-in template (owner_id=None) works."""
        tpl = await create_template(db_session, user_id=None, name="Built-in", is_builtin=True)
        resp = await client.get(
            f"/api/v1/agents/templates/{tpl.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["is_builtin"] is True

    async def test_get_nonexistent_404(self, client: AsyncClient, user_id: UUID):
        """Getting a non-existent template returns 404."""
        resp = await client.get(
            "/api/v1/agents/templates/00000000-0000-0000-0000-000000000000",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestUpdateTemplate:
    """PATCH /api/v1/agents/templates/{template_id}"""

    async def test_update_own_template(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Updating own template succeeds."""
        tpl = await create_template(db_session, user_id, name="Original")
        resp = await client.patch(
            f"/api/v1/agents/templates/{tpl.id}",
            json={"name": "Updated", "temperature": 0.5},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["temperature"] == 0.5

    async def test_update_builtin_template_403(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Updating a built-in template returns 403."""
        tpl = await create_template(db_session, user_id=None, name="Built-in", is_builtin=True)
        resp = await client.patch(
            f"/api/v1/agents/templates/{tpl.id}",
            json={"name": "Hacked"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 403
        assert "built-in" in resp.json()["detail"].lower()


class TestDeleteTemplate:
    """DELETE /api/v1/agents/templates/{template_id}"""

    async def test_delete_own_template(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting own template returns 204."""
        tpl = await create_template(db_session, user_id)
        resp = await client.delete(
            f"/api/v1/agents/templates/{tpl.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 204

    async def test_delete_builtin_template_403(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Deleting a built-in template returns 403."""
        tpl = await create_template(db_session, user_id=None, name="Built-in", is_builtin=True)
        resp = await client.delete(
            f"/api/v1/agents/templates/{tpl.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 403
        assert "built-in" in resp.json()["detail"].lower()


class TestCreateAgentFromTemplate:
    """POST /api/v1/agents/templates/{template_id}/create-agent"""

    async def test_create_basic(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Creating an agent from a template succeeds."""
        tpl = await create_template(
            db_session,
            user_id,
            name="Research template",
            system_prompt="You are a research agent.",
            model="claude-sonnet-5",
            temperature=0.3,
        )
        resp = await client.post(
            f"/api/v1/agents/templates/{tpl.id}/create-agent",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Research template"
        assert data["system_prompt"] == "You are a research agent."
        assert data["model"] == "claude-sonnet-5"
        assert data["temperature"] == 0.3
        assert data["owner_id"] == str(user_id)

    async def test_create_with_name_override(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Name override via query param works."""
        tpl = await create_template(db_session, user_id, name="Base template")
        resp = await client.post(
            f"/api/v1/agents/templates/{tpl.id}/create-agent?name=Custom%20Agent",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Custom Agent"

    async def test_create_with_default_tools(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Agent created from template inherits default tools."""
        tpl = await create_template(
            db_session,
            user_id,
            name="Tooled template",
            default_tools=[
                {"tool_type": "calculator", "name": "Calc", "description": "Math", "config": {}},
                {"tool_type": "current_time", "name": "Clock", "description": "Time", "config": {}},
            ],
        )
        resp = await client.post(
            f"/api/v1/agents/templates/{tpl.id}/create-agent",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        agent_id = UUID(resp.json()["id"])

        # Verify tools were cloned
        result = await db_session.execute(
            select(AgentTool).where(AgentTool.agent_id == agent_id)
        )
        tools = result.scalars().all()
        assert len(tools) == 2
        tool_types = {t.tool_type for t in tools}
        assert tool_types == {"calculator", "current_time"}

    async def test_create_from_builtin_template(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Creating from a built-in template works."""
        tpl = await create_template(
            db_session, user_id=None, name="Built-in template", is_builtin=True,
        )
        resp = await client.post(
            f"/api/v1/agents/templates/{tpl.id}/create-agent",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201

    async def test_create_from_nonexistent_template_404(self, client: AsyncClient, user_id: UUID):
        """Creating from a non-existent template returns 404."""
        resp = await client.post(
            "/api/v1/agents/templates/00000000-0000-0000-0000-000000000000/create-agent",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestOwnershipIsolation:
    """Every direct-resource endpoint on another user's entity returns 404."""

    @pytest_asyncio.fixture
    async def other_context(self, db_session: AsyncSession) -> tuple[UUID, Agent, AgentRun, AgentTool, AgentTemplate]:
        """Create a full context owned by "other" user."""
        other = await create_user(db_session, email="bob@example.com", username="bob")
        agent = await create_agent(db_session, other.id, name="Other's agent")
        run = await create_run(db_session, other.id, agent.id, status="queued")
        tool = await create_tool(db_session, agent.id)
        tpl = await create_template(db_session, other.id, name="Other's template")
        return other.id, agent, run, tool, tpl

    async def test_get_agent_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.get(f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_patch_agent_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.patch(f"/api/v1/agents/{agent.id}", json={"name": "x"}, headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_delete_agent_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.delete(f"/api/v1/agents/{agent.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_execute_agent_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/execute",
            json={"input_text": "Hello"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_list_runs_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.get(f"/api/v1/agents/{agent.id}/runs", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_get_run_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, _, run, _, _ = other_context
        resp = await client.get(f"/api/v1/agents/runs/{run.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_cancel_run_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, _, run, _, _ = other_context
        resp = await client.post(f"/api/v1/agents/runs/{run.id}/cancel", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_add_tool_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.post(
            f"/api/v1/agents/{agent.id}/tools",
            json={"tool_type": "calculator", "name": "x"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_list_tools_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, agent, _, _, _ = other_context
        resp = await client.get(f"/api/v1/agents/{agent.id}/tools", headers=auth_header(str(user_id)))
        assert resp.status_code == 404

    async def test_update_tool_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, _, _, tool, _ = other_context
        resp = await client.patch(
            f"/api/v1/agents/tools/{tool.id}",
            json={"name": "x"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_remove_tool_404(self, client: AsyncClient, user_id: UUID, other_context):
        _, _, _, tool, _ = other_context
        resp = await client.delete(f"/api/v1/agents/tools/{tool.id}", headers=auth_header(str(user_id)))
        assert resp.status_code == 404


# ── Fixtures ─────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def user_id(db_session: AsyncSession) -> UUID:
    """Create a test user and return their ID."""
    user = await create_user(db_session)
    return user.id

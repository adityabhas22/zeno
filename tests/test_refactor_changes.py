"""
Unit tests validating recent refactor decisions without requiring external deps.

These tests avoid importing livekit.* modules by reading file contents and
performing string-level assertions for key changes.
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_daily_planning_returns_main_agent():
    """Ensure DailyPlanningAgent returns MainZenoAgent on handoff."""
    content = read("agents/core/daily_planning_agent.py")
    assert "from agents.core.main_zeno_agent import MainZenoAgent" in content
    assert "return MainZenoAgent(), \"Daily planning session complete" in content


def test_zenoagent_exports_removed():
    """Verify ZenoAgent is no longer exported from package init files."""
    pkg_init = read("agents/__init__.py")
    core_init = read("agents/core/__init__.py")

    assert "ZenoAgent" not in pkg_init
    assert "ZenoAgent" not in core_init


def test_dockerfile_runs_smart_entrypoint():
    """Ensure Dockerfile executes the smart entrypoint instead of zeno_agent."""
    dockerfile = read("deployment/docker/Dockerfile.agent")
    assert "agents.core.smart_entrypoint" in dockerfile
    assert "agents.core.zeno_agent" not in dockerfile


def test_setup_script_guidance_updated():
    """Ensure setup script prints the updated run command to smart_entrypoint."""
    setup_script = read("scripts/setup.py")
    assert "agents.core.smart_entrypoint" in setup_script
    assert "agents.core.zeno_agent" not in setup_script


def test_phone_telephony_activation_keywords_present():
    """Quick sanity: verify activation/deactivation phrase lists exist for telephony agent."""
    telephony = read("agents/core/phone_telephony_agent.py")
    assert "_is_activation" in telephony
    assert "_is_deactivation" in telephony
    assert "\"hey zeno\"" in telephony.lower()
    assert "\"zeno out\"" in telephony.lower()


def test_agent_router_contains_expected_routing_logic():
    """Sanity check for AgentRouter routing/greeting strings (content-based)."""
    router = read("agents/core/agent_router.py")
    # Detects telephony by phone_number in metadata
    assert "phone_number" in router
    # Detects telephony by room name patterns
    assert "call-" in router or "phone-" in router
    # Has greeting branches for telephony and web
    assert "Greet the user as Zeno" in router
    assert "calling to provide their daily briefing" in router


def test_workflows_exports_and_files_removed():
    """Ensure unused workflows are not exported and files are removed."""
    wf_init = read("agents/workflows/__init__.py")
    assert "TaskPlanningWorkflow" not in wf_init
    assert "CallSchedulingWorkflow" not in wf_init

    assert not (REPO_ROOT / "agents/workflows/task_planning.py").exists()
    assert not (REPO_ROOT / "agents/workflows/call_scheduling.py").exists()


def test_readme_run_command_updated():
    """README should reference smart_entrypoint instead of zeno_agent."""
    readme = read("README.md")
    assert "agents.core.smart_entrypoint" in readme
    assert "agents.core.zeno_agent" not in readme

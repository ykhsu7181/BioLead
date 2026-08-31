import pytest

from scholarlead_agent.config import AppConfig, load_config


def test_agent_max_results_limit_defaults_to_50() -> None:
    assert AppConfig().agent_max_results_limit == 50


def test_load_config_reads_agent_max_results_limit_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MAX_RESULTS_LIMIT", "5")

    assert load_config().agent_max_results_limit == 5


@pytest.mark.parametrize("value", ["0", "-1", "invalid"])
def test_load_config_rejects_invalid_agent_max_results_limit(monkeypatch, value: str) -> None:
    monkeypatch.setenv("AGENT_MAX_RESULTS_LIMIT", value)

    with pytest.raises(ValueError, match="AGENT_MAX_RESULTS_LIMIT must be a positive integer"):
        load_config()


def test_app_config_rejects_boolean_agent_max_results_limit() -> None:
    with pytest.raises(ValueError, match="agent_max_results_limit must be a positive integer"):
        AppConfig(agent_max_results_limit=True)

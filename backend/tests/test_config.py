from app.core.config import Settings


def test_generic_debug_environment_variable_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "release")
    monkeypatch.delenv("TEUMSEOUL_DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.debug is False


def test_allowed_origins_accepts_comma_separated_value(monkeypatch) -> None:
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173, https://teumseoul.example.com",
    )

    settings = Settings(_env_file=None)

    assert settings.allowed_origins == [
        "http://localhost:5173",
        "https://teumseoul.example.com",
    ]


def test_recommendation_openai_settings_are_separated_from_chat_settings() -> None:
    settings = Settings(_env_file=None)

    assert settings.openai_timeout_seconds == 8
    assert settings.openai_max_candidates == 5
    assert settings.recommendation_timeout_seconds == 30
    assert settings.recommendation_candidate_limit == 18

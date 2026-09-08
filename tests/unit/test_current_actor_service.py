import pytest

from app.services import (
    current_actor_service,
)


pytestmark = pytest.mark.unit


def test_resolves_domain_user(
    monkeypatch,
):
    monkeypatch.setattr(
        current_actor_service.getpass,
        "getuser",
        lambda: "musuario",
    )

    monkeypatch.setenv(
        "USERDOMAIN",
        "RANSA",
    )

    assert (
        current_actor_service
        .resolve_current_actor()
        == "RANSA\\musuario"
    )


def test_without_domain_returns_username(
    monkeypatch,
):
    monkeypatch.setattr(
        current_actor_service.getpass,
        "getuser",
        lambda: "musuario",
    )

    monkeypatch.delenv(
        "USERDOMAIN",
        raising=False,
    )

    assert (
        current_actor_service
        .resolve_current_actor()
        == "musuario"
    )


def test_workgroup_is_not_used_as_domain(
    monkeypatch,
):
    monkeypatch.setattr(
        current_actor_service.getpass,
        "getuser",
        lambda: "musuario",
    )

    monkeypatch.setenv(
        "USERDOMAIN",
        "WORKGROUP",
    )

    assert (
        current_actor_service
        .resolve_current_actor()
        == "musuario"
    )


def test_empty_username_is_rejected(
    monkeypatch,
):
    monkeypatch.setattr(
        current_actor_service.getpass,
        "getuser",
        lambda: "   ",
    )

    with pytest.raises(
        current_actor_service.CurrentActorError,
        match="identificar",
    ):
        (
            current_actor_service
            .resolve_current_actor()
        )

import pytest

from app.ui.action_menu import (
    action_menu_source_state,
)


pytestmark = pytest.mark.unit


class FakeButton:
    def __init__(
        self,
        *,
        text,
        enabled,
        tooltip="",
    ):
        self._text = text
        self._enabled = enabled
        self._tooltip = tooltip

    def text(
        self,
    ):
        return self._text

    def isEnabled(
        self,
    ):
        return self._enabled

    def toolTip(
        self,
    ):
        return self._tooltip


def test_action_menu_source_state():
    source = FakeButton(
        text="Exportar Excel",
        enabled=True,
        tooltip="Exporta datos",
    )

    assert (
        action_menu_source_state(
            source
        )
        == (
            "Exportar Excel",
            True,
            "Exporta datos",
        )
    )


def test_action_menu_state_keeps_disabled_action():
    source = FakeButton(
        text="Distribuir por CECO",
        enabled=False,
    )

    assert (
        action_menu_source_state(
            source
        )
        == (
            "Distribuir por CECO",
            False,
            "",
        )
    )


def test_action_menu_uses_dynamic_source_text():
    source = FakeButton(
        text="Reactivar fila",
        enabled=True,
    )

    text, enabled, _ = (
        action_menu_source_state(
            source
        )
    )

    assert text == "Reactivar fila"
    assert enabled

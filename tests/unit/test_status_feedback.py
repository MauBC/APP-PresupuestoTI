import pytest

from app.ui.status_feedback import (
    VALID_STATUS_TONES,
    normalize_status_tone,
    set_status_feedback,
)


pytestmark = pytest.mark.unit


class FakeStyle:
    def __init__(
        self,
    ):
        self.unpolished = False
        self.polished = False

    def unpolish(
        self,
        widget,
    ):
        self.unpolished = True

    def polish(
        self,
        widget,
    ):
        self.polished = True


class FakeLabel:
    def __init__(
        self,
    ):
        self.properties = {}
        self.text = ""
        self.updated = False
        self._style = FakeStyle()

    def setProperty(
        self,
        name,
        value,
    ):
        self.properties[
            name
        ] = value

    def setText(
        self,
        value,
    ):
        self.text = value

    def style(
        self,
    ):
        return self._style

    def update(
        self,
    ):
        self.updated = True


def test_status_tones_are_stable():
    assert VALID_STATUS_TONES == (
        "neutral",
        "loading",
        "success",
        "warning",
        "error",
        "empty",
    )


def test_normalize_status_tone():
    assert (
        normalize_status_tone(
            "ERROR"
        )
        == "error"
    )

    assert (
        normalize_status_tone(
            "unknown"
        )
        == "neutral"
    )


def test_set_status_feedback_updates_label():
    label = FakeLabel()

    result = set_status_feedback(
        label,
        "Calculando...",
        tone="loading",
    )

    assert result == "loading"

    assert (
        label.properties[
            "statusTone"
        ]
        == "loading"
    )

    assert (
        label.text
        == "Calculando..."
    )

    assert label.updated
    assert (
        label._style.unpolished
    )
    assert (
        label._style.polished
    )


def test_invalid_feedback_tone_is_safe():
    label = FakeLabel()

    result = set_status_feedback(
        label,
        "Texto",
        tone="inventado",
    )

    assert result == "neutral"

    assert (
        label.properties[
            "statusTone"
        ]
        == "neutral"
    )

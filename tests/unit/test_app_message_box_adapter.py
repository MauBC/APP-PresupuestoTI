import pytest

import app.ui.dialogs.app_message_box as message_module

from app.ui.dialogs.app_message_box import (
    AppMessageBox,
)


pytestmark = pytest.mark.unit


def test_warning_uses_corporate_dialog(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        message_module,
        "show_warning",
        lambda parent, title, message:
            calls.append(
                (
                    parent,
                    title,
                    message,
                )
            ),
    )

    result = AppMessageBox.warning(
        None,
        "Titulo",
        "Mensaje",
    )

    assert calls == [
        (
            None,
            "Titulo",
            "Mensaje",
        )
    ]

    assert (
        result
        == AppMessageBox
        .StandardButton
        .Ok
    )


def test_information_uses_corporate_dialog(
    monkeypatch,
):
    calls = []

    monkeypatch.setattr(
        message_module,
        "show_info",
        lambda parent, title, message:
            calls.append(
                (
                    title,
                    message,
                )
            ),
    )

    AppMessageBox.information(
        None,
        "Info",
        "Contenido",
    )

    assert calls == [
        (
            "Info",
            "Contenido",
        )
    ]


@pytest.mark.parametrize(
    "confirmed, expected",
    (
        (
            True,
            AppMessageBox
            .StandardButton.Yes,
        ),
        (
            False,
            AppMessageBox
            .StandardButton.No,
        ),
    ),
)
def test_question_preserves_yes_no_contract(
    monkeypatch,
    confirmed,
    expected,
):
    monkeypatch.setattr(
        message_module,
        "ask_confirmation",
        lambda *args, **kwargs:
            confirmed,
    )

    result = AppMessageBox.question(
        None,
        "Confirmar",
        "Continuar?",
        AppMessageBox.StandardButton.Yes
        |
        AppMessageBox.StandardButton.No,
        AppMessageBox.StandardButton.No,
    )

    assert result == expected

VALID_STATUS_TONES = (
    "neutral",
    "loading",
    "success",
    "warning",
    "error",
    "empty",
)


def normalize_status_tone(
    tone,
):
    value = str(
        tone
        or "neutral"
    ).strip().lower()

    if (
        value
        not in VALID_STATUS_TONES
    ):
        return "neutral"

    return value


def set_status_feedback(
    label,
    text,
    *,
    tone="neutral",
):
    normalized = (
        normalize_status_tone(
            tone
        )
    )

    label.setProperty(
        "statusTone",
        normalized,
    )

    label.setText(
        str(
            text
            or ""
        )
    )

    style = label.style()

    style.unpolish(
        label
    )

    style.polish(
        label
    )

    label.update()

    return normalized

def apply_month_column_visibility(
    *,
    table,
    columns,
    month_columns,
    months_visible: bool,
) -> int:
    columns = tuple(
        columns
        or ()
    )

    month_columns = set(
        month_columns
        or ()
    )

    visible = bool(
        months_visible
    )

    matched = 0

    for index, column in enumerate(
        columns
    ):
        is_month = (
            column
            in month_columns
        )

        if is_month:
            matched += 1

        table.setColumnHidden(
            index,
            bool(
                is_month
                and not visible
            ),
        )

    return matched

import sys
from pathlib import Path


def resource_path(
    relative_path: str,
) -> Path:
    bundle_root = getattr(
        sys,
        "_MEIPASS",
        None,
    )

    if bundle_root is not None:
        base_path = Path(
            bundle_root
        )

    else:
        base_path = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

    return (
        base_path
        / relative_path
    )

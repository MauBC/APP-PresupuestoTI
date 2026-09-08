import getpass
import os


class CurrentActorError(
    RuntimeError
):
    pass


def resolve_current_actor() -> str:
    username = str(
        getpass.getuser()
        if getpass.getuser() is not None
        else ""
    ).strip()

    if not username:
        raise CurrentActorError(
            "No se pudo identificar al usuario "
            "actual de Windows."
        )

    domain = str(
        os.environ.get(
            "USERDOMAIN",
            ""
        )
    ).strip()

    if (
        domain
        and domain.upper()
        != "WORKGROUP"
    ):
        return (
            f"{domain}\\{username}"
        )

    return username

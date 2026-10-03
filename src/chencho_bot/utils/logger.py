import logging

from rich.logging import RichHandler


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                markup=True,
                show_time=True,
                show_path=False,
            )
        ],
    )
    logging.getLogger("chencho_bot").setLevel(logging.DEBUG)

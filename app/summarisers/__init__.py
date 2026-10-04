"""Chooses the summariser from the SUMMARISER_MODE setting."""
from app import config
from app.summarisers.base import Summariser


def get_summariser() -> Summariser:
    if config.SUMMARISER_MODE == "fake":
        from app.summarisers.fake import FakeSummariser
        return FakeSummariser()
    if config.SUMMARISER_MODE == "foundry":
        from app.summarisers.foundry import FoundrySummariser
        return FoundrySummariser()
    raise ValueError(f"Unknown SUMMARISER_MODE: {config.SUMMARISER_MODE!r}")

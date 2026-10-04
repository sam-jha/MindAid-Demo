"""One shared Jinja2 template setup."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.constants import SUPPORT_RESOURCES

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
templates.env.globals["support_resources"] = SUPPORT_RESOURCES


def fmt_date(dt):
    return dt.strftime("%d %b %Y")


def fmt_datetime(dt):
    return dt.strftime("%d %b %Y, %H:%M")


templates.env.filters["fmt_date"] = fmt_date
templates.env.filters["fmt_datetime"] = fmt_datetime

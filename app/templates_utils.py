"""
Utility to setup Jinja2 templates with timezone filters
"""
from fastapi.templating import Jinja2Templates
from app import utils

def create_templates(directory: str = "app/templates") -> Jinja2Templates:
    """
    Create Jinja2Templates instance with timezone filters registered.
    Use this instead of directly instantiating Jinja2Templates.
    """
    templates = Jinja2Templates(directory=directory)
    from urllib.parse import quote
    templates.env.filters["jakarta_time"] = utils.to_jakarta_time
    templates.env.filters["format_datetime_jakarta"] = utils.format_datetime_jakarta
    templates.env.filters["urlencode"] = quote
    return templates



from flask import Blueprint

preop_bp = Blueprint(
    "preop",
    __name__,
    url_prefix="/preop",
    template_folder="templates"
)

from app.preop import routes

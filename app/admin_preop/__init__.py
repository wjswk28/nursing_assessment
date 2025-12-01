from flask import Blueprint

admin_preop_bp = Blueprint(
    "admin_preop",
    __name__,
    url_prefix="/admin/preop",
    template_folder="templates"
)

from app.admin_preop import routes

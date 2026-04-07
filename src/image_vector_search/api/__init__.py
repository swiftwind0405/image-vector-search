"""REST API routers for the admin interface."""

from image_vector_search.api.admin_bulk_routes import create_admin_bulk_router
from image_vector_search.api.admin_routes import create_admin_router
from image_vector_search.api.admin_settings_routes import create_admin_settings_router
from image_vector_search.api.admin_tag_routes import create_admin_tag_router
from image_vector_search.api.auth_routes import create_auth_router

__all__ = [
    "create_admin_bulk_router",
    "create_admin_router",
    "create_admin_settings_router",
    "create_admin_tag_router",
    "create_auth_router",
]

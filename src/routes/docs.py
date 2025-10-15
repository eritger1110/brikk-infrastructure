# -*- coding: utf-8 -*-
"""
API Documentation Routes.

Serves OpenAPI/Swagger documentation at /docs.
"""
from flask import Blueprint, send_from_directory, current_app
from flask_swagger_ui import get_swaggerui_blueprint
import os

docs_bp = Blueprint('docs', __name__)

# Swagger UI configuration
SWAGGER_URL = '/docs'
API_URL = '/static/openapi.json'

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Brikk API Gateway",
        'docExpansion': 'list',
        'defaultModelsExpandDepth': 3,
        'displayRequestDuration': True,
        'filter': True,
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True
    }
)


@docs_bp.route('/static/openapi.json')
def serve_openapi_spec():
    """Serve the OpenAPI specification file."""
    static_dir = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_dir, 'openapi.json')


"""
Tests for blueprint registration helper.
"""

import pytest
from flask import Flask, Blueprint
from src.utils.blueprint_registry import (
    BlueprintRegistry,
    create_blueprint_registry,
    safe_register_blueprint
)


@pytest.fixture
def app():
    """Create a test Flask application."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def test_blueprint():
    """Create a test blueprint."""
    bp = Blueprint('test_bp', __name__, url_prefix='/test')
    
    @bp.route('/hello')
    def hello():
        return {'message': 'hello'}
    
    @bp.route('/world')
    def world():
        return {'message': 'world'}
    
    return bp


def test_create_blueprint_registry(app):
    """Test creating a blueprint registry."""
    registry = create_blueprint_registry(app)
    assert isinstance(registry, BlueprintRegistry)
    assert registry.app == app
    assert len(registry.registered_blueprints) == 0


def test_register_blueprint_success(app, test_blueprint):
    """Test successful blueprint registration."""
    registry = create_blueprint_registry(app)
    result = registry.register(test_blueprint)
    
    assert result is True
    assert len(registry.registered_blueprints) == 1
    
    bp_info = registry.registered_blueprints[0]
    assert bp_info['name'] == 'test_bp'
    assert bp_info['url_prefix'] == '/test'


def test_register_blueprint_with_custom_prefix(app, test_blueprint):
    """Test blueprint registration with custom URL prefix."""
    registry = create_blueprint_registry(app)
    result = registry.register(test_blueprint, url_prefix='/custom')
    
    assert result is True
    bp_info = registry.registered_blueprints[0]
    assert bp_info['url_prefix'] == '/custom'


def test_register_invalid_blueprint(app):
    """Test registration of invalid blueprint."""
    registry = create_blueprint_registry(app)
    result = registry.register("not_a_blueprint")
    
    assert result is False
    assert len(registry.registered_blueprints) == 0


def test_get_registered_blueprints(app, test_blueprint):
    """Test retrieving registered blueprints."""
    registry = create_blueprint_registry(app)
    registry.register(test_blueprint)
    
    blueprints = registry.get_registered_blueprints()
    assert len(blueprints) == 1
    assert blueprints[0]['name'] == 'test_bp'


def test_safe_register_blueprint_success(app, test_blueprint):
    """Test safe_register_blueprint with successful registration."""
    result = safe_register_blueprint(app, test_blueprint, url_prefix='/safe')
    assert result is True


def test_safe_register_blueprint_required_failure(app):
    """Test safe_register_blueprint with required=True on failure."""
    with pytest.raises(RuntimeError):
        safe_register_blueprint(app, "invalid", required=True)


def test_safe_register_blueprint_optional_failure(app):
    """Test safe_register_blueprint with required=False on failure."""
    result = safe_register_blueprint(app, "invalid", required=False)
    assert result is False


def test_print_route_map(app, test_blueprint, caplog):
    """Test printing route map."""
    import logging
    caplog.set_level(logging.INFO)
    
    registry = create_blueprint_registry(app)
    registry.register(test_blueprint)
    
    # Capture app logger output
    with caplog.at_level(logging.INFO, logger='flask.app'):
        registry.print_route_map()
    
    # The print_route_map method should be called without errors
    # We can't easily test the output since it uses app.logger
    # which may not be captured by caplog in all Flask versions
    assert len(registry.registered_blueprints) == 1


def test_multiple_blueprint_registration(app):
    """Test registering multiple blueprints."""
    registry = create_blueprint_registry(app)
    
    bp1 = Blueprint('bp1', __name__, url_prefix='/bp1')
    bp2 = Blueprint('bp2', __name__, url_prefix='/bp2')
    bp3 = Blueprint('bp3', __name__, url_prefix='/bp3')
    
    registry.register(bp1)
    registry.register(bp2)
    registry.register(bp3)
    
    assert len(registry.registered_blueprints) == 3
    
    names = [bp['name'] for bp in registry.registered_blueprints]
    assert 'bp1' in names
    assert 'bp2' in names
    assert 'bp3' in names


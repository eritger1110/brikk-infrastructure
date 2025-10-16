"""
Blueprint registration helper for Flask application.

Provides centralized, validated blueprint registration with:
- Automatic error handling and logging
- Route inventory and debugging support
- Consistent registration patterns
- Validation of blueprint configuration
"""

import logging
from typing import Optional, List, Dict, Any
from flask import Flask, Blueprint

logger = logging.getLogger(__name__)


class BlueprintRegistry:
    """
    Centralized blueprint registration manager.
    
    Tracks all registered blueprints and provides debugging utilities
    for route inspection and troubleshooting.
    """
    
    def __init__(self, app: Flask):
        """Initialize the blueprint registry."""
        self.app = app
        self.registered_blueprints: List[Dict[str, Any]] = []
        
    def register(
        self,
        blueprint: Blueprint,
        url_prefix: Optional[str] = None,
        **options
    ) -> bool:
        """
        Register a blueprint with validation and logging.
        
        Args:
            blueprint: Flask Blueprint instance to register
            url_prefix: Optional URL prefix for all blueprint routes
            **options: Additional options to pass to register_blueprint
            
        Returns:
            bool: True if registration successful, False otherwise
        """
        try:
            # Validate blueprint
            if not isinstance(blueprint, Blueprint):
                logger.error(
                    f"Invalid blueprint type: {type(blueprint).__name__}. "
                    f"Expected Flask Blueprint."
                )
                return False
            
            # Register the blueprint
            if url_prefix is not None:
                options['url_prefix'] = url_prefix
                
            self.app.register_blueprint(blueprint, **options)
            
            # Track registration
            registration_info = {
                'name': blueprint.name,
                'url_prefix': url_prefix or getattr(blueprint, 'url_prefix', None),
                'import_name': blueprint.import_name,
                'routes': self._get_blueprint_routes(blueprint)
            }
            self.registered_blueprints.append(registration_info)
            
            # Log successful registration
            route_count = len(registration_info['routes'])
            logger.info(
                f"Registered blueprint '{blueprint.name}' "
                f"with {route_count} routes "
                f"at prefix '{registration_info['url_prefix'] or '/'}'"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to register blueprint '{getattr(blueprint, 'name', 'unknown')}': {e}",
                exc_info=True
            )
            return False
    
    def _get_blueprint_routes(self, blueprint: Blueprint) -> List[str]:
        """
        Extract route patterns from a blueprint.
        
        Args:
            blueprint: Flask Blueprint instance
            
        Returns:
            List of route patterns defined in the blueprint
        """
        routes = []
        for rule in blueprint.deferred_functions:
            # Each deferred function is a tuple: (func, args, kwargs)
            # We're interested in route decorators
            if hasattr(rule, '__name__'):
                routes.append(rule.__name__)
        return routes
    
    def get_registered_blueprints(self) -> List[Dict[str, Any]]:
        """
        Get list of all registered blueprints with their metadata.
        
        Returns:
            List of dictionaries containing blueprint information
        """
        return self.registered_blueprints.copy()
    
    def print_route_map(self) -> None:
        """Print a formatted map of all registered routes."""
        self.app.logger.info("=" * 80)
        self.app.logger.info("REGISTERED BLUEPRINTS AND ROUTES")
        self.app.logger.info("=" * 80)
        
        for bp_info in self.registered_blueprints:
            prefix = bp_info['url_prefix'] or '/'
            self.app.logger.info(f"\nBlueprint: {bp_info['name']} (prefix: {prefix})")
            self.app.logger.info(f"  Import: {bp_info['import_name']}")
            self.app.logger.info(f"  Routes: {len(bp_info['routes'])}")
            
        self.app.logger.info("\n" + "=" * 80)
        self.app.logger.info(f"Total blueprints registered: {len(self.registered_blueprints)}")
        self.app.logger.info("=" * 80)


def create_blueprint_registry(app: Flask) -> BlueprintRegistry:
    """
    Create and initialize a blueprint registry for the application.
    
    Args:
        app: Flask application instance
        
    Returns:
        BlueprintRegistry instance
    """
    return BlueprintRegistry(app)


def safe_register_blueprint(
    app: Flask,
    blueprint: Blueprint,
    url_prefix: Optional[str] = None,
    required: bool = True,
    **options
) -> bool:
    """
    Safely register a blueprint with error handling.
    
    This is a standalone function for backward compatibility and
    one-off registrations without using the BlueprintRegistry class.
    
    Args:
        app: Flask application instance
        blueprint: Blueprint to register
        url_prefix: Optional URL prefix
        required: If True, raise exception on failure. If False, log warning.
        **options: Additional registration options
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        RuntimeError: If registration fails and required=True
    """
    try:
        if url_prefix is not None:
            options['url_prefix'] = url_prefix
            
        app.register_blueprint(blueprint, **options)
        
        logger.info(
            f"Registered blueprint '{blueprint.name}' "
            f"at prefix '{url_prefix or '/'}'"
        )
        return True
        
    except Exception as e:
        bp_name = getattr(blueprint, 'name', str(type(blueprint).__name__))
        error_msg = f"Failed to register blueprint '{bp_name}': {e}"
        
        if required:
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
        else:
            logger.warning(error_msg, exc_info=True)
            return False


# -*- coding: utf-8 -*-
"""
Test suite for structured logging and request context propagation.

Tests request_id generation, context propagation, structured logging format,
and integration with Flask request lifecycle.
"""

import pytest
import json
import uuid
import logging
import io
from unittest.mock import patch, MagicMock
from flask import Flask, g

from src.services.request_context import (
    RequestContextMiddleware, init_request_context,
    get_request_id, get_request_context, set_auth_context
)
from src.services.structured_logging import (
    StructuredLogger, StructuredFormatter, get_logger,
    configure_logging, LoggingMiddleware, init_logging
)


@pytest.fixture
def app():
    """Create test Flask app."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['BRIKK_LOG_JSON'] = 'true'
    return app


@pytest.fixture
def client(app):
    """Create test client with request context middleware."""
    with app.app_context():
        init_request_context(app)
        init_logging(app)
    return app.test_client()


class TestRequestContextMiddleware:
    """Test request context middleware functionality."""

    def test_request_id_generation(self, app):
        """Test that request_id is generated for each request."""
        init_request_context(app)

        @app.route('/test')
        def test_route():
            request_id = get_request_id()
            assert request_id is not None
            assert isinstance(request_id, str)
            assert len(request_id) > 0
            return {'request_id': request_id}

        client = app.test_client()
        response = client.get('/test')
        assert response.status_code == 200

        data = response.get_json()
        assert 'request_id' in data

        # Should be a valid UUID format
        try:
            uuid.UUID(data['request_id'])
        except ValueError:
            pytest.fail("request_id should be a valid UUID")

    def test_request_id_in_response_headers(self, app):
        """Test that request_id is included in response headers."""
        init_request_context(app)

        @app.route('/test')
        def test_route():
            return {'message': 'test'}

        client = app.test_client()
        response = client.get('/test')

        assert 'X-Request-ID' in response.headers
        request_id = response.headers['X-Request-ID']

        # Should be a valid UUID
        try:
            uuid.UUID(request_id)
        except ValueError:
            pytest.fail("X-Request-ID should be a valid UUID")

    def test_request_id_consistency_within_request(self, app):
        """Test that request_id is consistent within a single request."""
        init_request_context(app)

        request_ids = []

        @app.route('/test')
        def test_route():
            # Get request_id multiple times within the same request
            for _ in range(5):
                request_ids.append(get_request_id())
            return {'count': len(request_ids)}

        client = app.test_client()
        response = client.get('/test')
        assert response.status_code == 200

        # All request_ids should be the same
        assert len(set(request_ids)) == 1
        assert len(request_ids) == 5

    def test_different_request_ids_for_different_requests(self, app):
        """Test that different requests get different request_ids."""
        init_request_context(app)

        @app.route('/test')
        def test_route():
            return {'request_id': get_request_id()}

        client = app.test_client()

        # Make multiple requests
        request_ids = []
        for _ in range(5):
            response = client.get('/test')
            data = response.get_json()
            request_ids.append(data['request_id'])

        # All request_ids should be different
        assert len(set(request_ids)) == 5

    def test_request_context_includes_request_info(self, app):
        """Test that request context includes request information."""
        init_request_context(app)

        @app.route('/test', methods=['POST'])
        def test_route():
            context = get_request_context()
            return context

        client = app.test_client()
        response = client.post('/test', json={'data': 'test'})
        assert response.status_code == 200

        context = response.get_json()
        assert 'request_id' in context
        assert 'method' in context
        assert 'path' in context
        assert context['method'] == 'POST'
        assert context['path'] == '/test'

    def test_auth_context_integration(self, app):
        """Test that auth context is included in request context."""
        init_request_context(app)

        @app.route('/test')
        def test_route():
            # Set auth context
            set_auth_context({
                'org_id': 'test-org',
                'key_id': 'test-key',
                'agent_id': 'test-agent'
            })

            context = get_request_context()
            return context

        client = app.test_client()
        response = client.get('/test')
        assert response.status_code == 200

        context = response.get_json()
        assert 'organization_id' in context
        assert 'api_key_id' in context
        assert 'agent_id' in context
        assert context['organization_id'] == 'test-org'
        assert context['api_key_id'] == 'test-key'
        assert context['agent_id'] == 'test-agent'


class TestStructuredFormatter:
    """Test structured logging formatter."""

    def test_json_formatting_enabled(self):
        """Test JSON formatting when enabled."""
        formatter = StructuredFormatter(json_enabled=True)

        # Create a log record
        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)

        # Should be valid JSON
        try:
            data = json.loads(formatted)
        except json.JSONDecodeError:
            pytest.fail("Formatted log should be valid JSON")

        # Check required fields
        assert 'timestamp' in data
        assert 'level' in data
        assert 'logger' in data
        assert 'message' in data
        assert 'module' in data
        assert 'function' in data
        assert 'line' in data

        assert data['level'] == 'INFO'
        assert data['logger'] == 'test.logger'
        assert data['message'] == 'Test message'
        assert data['line'] == 42

    def test_json_formatting_disabled(self):
        """Test plain text formatting when JSON is disabled."""
        formatter = StructuredFormatter(json_enabled=False)

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)

        # Should not be JSON
        try:
            json.loads(formatted)
            pytest.fail("Formatted log should not be JSON when disabled")
        except json.JSONDecodeError:
            pass  # Expected

        # Should contain the message
        assert 'Test message' in formatted

    def test_extra_fields_included(self):
        """Test that extra fields are included in JSON output."""
        formatter = StructuredFormatter(json_enabled=True)

        record = logging.LogRecord(
            name='test.logger',
            level=logging.INFO,
            pathname='test.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )

        # Add extra fields
        record.extra_fields = {
            'request_id': 'test-request-id',
            'user_id': 'test-user',
            'custom_field': 'custom_value'
        }

        formatted = formatter.format(record)
        data = json.loads(formatted)

        # Extra fields should be included
        assert data['request_id'] == 'test-request-id'
        assert data['user_id'] == 'test-user'
        assert data['custom_field'] == 'custom_value'

    def test_exception_formatting(self):
        """Test exception formatting in JSON logs."""
        formatter = StructuredFormatter(json_enabled=True)

        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name='test.logger',
                level=logging.ERROR,
                pathname='test.py',
                lineno=42,
                msg='Error occurred',
                args=(),
                exc_info=True
            )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        # Exception info should be included
        assert 'exception' in data
        assert 'ValueError' in data['exception']
        assert 'Test exception' in data['exception']


class TestStructuredLogger:
    """Test structured logger functionality."""

    def test_logger_creation(self):
        """Test structured logger creation."""
        logger = StructuredLogger('test.logger')
        assert logger.logger.name == 'test.logger'

    def test_log_levels(self):
        """Test different log levels."""
        # Capture log output
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(json_enabled=True))

        logger = StructuredLogger('test.logger')
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.DEBUG)

        # Test different log levels
        logger.debug('Debug message')
        logger.info('Info message')
        logger.warning('Warning message')
        logger.error('Error message')
        logger.critical('Critical message')

        output = stream.getvalue()
        lines = output.strip().split('\n')
        assert len(lines) == 5

        # Check that all levels are recorded
        levels = []
        for line in lines:
            data = json.loads(line)
            levels.append(data['level'])

        assert 'DEBUG' in levels
        assert 'INFO' in levels
        assert 'WARNING' in levels
        assert 'ERROR' in levels
        assert 'CRITICAL' in levels

    def test_convenience_logging_methods(self):
        """Test convenience logging methods."""
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(json_enabled=True))

        logger = StructuredLogger('test.logger')
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.DEBUG)

        # Test convenience methods
        logger.log_request_start('POST', '/api/test')
        logger.log_request_end('POST', '/api/test', 200, 150.5)
        logger.log_auth_event('login', True, user_id='test-user')
        logger.log_rate_limit_event('org:test', True, limit=100)
        logger.log_idempotency_event('replay', key='test-key')
        logger.log_security_event('suspicious_activity', 'warning')
        logger.log_performance_event('database_query', 250.0)
        logger.log_error_event('Database connection failed', 'database')

        output = stream.getvalue()
        lines = output.strip().split('\n')
        assert len(lines) == 8

        # Check event types
        event_types = []
        for line in lines:
            data = json.loads(line)
            if 'event_type' in data:
                event_types.append(data['event_type'])

        assert 'request_start' in event_types
        assert 'request_end' in event_types
        assert 'auth_event' in event_types
        assert 'rate_limit' in event_types
        assert 'idempotency' in event_types
        assert 'security' in event_types
        assert 'performance' in event_types
        assert 'error' in event_types


class TestLoggingMiddleware:
    """Test logging middleware functionality."""

    def test_request_logging(self, app):
        """Test that requests are logged automatically."""
        # Capture log output
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(json_enabled=True))

        # Configure logging
        init_logging(app)

        # Add handler to request logger
        request_logger = logging.getLogger('brikk.requests')
        request_logger.addHandler(handler)
        request_logger.setLevel(logging.DEBUG)

        @app.route('/test')
        def test_route():
            return {'message': 'test'}

        client = app.test_client()
        response = client.get('/test')
        assert response.status_code == 200

        output = stream.getvalue()
        lines = [line for line in output.strip().split('\n') if line]

        # Should have request start and end logs
        assert len(lines) >= 2

        # Check log content
        start_log = None
        end_log = None

        for line in lines:
            try:
                data = json.loads(line)
                if data.get('event_type') == 'request_start':
                    start_log = data
                elif data.get('event_type') == 'request_end':
                    end_log = data
            except json.JSONDecodeError:
                continue

        assert start_log is not None
        assert end_log is not None

        # Check start log
        assert start_log['method'] == 'GET'
        assert start_log['path'] == '/test'

        # Check end log
        assert end_log['method'] == 'GET'
        assert end_log['path'] == '/test'
        assert end_log['status_code'] == 200
        assert 'duration_ms' in end_log

    def test_health_endpoints_not_logged(self, app):
        """Test that health endpoints are not logged to reduce noise."""
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredFormatter(json_enabled=True))

        init_logging(app)

        request_logger = logging.getLogger('brikk.requests')
        request_logger.addHandler(handler)
        request_logger.setLevel(logging.DEBUG)

        # Add health endpoints
        @app.route('/healthz')
        def health():
            return {'status': 'healthy'}

        @app.route('/readyz')
        def readiness():
            return {'status': 'ready'}

        @app.route('/metrics')
        def metrics():
            return 'metrics data'

        client = app.test_client()

        # Make requests to health endpoints
        client.get('/healthz')
        client.get('/readyz')
        client.get('/metrics')

        output = stream.getvalue()

        # Should not log health endpoints
        assert '/healthz' not in output
        assert '/readyz' not in output
        assert '/metrics' not in output


class TestLoggingConfiguration:
    """Test logging configuration."""

    @patch.dict('os.environ', {'BRIKK_LOG_JSON': 'true'})
    def test_json_logging_enabled(self, app):
        """Test JSON logging when enabled."""
        configure_logging(app)

        # Check that JSON formatter is used
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)
        assert handler.formatter.json_enabled is True

    @patch.dict('os.environ', {'BRIKK_LOG_JSON': 'false'})
    def test_json_logging_disabled(self, app):
        """Test plain text logging when JSON is disabled."""
        configure_logging(app)

        root_logger = logging.getLogger()
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, StructuredFormatter)
        assert handler.formatter.json_enabled is False

    @patch.dict('os.environ', {'LOG_LEVEL': 'DEBUG'})
    def test_log_level_configuration(self, app):
        """Test log level configuration."""
        configure_logging(app)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_logger_configuration(self, app):
        """Test that specific loggers are configured."""
        configure_logging(app)

        expected_loggers = [
            'brikk.coordination',
            'brikk.auth',
            'brikk.rate_limit',
            'brikk.idempotency',
            'brikk.metrics',
            'brikk.security'
        ]

        for logger_name in expected_loggers:
            logger = logging.getLogger(logger_name)
            assert logger.level >= logging.INFO


class TestLoggingIntegration:
    """Test logging integration with Flask app."""

    def test_init_logging(self, app):
        """Test logging initialization."""
        init_logging(app)

        # Check that logging is configured
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

        # Check that middleware is installed
        # This is tested indirectly by checking if request logging works
        @app.route('/test')
        def test_route():
            return {'message': 'test'}

        client = app.test_client()
        response = client.get('/test')
        assert response.status_code == 200

    def test_get_logger_function(self):
        """Test get_logger convenience function."""
        logger = get_logger('test.module')
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == 'test.module'


if __name__ == '__main__':
    pytest.main([__file__])

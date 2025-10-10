# Changelog

All notable changes to the Brikk Infrastructure project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-10

### Added - Stage 1: Agent Core + Echo Workflow (MVP)

#### Agent Management
- **Agent Model**: Complete agent lifecycle management with status tracking
- **POST /api/v1/agents**: Create agents with automatic API key generation
- **GET /api/v1/agents**: List user's agents with filtering and pagination
- **PBKDF2 API Key Security**: Non-reversible hashing for secure credential storage
- **One-time API Key Display**: Security-first approach with single key revelation
- **Organization-based Isolation**: Multi-tenant architecture with proper access controls

#### Echo Workflow
- **MessageLog Model**: Complete message tracking with request/response storage
- **POST /api/v1/coordination/echo**: Simple message echo for testing agent communication
- **POST /api/v1/echo**: Alternative echo endpoint with simplified interface
- **GET /api/v1/echo/logs**: Retrieve message logs scoped to authenticated user
- **Message Validation**: Comprehensive input validation and error handling

#### Authentication & Security
- **JWT Session Authentication**: Primary authentication method with ownership verification
- **Optional HMAC Request Signing**: Advanced security with X-Brikk-* headers
- **API Key Authentication**: PBKDF2-hashed keys with automatic expiration
- **Ownership Verification**: Agents can only be accessed by their owners
- **Timestamp Drift Protection**: ±300 seconds tolerance for HMAC requests

#### Rate Limiting & Performance
- **Redis Rate Limiting**: Configurable thresholds with sensible defaults
- **Per-user Rate Keys**: Intelligent rate limiting based on user identity
- **Admin Exemption**: Automatic rate limit bypass for administrative users
- **Configurable Limits**: Environment-based rate limit configuration

#### Idempotency & Reliability
- **Idempotency Protection**: Duplicate request prevention using request fingerprinting
- **Custom Idempotency Keys**: Support for 'Idempotency-Key' header
- **Response Caching**: Automatic caching of successful responses
- **Conflict Detection**: Proper handling of idempotency key conflicts

#### Audit & Monitoring
- **AuditLog Model**: Comprehensive operation tracking for compliance
- **Security Event Logging**: Authentication failures, rate limiting, access violations
- **Request Context Tracking**: Complete request lifecycle monitoring
- **Structured Logging**: JSON-formatted logs for centralized processing

#### Frontend Dashboard
- **React 18 Application**: Modern frontend with Vite build system
- **Agent Management Interface**: Create, list, and manage agents
- **Echo Test Page**: Interactive message testing and validation
- **Message Logs Viewer**: Complete request/response history
- **Dark Theme UI**: Professional interface with Brikk brand identity
- **Responsive Design**: Mobile and desktop compatibility

#### Configuration & Deployment
- **Environment-based Configuration**: Comprehensive feature flag system
- **Docker Support**: Containerized deployment with docker-compose
- **Database Migrations**: Alembic-based schema management
- **Health Check Endpoints**: Service monitoring and load balancer integration

#### Testing Infrastructure
- **Pytest Backend Tests**: Comprehensive API and model testing
- **Vitest Frontend Tests**: React component and integration testing
- **Test Fixtures**: Reusable test data and authentication helpers
- **Coverage Reporting**: Code coverage tracking and reporting

### Security Features

#### Authentication Methods
- **Primary**: JWT session authentication with user ownership verification
- **Optional**: HMAC request signing with configurable secret keys
- **Fallback**: API key authentication for programmatic access

#### Data Protection
- **PBKDF2 Hashing**: Industry-standard password hashing for API keys
- **Salt Generation**: Unique salts for each hashed credential
- **Non-reversible Storage**: API keys cannot be retrieved after creation
- **Secure Headers**: Comprehensive security header implementation

#### Access Control
- **Organization Isolation**: Multi-tenant data separation
- **User Ownership**: Agents and messages scoped to creating user
- **Permission Validation**: Comprehensive authorization checks
- **Session Management**: Secure session handling with proper expiration

### Configuration

#### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/brikk
REDIS_URL=redis://localhost:6379/0

# Security Configuration
SECRET_KEY=your-secret-key
HMAC_SECRET_KEY=your-hmac-key

# Feature Flags
BRIKK_HMAC_AUTH_ENABLED=false  # Enable optional HMAC authentication
BRIKK_RATE_LIMIT_ENABLED=true  # Enable Redis rate limiting
BRIKK_IDEM_ENABLED=true        # Enable idempotency protection
BRIKK_ALLOW_UUID4=true         # Allow UUIDv4 in requests

# Rate Limiting
RATE_LIMIT_DEFAULT=100         # Requests per window
RATE_LIMIT_WINDOW=3600         # Window size in seconds
```

#### Rate Limiting Defaults
- **Agents API**: 10 requests/minute (creation), 300/minute (listing)
- **Echo API**: 50 requests/minute (echo), 100/minute (logs)
- **Coordination API**: 100 requests/minute with burst tolerance

### API Endpoints

#### Agent Management
- `POST /api/v1/agents` - Create agent with one-time API key
- `GET /api/v1/agents` - List user's agents
- `GET /api/v1/agents/{id}` - Get specific agent details
- `PUT /api/v1/agents/{id}` - Update agent information
- `DELETE /api/v1/agents/{id}` - Soft delete agent

#### Echo Workflow
- `POST /api/v1/coordination/echo` - Full coordination echo with auth context
- `POST /api/v1/echo` - Simplified echo for testing
- `GET /api/v1/echo/logs` - Retrieve message logs

#### Health & Monitoring
- `GET /api/v1/coordination/health` - Service health check
- `GET /api/inbound/_ping` - Basic connectivity test

### Frontend Routes
- `/app/agents` - Agent management interface
- `/app/echo` - Echo test and validation page
- `/app/logs` - Message history and audit logs
- `/` - Dashboard home with navigation

### Technical Specifications

#### Backend Stack
- **Framework**: Flask 2.3+ with Blueprint architecture
- **Database**: SQLAlchemy 2.0+ ORM with PostgreSQL 13+
- **Caching**: Redis 7.0+ for rate limiting and sessions
- **Security**: PBKDF2 hashing, JWT sessions, optional HMAC
- **Testing**: pytest with comprehensive fixtures and coverage

#### Frontend Stack
- **Framework**: React 18 with Vite 5.0+ build system
- **Styling**: Tailwind CSS 3.0+ with custom dark theme
- **Components**: shadcn/ui design system for consistency
- **Icons**: Lucide React for scalable vector icons
- **Routing**: React Router DOM for client-side navigation

#### Security Architecture
- **Multi-layer Authentication**: JWT primary, HMAC optional
- **Rate Limiting**: Redis-based with configurable thresholds
- **Audit Logging**: Complete operation tracking for compliance
- **Input Validation**: Comprehensive request validation and sanitization
- **Error Handling**: Structured error responses with request tracking

### Breaking Changes
- None (initial release)

### Deprecated
- None (initial release)

### Removed
- None (initial release)

### Fixed
- None (initial release)

### Migration Guide
This is the initial release. No migration required.

### Known Issues
- Frontend tests require additional optimization for asynchronous component rendering
- HMAC authentication requires separate secret storage when using PBKDF2 API keys
- Rate limiting configuration requires Redis connection for full functionality

### Upcoming in v0.2.0
- Advanced coordination workflows with multi-step agent interactions
- Enhanced monitoring and alerting capabilities
- External system integrations via webhooks and API connectors
- Advanced agent discovery and registration features
- Performance optimizations for high-volume coordination scenarios

---

**Release Notes**: This release establishes the foundation for the Brikk Agent Coordination Platform with comprehensive security, monitoring, and user interface capabilities. The implementation provides enterprise-grade features suitable for production deployment while maintaining the flexibility for future enhancements.

**Compatibility**: Requires Python 3.9+, Node.js 18+, PostgreSQL 13+, and Redis 7.0+

**Security**: All API keys are hashed using PBKDF2 and cannot be retrieved after creation. Enable HMAC authentication for enhanced security in production environments.

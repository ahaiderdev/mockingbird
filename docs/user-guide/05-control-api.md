# Control API

The generator provides a REST API for runtime control and monitoring.

## ⚠️ Testing Status & Disclaimer

**This Control API has not been fully tested as a whole system.**

While individual endpoints have been implemented and basic functionality verified, comprehensive integration testing has not been completed. Use with caution, especially in production-like environments.

**Tested:**
- Health check and status endpoints
- Basic spike triggering
- Log level changes

**Not Fully Tested:**
- Spike behavior under high load or with many simultaneous spikes
- Edge cases and race conditions
- Long-running spike stability

**Not Implemented:**
- Config reload (returns 501)
- Error rate injection (placeholder only)
- Scenario management (placeholder only)
- Spike cancellation
- Authentication/authorization

## Base URL

```
http://localhost:8081
```

Configure the port in your config:

```yaml
global:
  control_api_port: 8081
```

## Health & Status Endpoints

### GET /healthz

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1699123456.789
}
```

**Example**:
```bash
curl http://localhost:8081/healthz
```

### GET /status

Get detailed generator status.

**Response**:
```json
{
  "uptime_seconds": 3600,
  "tick_count": 3600,
  "active_metrics": 4,
  "total_series": 156,
  "active_spikes": ["requests_total"],
  "active_scenarios": ["high_load"],
  "config": {
    "tick_interval_s": 1,
    "seed": 42
  }
}
```

**Fields**:
- `uptime_seconds`: How long the generator has been running
- `tick_count`: Number of generation cycles completed
- `active_metrics`: Number of metrics being generated
- `total_series`: Total number of time series
- `active_spikes`: Metrics currently experiencing spikes
- `active_scenarios`: Active test scenarios
- `config`: Current configuration settings

**Example**:
```bash
curl http://localhost:8081/status | jq
```

## Control Endpoints

### POST /control/spike

Trigger a temporary spike in metric values.

#### How It Works

The spike multiplier is applied to **all series** of the specified metric for the duration specified. The spike:
- ✅ Starts immediately upon request
- ✅ Automatically expires after `duration_s` seconds
- ✅ Applies to all label combinations of that metric
- ❌ Cannot be cancelled early (no stop endpoint)
- ✅ Can coexist with other spikes on different metrics

#### Spike Lifecycle

```
Time 0:00  - API request received
Time 0:00  - Spike activated, multiplier applied
Time 0:01  - Metrics are multiplied (e.g., 5x higher)
Time 0:02  - Still multiplied
...
Time 4:59  - Still multiplied
Time 5:00  - Spike automatically expires
Time 5:01  - Metrics return to normal values
Time 5:02  - Spike removed from active_spikes list
```

#### Request Body

```json
{
  "metric": "requests_total",
  "multiplier": 5.0,
  "duration_s": 300
}
```

#### Parameters

- `metric` (string): Name of the metric to spike **without prefix**
  - ✅ Correct: `"requests_total"`
  - ❌ Wrong: `"synthetic_prom_requests_total"`
- `multiplier` (float): Factor to multiply values by
  - Can be > 1.0 (increase) or < 1.0 (decrease)
  - Example: `5.0` = 5x increase, `0.5` = 50% reduction
- `duration_s` (int): How long the spike lasts in seconds
  - Spike automatically ends after this duration
  - No manual cancellation available

#### Response

```json
{
  "status": "spike_triggered",
  "metric": "requests_total",
  "multiplier": 5.0,
  "duration_s": 300
}
```

#### Example

```bash
# Trigger 5x traffic spike for 5 minutes
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 5,
    "duration_s": 300
  }'
```

#### Duration Examples

| `duration_s` | Duration | Use Case |
|--------------|----------|----------|
| `30` | 30 seconds | Quick functionality test |
| `60` | 1 minute | Rapid alert testing |
| `300` | 5 minutes | Standard load test |
| `600` | 10 minutes | Autoscaling verification |
| `1800` | 30 minutes | Sustained load test |
| `3600` | 1 hour | Long-running scenario |

#### Checking Spike Status

**While spike is active:**
```bash
curl http://localhost:8081/status | jq '.active_spikes'
# Output: ["requests_total"]
```

**After spike expires:**
```bash
curl http://localhost:8081/status | jq '.active_spikes'
# Output: []
```

**Note:** There is currently no way to check how much time remains on an active spike.

#### Multiple Simultaneous Spikes

You can trigger multiple spikes at the same time:

```bash
# Spike requests for 5 minutes
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 5,
    "duration_s": 300
  }'

# Spike latency for 10 minutes (different duration)
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "req_latency_seconds",
    "multiplier": 3,
    "duration_s": 600
  }'

# Both are now active
curl http://localhost:8081/status | jq '.active_spikes'
# Output: ["requests_total", "req_latency_seconds"]
```

Each spike expires independently based on its own `duration_s`.

#### Limitations

- ❌ **No cancellation**: Cannot stop a spike before it expires
- ❌ **No time remaining**: Cannot query how long is left
- ❌ **No spike history**: Past spikes are not logged
- ⚠️ **Metric name validation**: No validation that metric exists
- ⚠️ **Multiplier limits**: No bounds checking on multiplier value

#### Use Cases

- Test autoscaling behavior
- Trigger alerting rules
- Simulate traffic bursts
- Test backend performance under load

### POST /control/error_rate

Set error injection rate (placeholder for future implementation).

**Request Body**:
```json
{
  "metric": "requests_total",
  "rate": 0.05,
  "duration_s": 600
}
```

**Parameters**:
- `metric` (string): Metric to inject errors into
- `rate` (float): Error rate (0.0 to 1.0)
- `duration_s` (int): Duration in seconds

**Response**:
```json
{
  "status": "error_rate_set",
  "metric": "requests_total",
  "rate": 0.05,
  "duration_s": 600
}
```

**Example**:
```bash
# Inject 5% error rate for 10 minutes
curl -X POST http://localhost:8081/control/error_rate \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "rate": 0.05,
    "duration_s": 600
  }'
```

**Note**: This is a placeholder endpoint. Full implementation coming soon.

### POST /control/reload

Reload configuration without restarting.

**Response**:
```json
{
  "status": "config_reloaded",
  "timestamp": 1699123456.789
}
```

**Example**:
```bash
# Edit config file
vim configs/baseline.yaml

# Reload without restart
curl -X POST http://localhost:8081/control/reload
```

**Note**: Currently returns 501 (Not Implemented). Feature coming soon.

### POST /control/loglevel

Change log level at runtime.

**Request Body**:
```json
{
  "level": "DEBUG"
}
```

**Parameters**:
- `level` (string): Log level - DEBUG, INFO, WARNING, ERROR, CRITICAL

**Response**:
```json
{
  "status": "log_level_changed",
  "level": "DEBUG",
  "timestamp": 1699123456.789
}
```

**Example**:
```bash
# Enable debug logging
curl -X POST http://localhost:8081/control/loglevel \
  -H 'Content-Type: application/json' \
  -d '{"level": "DEBUG"}'

# Return to normal
curl -X POST http://localhost:8081/control/loglevel \
  -H 'Content-Type: application/json' \
  -d '{"level": "INFO"}'
```

**Use Cases**:
- Debug issues without restart
- Reduce log noise in production
- Temporarily increase verbosity

### POST /control/scenario

Start a named test scenario.

**Request Body**:
```json
{
  "scenario": "high_load"
}
```

**Parameters**:
- `scenario` (string): Scenario name

**Response**:
```json
{
  "status": "scenario_started",
  "scenario": "high_load",
  "timestamp": 1699123456.789
}
```

**Example**:
```bash
curl -X POST http://localhost:8081/control/scenario \
  -H 'Content-Type: application/json' \
  -d '{"scenario": "high_load"}'
```

### DELETE /control/scenario/{scenario_name}

Stop a running scenario.

**Response**:
```json
{
  "status": "scenario_stopped",
  "scenario": "high_load",
  "timestamp": 1699123456.789
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8081/control/scenario/high_load
```

**Note**: Scenario system is a placeholder for future complex test patterns.

## Common Use Cases

### 1. Trigger Traffic Spike for Testing

```bash
# Start spike
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{
    "metric": "requests_total",
    "multiplier": 10,
    "duration_s": 600
  }'

# Monitor in Prometheus/Grafana
# Observe autoscaling, alerting, etc.

# Check status
curl http://localhost:8081/status | jq '.active_spikes'
```

### 2. Debug Generation Issues

```bash
# Enable debug logging
curl -X POST http://localhost:8081/control/loglevel \
  -d '{"level": "DEBUG"}'

# Watch logs
docker-compose logs -f generator

# Return to normal
curl -X POST http://localhost:8081/control/loglevel \
  -d '{"level": "INFO"}'
```

### 3. Monitor Generator Health

```bash
# Simple health check
curl http://localhost:8081/healthz

# Detailed status
curl http://localhost:8081/status | jq

# Check uptime
curl http://localhost:8081/status | jq '.uptime_seconds'

# Check series count
curl http://localhost:8081/status | jq '.total_series'
```

### 4. Automated Testing Script

```bash
#!/bin/bash

# Start generator
docker-compose up -d generator

# Wait for startup
sleep 5

# Check health
if ! curl -f http://localhost:8081/healthz; then
  echo "Generator not healthy"
  exit 1
fi

# Trigger spike
curl -X POST http://localhost:8081/control/spike \
  -H 'Content-Type: application/json' \
  -d '{"metric": "requests_total", "multiplier": 5, "duration_s": 60}'

# Run tests
./run_load_tests.sh

# Check final status
curl http://localhost:8081/status | jq

# Cleanup
docker-compose down
```

## API Documentation

The generator uses FastAPI, which provides automatic API documentation.

### Interactive API Docs

Visit: http://localhost:8081/docs

Features:
- Interactive API explorer
- Try endpoints directly in browser
- Request/response schemas
- Example values

### OpenAPI Schema

Visit: http://localhost:8081/openapi.json

Get the complete OpenAPI 3.0 schema for:
- Code generation
- API clients
- Documentation tools

## Error Handling

### 400 Bad Request

Invalid request parameters.

**Example**:
```json
{
  "detail": "Invalid log level: TRACE"
}
```

### 500 Internal Server Error

Server-side error.

**Example**:
```json
{
  "detail": "Error triggering spike: metric not found"
}
```

### 501 Not Implemented

Feature not yet implemented.

**Example**:
```json
{
  "detail": "Config reload not implemented in engine"
}
```

## Integration Examples

### Python

```python
import requests

# Trigger spike
response = requests.post(
    "http://localhost:8081/control/spike",
    json={
        "metric": "requests_total",
        "multiplier": 5,
        "duration_s": 300
    }
)
print(response.json())

# Check status
status = requests.get("http://localhost:8081/status").json()
print(f"Total series: {status['total_series']}")
print(f"Active spikes: {status['active_spikes']}")
```

### curl

```bash
# All examples above use curl
# Add -v for verbose output
# Add -i to see response headers
# Add | jq for pretty JSON
```

### Monitoring

Add the API to your monitoring:

```yaml
# Prometheus blackbox_exporter config
modules:
  http_2xx:
    prober: http
    http:
      valid_status_codes: [200]
      
# Scrape config
scrape_configs:
  - job_name: 'generator-api'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://generator:8081/healthz
```

## Known Limitations & Missing Features

### Not Implemented

#### 1. Spike Cancellation

Currently, there is no way to cancel an active spike before it expires.

**Workaround:** Wait for the spike to expire naturally, or restart the generator.

**Proposed endpoint (not implemented):**
```bash
DELETE /control/spike/{metric_name}
```

#### 2. Config Reload

The `/control/reload` endpoint returns 501 (Not Implemented).

**Workaround:** Restart the generator to apply config changes.

#### 3. Error Rate Injection

The `/control/error_rate` endpoint is a placeholder only.

**Status:** Logs the request but does not actually inject errors.

#### 4. Scenario Management

The scenario endpoints (`POST/DELETE /control/scenario`) are placeholders for future complex test patterns.

**Status:** Tracks scenario state but does not affect metric generation.

#### 5. Authentication

The API has no authentication mechanism.

**Security Risk:** Anyone with network access can control the generator.

**Mitigation:** Use network isolation, firewall rules, or reverse proxy with auth.

#### 6. Rate Limiting

No rate limiting on API endpoints.

**Risk:** API can be overwhelmed with requests.

#### 7. Audit Logging

No audit trail of API calls.

**Workaround:** Check generator logs for INFO level messages about API calls.

#### 8. Spike Time Remaining

Cannot query how much time is left on an active spike.

**Workaround:** Track spike start time manually and calculate remaining time.

### Partially Implemented

#### 1. Spike Functionality

- ✅ Basic spike triggering works
- ✅ Automatic expiration works
- ⚠️ Not tested under high load
- ⚠️ Not tested with many simultaneous spikes
- ❌ No validation that metric exists
- ❌ No bounds checking on multiplier

#### 2. Status Endpoint

- ✅ Returns basic status
- ⚠️ Some fields may be 0 if engine not fully initialized
- ❌ No historical data
- ❌ No performance metrics

### Testing Status

| Feature | Implementation | Testing | Production Ready |
|---------|---------------|---------|------------------|
| Health check | Complete | Basic | Use with caution |
| Status | Complete | Basic | Use with caution |
| Spike trigger | Complete | Basic | Use with caution |
| Spike cancel | Not implemented | N/A | Not available |
| Log level | Complete | Basic | Safe to use |
| Config reload | Not implemented | N/A | Not available |
| Error injection | Placeholder | None | Not functional |
| Scenarios | Placeholder | None | Not functional |
| Authentication | Not implemented | N/A | Not available |

### Future Enhancements

Potential features for future versions:

**1. Spike Management**
- Cancel active spikes
- Query time remaining
- Spike history/audit log
- Gradual ramp up/down

**2. Config Management**
- Hot reload without restart
- Validate config before applying
- Rollback capability

**3. Error Injection**
- Implement actual error injection
- Configurable error patterns
- Error rate over time

**4. Scenarios**
- Pre-defined test scenarios
- Custom scenario definitions
- Scenario templates

**5. Security**
- API key authentication
- Role-based access control
- TLS/HTTPS support
- Rate limiting

**6. Observability**
- API metrics (request count, latency)
- Audit logging
- Webhook notifications
- API call history

**7. Advanced Features**
- Schedule spikes in advance
- Recurring spikes (cron-like)
- Conditional spikes (based on metrics)
- Spike templates

## Security Considerations

⚠️ **CRITICAL: The Control API has NO authentication or authorization!**

### Current Security Posture

**What's Protected:**
- ❌ Nothing - API is completely open

**What's NOT Protected:**
- Anyone with network access can:
  - Trigger spikes (potentially causing issues)
  - Change log levels
  - Query generator status
  - Attempt to reload config

### Risks

**1. Unauthorized Access**
- Malicious actors can disrupt metric generation
- No audit trail of who made changes

**2. Denial of Service**
- No rate limiting
- API can be overwhelmed with requests

**3. Information Disclosure**
- Status endpoint reveals internal state
- Config details exposed

### Recommended Mitigations

#### For Development/Testing (Current Setup)

✅ **Network Isolation**: Run in Docker internal network  
✅ **Localhost Only**: Don't expose port 8081 externally  
✅ **Firewall**: Block external access

**Example Docker Compose network isolation:**
```yaml
services:
  generator:
    ports:
      - "8000:8000"  # Metrics - OK to expose
    # Do NOT expose 8081 externally
    networks:
      - internal

networks:
  internal:
    internal: true
```

#### For Production (If Needed)

**1. Reverse Proxy with Authentication**
```nginx
location /control/ {
    auth_basic "Generator Control";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://generator:8081/control/;
}
```

**2. VPN Access Only**
- Require VPN connection to access API
- Use network policies to restrict access

**3. API Gateway**
- Use API gateway with authentication
- Add rate limiting
- Enable audit logging

**4. mTLS**
- Require client certificates
- Mutual TLS authentication

### Best Practices

- ✅ Never expose port 8081 to the internet
- ✅ Use internal Docker networks
- ✅ Monitor API access via logs
- ✅ Restrict network access with firewall rules
- ⚠️ Consider this API as "admin only"
- ⚠️ Treat any access as privileged operation

## Next Steps

- **[Metrics Reference](06-metrics-reference.md)** - All generated metrics
- **[Deployment](07-deployment.md)** - Deployment options
- **[Features](04-features.md)** - Back to features overview


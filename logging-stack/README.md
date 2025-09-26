# Cage Logging Stack

This directory contains a complete logging stack setup for the Cage application using Loki, Promtail, Grafana, and logrotate.

## Overview

The logging stack provides:
- **Loki**: Log aggregation and storage
- **Promtail**: Log collection and forwarding from existing Cage log files
- **Grafana**: Log visualization and querying interface
- **logrotate**: Automatic log rotation and compression

## Existing Log Files Supported

The stack is configured to ingest logs from:
- `../logs/api.log` - API request/response logs
- `../logs/crewai/crewai.log` - CrewAI agent activity logs
- `../logs/manage.log` - Management/health check logs
- `../logs/mcp/mcp.log` - MCP server logs

## Quick Start

1. **Start the logging stack:**
   ```bash
   cd logging-stack
   docker-compose up -d
   ```

2. **Access Grafana:**
   - URL: http://localhost:3000
   - Username: `admin`
   - Password: `admin`

3. **Verify services are running:**
   ```bash
   docker-compose ps
   ```

## LogQL Queries

### Basic Queries
- All logs: `{job="cage-logs"}`
- API logs only: `{job="cage-logs", component="api"}`
- Error logs: `{job="cage-logs"} |= "ERROR"`
- HTTP requests: `{job="cage-logs"} |= "http_request"`

### Advanced Queries
- Errors by component: `{job="cage-logs"} |= "ERROR" | json | level="ERROR"`
- API response times: `{job="cage-logs", component="api"} |= "http_response" | json | duration_ms > 1000`
- CrewAI agent activities: `{job="cage-logs", component="crewai"} |= "Agent Activity"`

## Configuration Details

### Loki Configuration
- Retention: 30 days (720h)
- Storage: Filesystem-based
- Max line size: 256KB
- Ingestion rate: 16MB/s

### Promtail Configuration
- Parses JSON logs with fields: timestamp, level, message, file, line
- Extracts labels for filtering: level, file, component, event, method, status_code
- Handles different timestamp formats from different components

### Log Rotation
- Rotates logs when they reach 50MB
- Keeps 14 rotated files
- Compresses old logs
- Uses copytruncate to avoid log loss
- Runs every 5 minutes

## Troubleshooting

### Services Not Starting
```bash
# Check service logs
docker-compose logs loki
docker-compose logs promtail
docker-compose logs grafana
```

### No Logs in Grafana
1. Verify Promtail is reading log files:
   ```bash
   docker-compose logs promtail
   ```

2. Check Loki is receiving logs:
   ```bash
   curl http://localhost:3100/ready
   ```

3. Verify log file permissions:
   ```bash
   ls -la ../logs/
   ```

### Log Rotation Issues
```bash
# Check logrotate status
docker-compose exec logrotate cat /var/lib/logrotate/status

# Force rotation
docker-compose exec logrotate logrotate -f /etc/logrotate.conf
```

## Monitoring

### Health Checks
- Loki: http://localhost:3100/ready
- Grafana: http://localhost:3000/api/health

### Metrics
- Promtail metrics: http://localhost:9080/metrics
- Loki metrics: http://localhost:3100/metrics

## Customization

### Adding New Log Files
1. Add new scrape config in `promtail/config.yml`
2. Add rotation rule in `logrotate/logrotate.conf`
3. Restart services: `docker-compose restart promtail logrotate`

### Changing Retention
Edit `loki/config.yml` and modify:
- `retention_period` in `table_manager`
- `reject_old_samples_max_age` in `limits_config`

## Security Notes

- Grafana admin credentials are set to `admin/admin` (change in production)
- Loki has authentication disabled (enable for production)
- All services run in Docker containers with limited privileges

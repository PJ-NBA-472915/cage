#!/bin/bash

# Setup script for Grafana datasource and dashboard
# This script configures Grafana to connect to Loki and creates a basic dashboard
# Use this when running the main docker-compose.yml with logging services

echo "Setting up Grafana datasource and dashboard..."

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
until curl -s http://localhost:3000/api/health > /dev/null; do
    echo "Waiting for Grafana..."
    sleep 2
done

echo "Grafana is ready!"

# Add Loki datasource
echo "Adding Loki datasource..."
curl -X POST \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @logging-stack/grafana-datasource.json \
  http://localhost:3000/api/datasources

echo ""
echo "Loki datasource added!"

# Import dashboard
echo "Importing dashboard..."
curl -X POST \
  -H "Content-Type: application/json" \
  -u admin:admin \
  -d @logging-stack/grafana-dashboard.json \
  http://localhost:3000/api/dashboards/db

echo ""
echo "Dashboard imported!"

echo ""
echo "Setup complete! You can now access Grafana at:"
echo "  URL: http://localhost:3000"
echo "  Username: admin"
echo "  Password: admin"
echo ""
echo "Useful LogQL queries:"
echo "  All logs: {job=\"cage-logs\"}"
echo "  API logs: {job=\"cage-logs\", component=\"api\"}"
echo "  Error logs: {job=\"cage-logs\"} |= \"ERROR\""
echo "  CrewAI logs: {job=\"cage-logs\", component=\"crewai\"}"
echo ""
echo "To start all services including logging:"
echo "  docker-compose up -d"
echo ""
echo "To start only logging services:"
echo "  docker-compose up -d loki promtail grafana logrotate"

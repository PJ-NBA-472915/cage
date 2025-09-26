#!/bin/sh

# Install logrotate package
echo "Installing logrotate package..."
apk add --no-cache logrotate

# Create logrotate status directory
mkdir -p /var/lib/logrotate

# Start cron daemon
echo "Starting cron daemon..."
crond -f -l 8

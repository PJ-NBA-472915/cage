FROM alpine:3.20

# Install logrotate and busybox (includes crond)
RUN apk add --no-cache logrotate

# Create logrotate status directory
RUN mkdir -p /var/lib/logrotate

# Copy configuration files
COPY logrotate.conf /etc/logrotate.conf
COPY crontab /etc/crontabs/root

# Create a simple startup script
RUN echo '#!/bin/sh' > /startup.sh && \
    echo 'echo "Starting logrotate service..."' >> /startup.sh && \
    echo 'crond -f -l 8 &' >> /startup.sh && \
    echo 'wait' >> /startup.sh && \
    chmod +x /startup.sh

CMD ["/startup.sh"]

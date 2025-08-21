#!/bin/bash

# Handle interrupt signals gracefully
trap 'echo "Received interrupt signal, exiting..."; exit 0' INT TERM

sleep infinity
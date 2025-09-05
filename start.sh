#!/bin/bash

if [ "$HTTPS_ENABLED" = "true" ]; then
    echo "🔒 Starting HTTPS server..."
    uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-certfile ssl/cert.pem --ssl-keyfile ssl/key.pem --reload
else
    echo "🌐 Starting HTTP server..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

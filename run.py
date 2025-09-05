import uvicorn
from dotenv import load_dotenv
import os
import argparse

load_dotenv()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FastAPI server")
    parser.add_argument("--https", action="store_true", help="Run with HTTPS")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    
    args = parser.parse_args()
    
    if args.https:
        print("🔒 Starting HTTPS server...")
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=8443,
            ssl_certfile="ssl/cert.pem",
            ssl_keyfile="ssl/key.pem",
            reload=True
        )
    else:
        print("🌐 Starting HTTP server...")
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=True
        )

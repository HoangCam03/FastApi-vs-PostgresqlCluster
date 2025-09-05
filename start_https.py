#!/usr/bin/env python3
"""
Script to start Docker containers with HTTPS
"""

import os
import subprocess
import sys
from pathlib import Path

def check_ssl_certificates():
    """Check if SSL certificates exist"""
    ssl_dir = Path("ssl")
    cert_path = ssl_dir / "cert.pem"
    key_path = ssl_dir / "key.pem"
    
    if not cert_path.exists() or not key_path.exists():
        print("❌ SSL certificates not found!")
        print("Generating SSL certificates...")
        
        try:
            # Import từ thư mục ssl
            import sys
            sys.path.append('ssl')
            from generate_ssl_python import generate_ssl_certificate
            if not generate_ssl_certificate():
                print("Failed to generate SSL certificates!")
                sys.exit(1)
        except ImportError:
            print("Please create ssl/generate_ssl_python.py first!")
            sys.exit(1)
    
    print("✅ SSL certificates found!")

def start_with_https():
    """Start with HTTPS"""
    print("🔒 Starting with HTTPS...")
    
    # Check SSL certificates
    check_ssl_certificates()
    
    # Start database
    print("📊 Starting database...")
    subprocess.run(["docker-compose", "-f", "docker-compose.db.yml", "up", "-d"])
    
    # Start application with HTTPS
    print("🚀 Starting application with HTTPS...")
    subprocess.run(["docker-compose", "-f", "docker-compose.https.yml", "up", "--build"])

def start_with_http():
    """Start with HTTP"""
    print(" Starting with HTTP...")
    
    # Start database
    print("📊 Starting database...")
    subprocess.run(["docker-compose", "-f", "docker-compose.db.yml", "up", "-d"])
    
    # Start application with HTTP
    print("🚀 Starting application with HTTP...")
    subprocess.run(["docker-compose", "up", "--build"])

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Docker containers")
    parser.add_argument("--https", action="store_true", help="Start with HTTPS")
    
    args = parser.parse_args()
    
    if args.https:
        start_with_https()
    else:
        start_with_http()

if __name__ == "__main__":
    main()

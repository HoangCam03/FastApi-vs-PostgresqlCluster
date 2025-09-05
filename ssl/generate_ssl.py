import os
import subprocess
from pathlib import Path

def generate_ssl_certificate():
    """Generate self-signed SSL certificate for Docker development"""
    
    # Get current directory (ssl folder)
    current_dir = Path(__file__).parent
    
    # Certificate paths
    cert_path = current_dir / "cert.pem"
    key_path = current_dir / "key.pem"
    
    # Generate certificate using OpenSSL
    cmd = [
        "openssl", "req", "-x509", "-newkey", "rsa:4096",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", "365",
        "-nodes",
        "-subj", "/C=VN/ST=Hanoi/L=Hanoi/O=Development/CN=localhost"
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ SSL certificate generated successfully!")
        print(f" Certificate: {cert_path}")
        print(f"🔑 Private key: {key_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error generating SSL certificate: {e}")
        return False
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL first.")
        return False

if __name__ == "__main__":
    generate_ssl_certificate()

import os
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from pathlib import Path

def create_browser_certificate():
    """Create certificate file for browser import"""
    
    # Get current directory (ssl folder)
    current_dir = Path(__file__).parent
    
    # Certificate paths
    cert_pem_path = current_dir / "cert.pem"
    cert_crt_path = current_dir / "cert.crt"
    
    try:
        # Read existing certificate
        with open(cert_pem_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        
        # Write certificate in DER format for browser
        with open(cert_crt_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.DER))
        
        print(f"✅ Browser certificate created successfully!")
        print(f" Certificate: {cert_crt_path}")
        print(f"�� You can now import this certificate into your browser")
        return True
        
    except FileNotFoundError:
        print("❌ SSL certificate not found. Please run generate_ssl_python.py first!")
        return False
    except Exception as e:
        print(f"❌ Error creating browser certificate: {e}")
        return False

if __name__ == "__main__":
    create_browser_certificate()

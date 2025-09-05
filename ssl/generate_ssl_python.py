import os
import ssl
import socket
import ipaddress
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta, timezone
from pathlib import Path

def generate_ssl_certificate():
    """Generate self-signed SSL certificate using Python cryptography"""
    
    # Get current directory (ssl folder)
    current_dir = Path(__file__).parent
    
    # Certificate paths
    cert_path = current_dir / "cert.pem"
    key_path = current_dir / "key.pem"
    cert_crt_path = current_dir / "cert.crt"
    
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "VN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Hanoi"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Hanoi"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Development"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        # Get localhost IP address
        try:
            localhost_ip = socket.gethostbyname("localhost")
            ip_address = ipaddress.IPv4Address(localhost_ip)
        except:
            # Fallback to 127.0.0.1 if localhost resolution fails
            ip_address = ipaddress.IPv4Address("127.0.0.1")
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.DNSName("127.0.0.1"),
                x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                x509.IPAddress(ipaddress.IPv4Address("0.0.0.0")),
                x509.IPAddress(ip_address),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Write private key
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Write certificate (PEM format)
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write certificate (DER format for browser)
        with open(cert_crt_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.DER))
        
        print(f"✅ SSL certificate generated successfully!")
        print(f" Certificate (PEM): {cert_path}")
        print(f" Certificate (DER): {cert_crt_path}")
        print(f"🔑 Private key: {key_path}")
        print(f"📝 Browser certificate ready for import!")
        return True
        
    except ImportError:
        print("❌ cryptography library not found. Installing...")
        os.system("pip install cryptography")
        return generate_ssl_certificate()
    except Exception as e:
        print(f"❌ Error generating SSL certificate: {e}")
        return False

if __name__ == "__main__":
    generate_ssl_certificate()

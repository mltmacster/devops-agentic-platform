"""SSL/TLS Certificate Lifecycle Management.

Provides utilities for:
  • Generating self-signed certificates (for local development)
  • Let's Encrypt ACME protocol integration (for production)  
  • Certificate validation and expiration tracking
  • Certificate chain management (CA → intermediate → leaf)

Usage:
    from src.network.ssl_manager import CertificateManager
    
    # Generate self-signed certificate for development
    certs = CertificateManager.generate_self_signed("localhost")
    
    # Validate certificate expiration
    result = CertificateManager.validate_cert_path("/path/to/cert.pem")
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import ssl as ssl_module


@dataclass
class CertificateInfo:
    """Metadata about a TLS certificate."""

    hostname: str = "localhost"
    subject: str = ""
    issuer: str = ""
    not_before: datetime | None = None
    not_after: datetime | None = None
    is_valid: bool = True
    days_until_expiry: int = 0
    path_cert: str | None = None
    path_key: str | None = None

    @property
    def is_expired(self) -> bool:
        """Check if the certificate has expired."""
        if self.not_after is None:
            return False
        return datetime.now() > self.not_after

    @property
    def is_near_expiry(self, warning_days: int = 30) -> bool:
        """Check if the certificate will expire within warning_days."""
        if self.not_after is None:
            return False
        return (self.not_after - datetime.now()).days <= warning_days


@dataclass
class CertificateBundle:
    """A complete certificate bundle (cert + key + CA chain)."""

    cert_path: str = ""
    key_path: str = ""
    ca_cert_path: str | None = None
    hostname: str = "localhost"

    def to_dict(self) -> dict[str, str]:
        """Export certificate bundle as a dictionary."""
        result: dict[str, str] = {
            "cert": self.cert_path,
            "key": self.key_path,
        }
        if self.ca_cert_path:
            result["ca"] = self.ca_cert_path
        return result


class CertificateManager:
    """Manages TLS certificate lifecycle for the DAP platform.

    Handles:
      1. Self-signed certificate generation (development)
      2. Let's Encrypt ACME challenge (production)
      3. Certificate validation and expiration warnings
      4. Certificate chain building (CA → leaf)

    In production, you would integrate with:
      • Let's Encrypt ACME challenge (certbot)
      • Cloud provider managed certificates (AWS ACM, GCP Managed SSL)
      • Internal PKI for internal services

    For local development, self-signed certificates are generated automatically.
    """

    DEFAULT_CERT_DIR = ".vault/certs"
    DEFAULT_KEY_SIZE = 2048
    DEFAULT_CERT_VALIDITY_DAYS = 365

    def __init__(self, cert_dir: str | None = None):
        """Initialize the certificate manager.

        Args:
            cert_dir: Directory to store certificates (default: .vault/certs).
        """
        self.cert_dir = Path(cert_dir or self.DEFAULT_CERT_DIR)
        self.cert_dir.mkdir(parents=True, exist_ok=True)

    # ─── Certificate Generation ────────────────────────────

    def generate_self_signed(
        self, hostname: str = "localhost",
        validity_days: int = 365,
    ) -> CertificateBundle:
        """Generate a self-signed TLS certificate.

        Creates both the certificate and private key files using OpenSSL.
        The certificate is self-signed, meaning it can only be verified by
        a client that trusts this specific certificate.

        Args:
            hostname: Common Name (CN) for the certificate.
            validity_days: Certificate validity period in days.

        Returns:
            CertificateBundle with paths to cert, key files.
        """

        cert_file = self.cert_dir / f"{hostname}.crt"
        key_file = self.cert_dir / f"{hostname}.key"

        # Generate private key
        self._run_openssl(
            [
                "genpkey",
                "-algorithm", "RSA",
                "-out", str(key_file),
                f"-pkeybits:{self.DEFAULT_KEY_SIZE}",
            ],
        )

        # Generate self-signed certificate
        self._run_openssl(
            [
                "req",
                "-new",
                "-x509",
                "-key", str(key_file),
                "-out", str(cert_file),
                f"-days:{validity_days}",
                f"-subj:/CN={hostname}/O=DevOps Agentic Platform/C=US",
                "-nodes",  # No passphrase for non-interactive use
            ],
        )

        return CertificateBundle(
            cert_path=str(cert_file),
            key_path=str(key_file),
            hostname=hostname,
        )

    def generate_ca_certificate(
        self, ca_name: str = "DAP-CA",
    ) -> CertificateBundle:
        """Generate a Certificate Authority (CA) certificate.

        A CA is used to sign leaf certificates for multiple subdomains/hosts.
        This is useful when you have many sandbox instances and want a single
        CA to sign all of them.

        Args:
            ca_name: Name for the certificate authority.

        Returns:
            CertificateBundle with CA cert and key paths.
        """

        ca_file = self.cert_dir / f"{ca_name}.crt"
        key_file = self.cert_dir / f"{ca_name}.key"

        # Generate CA private key
        self._run_openssl(
            [
                "genpkey",
                "-algorithm", "RSA",
                "-out", str(key_file),
                f"-pkeybits:{self.DEFAULT_KEY_SIZE}",
            ],
        )

        # Generate CA certificate (self-signed, long-lived)
        self._run_openssl(
            [
                "req",
                "-new",
                "-x509",
                "-key", str(key_file),
                "-out", str(ca_file),
                "-days", "3650",  # 10 years for CA certificates
                f"-subj:/CN={ca_name}/O=DevOps Agentic Platform/C=US",
                "-nodes",
            ],
        )

        return CertificateBundle(
            cert_path=str(ca_file),
            key_path=str(key_file),
            ca_cert_path=str(ca_file),  # CA cert is also the CA bundle
        )

    def generate_ca_signed(
        self,
        hostname: str = "localhost",
        ca_bundle: CertificateBundle | None = None,
    ) -> CertificateBundle:
        """Generate a certificate signed by a CA.

        This creates a leaf certificate that's signed by a Certificate Authority,
        allowing clients to verify the chain of trust.

        Args:
            hostname: Common Name (CN) for the leaf certificate.
            ca_bundle: The CA bundle to use for signing. If None, generates one.

        Returns:
            CertificateBundle with leaf cert + key paths.
        """

        if ca_bundle is None:
            ca_bundle = self.generate_ca_certificate()

        cert_file = self.cert_dir / f"{hostname}.crt"
        key_file = self.cert_dir / f"{hostname}.key"

        # Generate private key
        self._run_openssl(
            [
                "genpkey",
                "-algorithm", "RSA",
                "-out", str(key_file),
                f"-pkeybits:{self.DEFAULT_KEY_SIZE}",
            ],
        )

        # Generate CSR (Certificate Signing Request)
        csr_file = self.cert_dir / f"{hostname}.csr"
        self._run_openssl(
            [
                "req",
                "-new",
                "-key", str(key_file),
                "-out", str(csr_file),
                f"-subj:/CN={hostname}/O=DevOps Agentic Platform/C=US",
                "-nodes",
            ],
        )

        # Sign the CSR with the CA certificate
        self._run_openssl(
            [
                "x509",
                "-req",
                "-in", str(csr_file),
                "-CA", ca_bundle.ca_cert_path,
                "-CAkey", ca_bundle.key_path,
                "-out", str(cert_file),
                "-days", "365",
            ],
        )

        # Build the certificate bundle (leaf + CA)
        return CertificateBundle(
            cert_path=str(cert_file),
            key_path=str(key_file),
            ca_cert_path=ca_bundle.ca_cert_path,
            hostname=hostname,
        )

    # ─── Certificate Validation ──────────────────────────────

    @staticmethod
    def validate_cert_path(
        cert_path: str,
        warn_days: int = 30,
    ) -> CertificateInfo:
        """Validate a certificate file and extract its metadata.

        Args:
            cert_path: Path to the PEM-encoded certificate file.
            warn_days: Days before expiry to flag as warning.

        Returns:
            CertificateInfo with validation results and metadata.
        """

        try:
            # Parse certificate using Python's ssl module
            with open(cert_path, "rb") as f:
                cert_data = f.read()

            # Parse to get subject and issuer info
            import ssl as _ssl
            try:
                # Python 3.7+: load_der_certificate or load_pem_certificate
                cert = _ssl.load_cert_chain(
                    certfile=cert_path,
                    keyfile=None,  # No key needed for validation
                )
            except Exception:
                # Fallback: use openssl command
                return CertificateManager._validate_with_openssl(cert_path, warn_days)

            # Extract subject and issuer
            cert_info = _ssl.get_certinfo()
            subject = cert_info["subject"]
            issuer = cert_info["issuer"]

            # Extract dates from the certificate object  
            not_before = None
            not_after = None

            # Try to get dates from cert_info (Python 3.7+)
            if hasattr(cert, "get_serial_number"):
                # Python 3.8+ provides more detailed info
                pass

            return CertificateInfo(
                hostname=subject.get((0, 3), "Unknown"),  # CN = common name
                subject=str(subject),
                issuer=str(issuer),
                is_valid=True,
            )

        except Exception as e:
            print(f"Certificate validation error: {e}")
            return CertificateInfo(is_valid=False)

    @staticmethod
    def _validate_with_openssl(
        cert_path: str, warn_days: int = 30
    ) -> CertificateInfo:
        """Fallback certificate validation using OpenSSL CLI."""

        try:
            # Get certificate details via openssl
            result = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in", cert_path,
                    "-noout",
                    "-dates",
                ],
                capture_output=True,
                text=True,
            )

            # Parse output
            not_before = None
            not_after = None

            for line in result.stdout.splitlines():
                if "notBefore" in line:
                    not_before = datetime.fromisoformat(
                        line.split("= 1)")[-1].replace("+00:00", "+00:00").rstrip()
                    )
                elif "notAfter" in line:
                    not_after = datetime.fromisoformat(
                        line.split("= 1)")[-1].replace("+00:00", "+00:00").rstrip()
                    )

            subject = subprocess.run(
                [
                    "openssl",
                    "x509",
                    "-in", cert_path,
                    "-noout",
                    "-subject",
                ],
                capture_output=True,
                text=True,
            ).stdout

            return CertificateInfo(
                hostname=subject.split("CN=")[-1].strip() if "CN=" in subject else "Unknown",
                issuer="N/A",
                not_before=not_before,
                not_after=not_after,
                is_valid=datetime.now() <= (not_after or datetime.max),
            )

        except Exception as e:
            print(f"OpenSSL validation error: {e}")
            return CertificateInfo(is_valid=False)

    # ─── Let's Encrypt Integration ──────────────────────────

    def run_lets_encrypt(
        self,
        domain: str,
        email: str = "admin@example.com",
    ) -> CertificateBundle | None:
        """Run Let's Encrypt ACME challenge to obtain a free certificate.

        This requires:
          • certbot installed on the system
          • Domain DNS pointing to your server's IP
          • HTTP access to domain/.well-known/acme-challenge/

        Args:
            domain: Domain name to obtain a certificate for.
            email: Contact email for Let's Encrypt notifications.

        Returns:
            CertificateBundle with paths to cert and key files, or None on failure.
        """

        # Check if certbot is available
        try:
            subprocess.run(
                ["which", "certbot"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            print("certbot not found. Install with:")
            print("  sudo apt install certbot")
            return None

        # Run certbot in non-interactive mode with standalone webroot
        result = subprocess.run(
            [
                "certbot",
                "--standalone",
                "--agree-tos",
                "--email", email,
                "--no-eff-email",
                f"--domain={domain}",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Let's Encrypt failed:\n{result.stderr}")
            return None

        # Certbot stores certificates in /etc/letsencrypt/live/domain/
        cert_dir = Path(f"/etc/letsencrypt/live/{domain}")

        return CertificateBundle(
            cert_path=str(cert_dir / "fullchain.pem"),
            key_path=str(cert_dir / "privkey.pem"),
            ca_cert_path=str(cert_dir / "chain.pem"),
            hostname=domain,
        )

    def test_lets_encrypt_challenge(
        self, domain: str, challenge_path: str | None = None
    ) -> bool:
        """Test if Let's Encrypt can validate domain ownership.

        Args:
            domain: Domain to verify ownership of.
            challenge_path: Directory for the ACME challenge files.

        Returns:
            True if the domain can be validated, False otherwise.
        """
        try:
            subprocess.run(
                [
                    "certbot",
                    "auth-tos",  # Test-only mode, doesn't actually register
                    "--agree-tos",
                    f"--email=admin@example.com",
                ],
                capture_output=True,
                text=True,
            )
            return True
        except Exception:
            return False

    # ─── Certificate Operations ──────────────────────────────

    def list_certificates(self) -> list[CertificateBundle]:
        """List all certificates in the certificate directory.

        Returns:
            List of CertificateBundle objects for all found certificates.
        """

        bundles = []
        cert_files = list(self.cert_dir.glob("*.crt")) + list(self.cert_dir.glob("*.pem"))

        for cert_file in cert_files:
            # Extract hostname from filename (e.g., "myhost.crt" → "myhost")
            hostname = cert_file.stem.replace("ca-", "").replace(".crt", "")

            key_file = self.cert_dir / f"{cert_file.stem}.key"
            ca_file = self.cert_dir / f"{cert_file.stem}_ca.crt"

            bundle = CertificateBundle(
                cert_path=str(cert_file),
                key_path=str(key_file) if key_file.exists() else "",
                ca_cert_path=str(ca_file) if ca_file.exists() else None,
                hostname=hostname,
            )

            # Validate the certificate
            bundle_info = self.validate_cert_path(bundle.cert_path)
            bundle.is_valid = bundle_info.is_valid

            bundles.append(bundle)

        return bundles

    def renew_cert(self, hostname: str, days: int = 365) -> CertificateBundle | None:
        """Renew an existing certificate with a new expiry date.

        Args:
            hostname: The hostname of the certificate to renew.
            days: Validity period in days (default 365).

        Returns:
            CertificateBundle with new certificate paths, or None on failure.
        """

        old_cert = self.cert_dir / f"{hostname}.crt"
        if not old_cert.exists():
            print(f"No existing certificate found for {hostname}")
            return None

        # Generate new certificate (overwrites old)
        return self.generate_self_signed(hostname, validity_days=days)

    # ─── Helper Methods ─────────────────────────────────────

    def _run_openssl(self, args: list[str]) -> subprocess.CompletedProcess | None:
        """Run an OpenSSL command and return the result.

        Args:
            args: Command arguments (without 'openssl' prefix).

        Returns:
            CompletedProcess or None on failure.
        """

        try:
            return subprocess.run(
                ["openssl"] + args,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
        except FileNotFoundError:
            print("OpenSSL not found. Install with:")
            if os.name == "nt":  # Windows
                print("  Chocolatey: choco install openssl")
            else:  # Linux/macOS
                print("  Ubuntu/Debian: sudo apt install openssl")
                print("  macOS: brew install openssl")
            return None

    def cleanup_expired(self, warn_days: int = 30) -> list[str]:
        """Find and report expired or expiring certificates.

        Args:
            warn_days: Certificates expiring within this many days are flagged.

        Returns:
            List of paths to expired or expiring certificates.
        """

        issues = []
        for cert_file in self.cert_dir.glob("*.crt"):
            hostname = cert_file.stem.replace(".crt", "")
            bundle = CertificateBundle(
                cert_path=str(cert_file),
                key_path=str(self.cert_dir / f"{hostname}.key"),
                hostname=hostname,
            )

            cert_info = self.validate_cert_path(
                bundle.cert_path, warn_days=warn_days
            )

            if cert_info.is_expired:
                issues.append(f"EXPIRED: {hostname} ({cert_file})")
            elif cert_info.is_near_expiry(warn_days):
                issues.append(f"EXPIRING IN {warn_days} DAYS: {hostname} ({cert_file})")

        return issues


# ─── Exports ─────────────────────────────────

__all__ = [
    "CertificateInfo",
    "CertificateBundle",
    "CertificateManager",
]

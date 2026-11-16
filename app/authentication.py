"""
Mutual Authentication and Secure Session Establishment for OneClick LAN Transfer.
Implements:
1. Zero-Windows-credential pairing: 6-digit random codes.
2. Ephemeral TLS self-signed certificate generation.
3. Mutual HMAC-SHA256 challenge-response handshake preventing MITM and unauthorized access.
4. Cryptographic session token generation.
"""

import ssl
import hmac
import json
import secrets
import hashlib
import logging
import datetime
from pathlib import Path
from typing import Tuple, Optional

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger("OneClickLAN.Authentication")

PAIRING_CODE_LENGTH = 6

def generate_pairing_code() -> Tuple[str, str]:
    """
    Generate a cryptographically secure 6-digit pairing code.
    Returns (display_code, raw_code) e.g. ("749-218", "749218").
    """
    digits = [str(secrets.randbelow(10)) for _ in range(PAIRING_CODE_LENGTH)]
    raw_code = "".join(digits)
    display_code = f"{raw_code[:3]}-{raw_code[3:]}"
    return display_code, raw_code

def normalize_pairing_code(code: str) -> str:
    """Strip spaces, dashes, and non-digit characters from user input."""
    return "".join(c for c in code if c.isdigit())

def generate_session_token() -> str:
    """Generate a random 32-byte hexadecimal session token."""
    return secrets.token_hex(32)

def compute_hmac(secret_key: str, message: str) -> str:
    """Compute HMAC-SHA256 for challenge-response authentication."""
    key_bytes = secret_key.encode("utf-8")
    msg_bytes = message.encode("utf-8")
    return hmac.new(key_bytes, msg_bytes, hashlib.sha256).hexdigest()

def generate_ephemeral_tls_cert(cert_path: Path, key_path: Path) -> Tuple[Path, Path]:
    """
    Generates a secure ephemeral self-signed X.509 certificate and 2048-bit RSA private key.
    Valid for direct LAN transfer sessions.
    """
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate RSA private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Subject & Issuer
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"OneClickLAN Host"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OneClick LAN Transfer")
    ])

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=7))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Write private key
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Write certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    logger.info(f"Generated ephemeral TLS certificate at {cert_path}")
    return cert_path, key_path

def create_server_ssl_context(cert_file: Path, key_file: Path) -> ssl.SSLContext:
    """
    Configure a secure TLS server context using TLS 1.2+ and strong cipher suites.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    return context

def create_client_ssl_context() -> ssl.SSLContext:
    """
    Configure a TLS client context for direct Cat6 link.
    Mutual identity verification is enforced via the HMAC-SHA256 challenge-response.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

def server_authenticate_client(conn, expected_pairing_code: str) -> Tuple[bool, str]:
    """
    Host side of mutual authentication:
    1. Send 32-byte server challenge.
    2. Receive client HMAC and client challenge.
    3. Verify client HMAC using pairing code.
    4. Respond with server HMAC and new session token.
    Returns (success, session_token_or_error_msg).
    """
    try:
        norm_key = normalize_pairing_code(expected_pairing_code)
        server_challenge = secrets.token_hex(16)

        # 1. Send challenge to client
        challenge_msg = json.dumps({"action": "CHALLENGE", "server_challenge": server_challenge}) + "\n"
        conn.sendall(challenge_msg.encode("utf-8"))

        # 2. Read client response
        raw_resp = conn.makefile("r", encoding="utf-8").readline()
        if not raw_resp:
            return False, "Client closed connection before authentication."

        data = json.loads(raw_resp.strip())
        client_hmac = data.get("client_hmac")
        client_challenge = data.get("client_challenge")

        if not client_hmac or not client_challenge:
            return False, "Malformed authentication payload from client."

        # 3. Verify client's HMAC
        expected_client_hmac = compute_hmac(norm_key, server_challenge)
        if not hmac.compare_digest(client_hmac, expected_client_hmac):
            logger.warning("Client provided INVALID pairing code.")
            fail_resp = json.dumps({"status": "FAILED", "reason": "Invalid pairing code."}) + "\n"
            conn.sendall(fail_resp.encode("utf-8"))
            return False, "Invalid pairing code provided by client."

        # 4. Generate server HMAC and session token
        server_hmac = compute_hmac(norm_key, client_challenge)
        session_token = generate_session_token()

        ok_resp = json.dumps({
            "status": "OK",
            "server_hmac": server_hmac,
            "session_token": session_token
        }) + "\n"
        conn.sendall(ok_resp.encode("utf-8"))

        logger.info("Client successfully authenticated with pairing code.")
        return True, session_token

    except Exception as e:
        logger.error(f"Error during server authentication: {e}")
        return False, str(e)

def client_authenticate_host(conn, input_pairing_code: str) -> Tuple[bool, str]:
    """
    Client side of mutual authentication:
    1. Receive server challenge.
    2. Compute HMAC and send along with client challenge.
    3. Receive server response and verify server HMAC.
    4. Store session token.
    Returns (success, session_token_or_error_msg).
    """
    try:
        norm_key = normalize_pairing_code(input_pairing_code)
        reader = conn.makefile("r", encoding="utf-8")

        # 1. Receive server challenge
        raw_msg = reader.readline()
        if not raw_msg:
            return False, "Host terminated connection unexpectedly."

        data = json.loads(raw_msg.strip())
        if data.get("action") != "CHALLENGE":
            return False, f"Unexpected handshake response: {data}"

        server_challenge = data.get("server_challenge")
        client_challenge = secrets.token_hex(16)
        client_hmac = compute_hmac(norm_key, server_challenge)

        # 2. Send client response
        resp_payload = json.dumps({
            "action": "RESPONSE",
            "client_hmac": client_hmac,
            "client_challenge": client_challenge
        }) + "\n"
        conn.sendall(resp_payload.encode("utf-8"))

        # 3. Receive host verification
        raw_auth_result = reader.readline()
        if not raw_auth_result:
            return False, "Host closed connection during verification."

        res_data = json.loads(raw_auth_result.strip())
        if res_data.get("status") != "OK":
            reason = res_data.get("reason", "Authentication rejected by host.")
            return False, reason

        server_hmac = res_data.get("server_hmac")
        expected_server_hmac = compute_hmac(norm_key, client_challenge)

        if not hmac.compare_digest(server_hmac, expected_server_hmac):
            return False, "Host verification failed: Host does not possess matching pairing code."

        session_token = res_data.get("session_token")
        logger.info("Successfully authenticated with Host.")
        return True, session_token

    except Exception as e:
        logger.error(f"Error during client authentication: {e}")
        return False, str(e)

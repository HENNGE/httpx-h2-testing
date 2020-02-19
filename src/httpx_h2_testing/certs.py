import datetime
from typing import Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKeyWithSerialization
from cryptography.x509 import Certificate
from cryptography.x509.oid import NameOID

BACKEND = default_backend()


def make_cert_and_key() -> Tuple[Certificate, RSAPrivateKeyWithSerialization]:

    now = datetime.datetime.utcnow()
    key: RSAPrivateKeyWithSerialization = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=BACKEND
    )
    cert: Certificate = (
        x509.CertificateBuilder()
        .subject_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "httpx-h2-testing")])
        )
        .issuer_name(
            x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "httpx-h2-testing")])
        )
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=10_000))
        .serial_number(x509.random_serial_number())
        .public_key(key.public_key())
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(private_key=key or key, algorithm=hashes.SHA256(), backend=BACKEND)
    )
    return cert, key

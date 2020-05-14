"""
A user-friendly API to public and private RSA keys.
"""

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa


class PrivateKey:
    def __init__(self, _key):
        assert isinstance(_key, rsa.RSAPrivateKey)
        self._key = _key

    @classmethod
    def generate(cls, size=2048):
        """ Generate a new private key, reprsenting an asymetric RSA key pair.
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=size, backend=default_backend()
        )
        return PrivateKey(private_key)

    @classmethod
    def from_str(cls, s, password):
        """ Load a private RSA key from a string.
        """
        assert isinstance(s, str)
        private_key = serialization.load_pem_private_key(
            s.replace("_", "\n").encode(),
            password=password.encode() if password else None,
            backend=default_backend(),
        )
        return PrivateKey(private_key)

    def to_str(self, password):
        """ Serialize this private RSA key to a string, encrypting it with the
        given password (or not encrypting when password is None.
        The returned string has no newlines.
        """
        if password is None:
            encryption = serialization.NoEncryption()
        else:
            encryption = serialization.BestAvailableEncryption(password.encode())
        return (
            self._key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=encryption,
            )
            .decode()
            .replace("\n", "_")
        )

    def get_id(self):
        """ Get a short string that identifies this key. The corresponding
        public key has the same id.
        """
        return self.get_public_key().get_id()

    def get_public_key(self):
        """ Get the PublicKey correctponding to this private key.
        """
        public_key = self._key.public_key()
        return PublicKey(public_key)

    def sign(self, data):
        """ Sign the given (bytes) data. Returns the (string) signature.
        """
        assert isinstance(data, bytes)
        sig = self._key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return base64.encodebytes(sig).decode()

    def decrypt(self, encrypted_data):
        """ Decrypt (bytes) data that was encrypted with the public key.
        """
        return self._key.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )


class PublicKey:
    def __init__(self, _key):
        assert isinstance(_key, rsa.RSAPublicKey)
        self._key = _key

    @classmethod
    def from_str(cls, s):
        """ Load a public RSA key from a string (as produced by to_str()).
        """
        assert isinstance(s, str)
        assert s.startswith("rsa-pub-")
        # Supporting ssh keys would be nice, but their key type is not always supported
        b = base64.urlsafe_b64decode(s[8:].encode())
        public_key = serialization.load_der_public_key(b, backend=default_backend())
        return PublicKey(public_key)

    def to_str(self):
        """ Serialize this public RSA key to a (url-safe) string.
        """
        x = self._key.public_bytes(
            encoding=serialization.Encoding.DER,  # binary
            format=serialization.PublicFormat.PKCS1,  # raw key
        )
        return "rsa-pub-" + base64.urlsafe_b64encode(x).decode()

    def get_id(self):
        """ Get a short string that identifies this key. The corresponding
        private key has the same id.
        """
        return self.to_str().strip()[-10:]

    def verify_data(self, signature, data):
        """ Verify that the given signature was the result of signing the
        given data with the corresponding private key. Returns a bool.
        """
        # note: we don't call this verify to avoid confusion with self._key.verify
        # which raises an error upon fail instead of returning a bool.
        assert isinstance(signature, str)
        assert isinstance(data, bytes)
        sig = base64.decodebytes(signature.encode())
        try:
            self._key.verify(
                sig,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        except InvalidSignature:
            return False
        else:
            return True

    def encrypt(self, data):
        """ Encrypt the given (bytes) data, which can subsequently only be
        decrypted with the corresponding private key.
        """
        assert isinstance(data, bytes)
        return self._key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

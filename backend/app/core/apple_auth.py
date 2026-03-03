import jwt as pyjwt
from jwt import PyJWKClient
from typing import Dict, Any

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"

# Cache for Apple's public keys
_jwks_client = None


def get_jwks_client() -> PyJWKClient:
    """Get or create PyJWKClient for Apple's public keys."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(APPLE_JWKS_URL)
    return _jwks_client


async def verify_apple_token(identity_token: str, client_id: str) -> Dict[str, Any]:
    """
    Verify Apple identity token signature and claims.

    Args:
        identity_token: The JWT from Apple
        client_id: Your app's Apple client ID (audience)

    Returns:
        Decoded payload if valid

    Raises:
        ValueError: If token is invalid
    """
    try:
        # Get signing key from Apple's JWKS
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(identity_token)

        # Verify signature and decode
        payload = pyjwt.decode(
            identity_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=APPLE_ISSUER,
            audience=client_id,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iss": True,
                "verify_aud": True,
            }
        )

        # Verify sub exists
        if not payload.get("sub"):
            raise ValueError("Missing sub claim")

        return payload

    except pyjwt.PyJWTError as e:
        raise ValueError(f"Invalid Apple token: {str(e)}")
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")

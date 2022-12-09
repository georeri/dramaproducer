import sys
import json
import logging
import time
import urllib.request
from typing import Dict, List
from dataclasses import dataclass
from jose import jwk, jwt
from jose.utils import base64url_decode
import constants as CONST

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


@dataclass
class JWK:
    """A JSON Web Key (JWK) model that represents a cryptographic key.

    The JWK specification:
    https://datatracker.ietf.org/doc/html/rfc7517
    """

    alg: str
    e: str
    kid: str
    kty: str
    n: str
    use: str

    def asdict(self):
        return self.__dict__


class Token:
    raw_token: str
    header: Dict
    claims: Dict
    is_valid_jwt: bool
    is_verified: bool

    def __init__(self, **kwargs):
        self.raw_token = kwargs.get("raw_token")
        self.header = kwargs.get("header", {})
        self.claims = kwargs.get("claims", {})
        self.is_valid_jwt = kwargs.get("is_valid_jwt", False)
        self.is_verified = kwargs.get("is_verified", False)

    def asdict(self):
        return self.__dict__


class CognitoAuthenticator:

    pool_region: str = CONST.AWS_DEFAULT_REGION
    pool_id: str = CONST.COGNITO_USER_POOL_ID
    client_id: str = CONST.COGNITO_USER_POOL_CLIENT_ID
    token: Token = Token()

    def __init__(self, token: str) -> None:
        self.issuer = (
            f"https://cognito-idp.{self.pool_region}.amazonaws.com/{self.pool_id}"
        )
        self.jwks = self.__get_jwks()
        if token:
            self.token = Token(raw_token=token)
            self.verify_token(token)

    def __get_jwks(self) -> List[JWK]:
        """Returns a list of JSON Web Keys (JWKs) from the issuer. A JWK is a
        public key used to verify a JSON Web Token (JWT).

        Returns:
            List of keys
        Raises:
            Exception when JWKS endpoint does not contain any keys
        """
        url = f"{self.issuer}/.well-known/jwks.json"
        logging.info(url)
        file = urllib.request.urlopen(url)
        res = json.loads(file.read().decode("utf-8"))
        logging.info(res)
        if not res.get("keys"):
            raise Exception("The JWKS endpoint does not contain any keys")
        jwks = [JWK(**key) for key in res["keys"]]
        return jwks

    def verify_token(
        self,
        token: str,
    ) -> None:
        """Verify a JSON Web Token (JWT).

        For more details refer to:
        https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html
        """

        try:
            self.token = Token(
                raw_token=token,
                is_valid_jwt=self._is_jwt(token),
                header=self._get_verified_header(token),
                claims=self._get_verified_claims(token),
                is_verified=True,
            )
        except CognitoError:
            return False
        return True

    def is_group_member(self, group: str):
        if (
            "cognito:groups" not in self.token.claims
            or self.token.claims["cognito:groups"] is None
        ):
            return False

        return group in self.token.claims["cognito:groups"]

    def _is_jwt(self, token: str) -> bool:
        """Validate a JSON Web Token (JWT).
        A JSON Web Token (JWT) includes three sections: Header, Payload and
        Signature. They are base64url encoded and are separated by dot (.)
        characters. If JWT token does not conform to this structure, it is
        considered invalid.

        Args:
            token: The token to validate
        Returns:
            True if valid
        Raises:
            CognitoError when invalid token
        """

        try:
            jwt.get_unverified_header(token)
            jwt.get_unverified_claims(token)
        except jwt.JWTError:
            logging.info("Invalid JWT")
            raise InvalidJWTError
        return True

    def _get_verified_header(self, token: str) -> Dict:
        """Verifies the signature of a a JSON Web Token (JWT) and returns its
        decoded header.

        Args:
            token: The token to decode header from
        Returns:
            A dict representation of the token header
        Raises:
            CognitoError when unable to verify signature
        """

        # extract key ID (kid) from token
        self.headers = jwt.get_unverified_header(token)
        kid = self.headers["kid"]

        # find JSON Web Key (JWK) that matches kid from token
        key = None
        for k in self.jwks:
            if k.kid == kid:
                # construct a key object from found key data
                key = jwk.construct(k.asdict())
                break
        if not key:
            logging.info(f"Unable to find a signing key that matches '{kid}'")
            raise InvalidKidError

        # get message and signature (base64 encoded)
        message, encoded_signature = str(token).rsplit(".", 1)
        signature = base64url_decode(encoded_signature.encode("utf-8"))

        if not key.verify(message.encode("utf8"), signature):
            logging.info("Signature verification failed")
            raise SignatureError

        # signature successfully verified
        return self.headers

    def _get_verified_claims(self, token: str) -> Dict:
        """Verifies the claims of a JSON Web Token (JWT) and returns its claims.

        Args:
            token: The token to decode claims from
        Returns:
            A dict representation of the token claims
        Raises:
            CognitoError when unable to verify claims
        """

        claims = jwt.get_unverified_claims(token)

        # verify expiration time
        if claims["exp"] < time.time():
            logging.info("Expired token")
            raise TokenExpiredError

        # verify issuer
        if claims["iss"] != self.issuer:
            logging.info("Invalid issuer claim")
            raise InvalidIssuerError

        # verify audience
        # note: claims["client_id"] for access token, claims["aud"] otherwise
        if claims["client_id"] != self.client_id:
            logging.info("Invalid audience claim")
            raise InvalidAudienceError

        # verify token use
        if claims["token_use"] != "access":
            logging.info("Invalid token use claim")
            raise InvalidTokenUseError

        # claims successfully verified
        return claims


class CognitoError(Exception):
    pass


class CognitoAuthError(Exception):
    pass


class InvalidJWTError(CognitoError):
    pass


class InvalidKidError(CognitoError):
    pass


class SignatureError(CognitoError):
    pass


class TokenExpiredError(CognitoError):
    pass


class InvalidIssuerError(CognitoError):
    pass


class InvalidAudienceError(CognitoError):
    pass


class InvalidTokenUseError(CognitoError):
    pass

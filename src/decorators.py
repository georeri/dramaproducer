from functools import wraps
from flask import request, abort
from auth import CognitoAuthenticator


def authentication_required(view):
    @wraps(view)
    def decorated(*args, **kwargs):

        access_token = request.cookies.get("access_token_cookie", "")
        authenticator = CognitoAuthenticator(access_token)
        if not authenticator.token.is_verified:
            abort(401)
        view.__globals__["authenticator"] = authenticator
        return view(*args, **kwargs)

    return decorated

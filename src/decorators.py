from functools import wraps
from flask import request, abort, make_response
from auth import CognitoAuthenticator
from typing import List


def authentication_required(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        access_token = request.cookies.get("access_token_cookie", "")
        authenticator = CognitoAuthenticator(access_token)
        if not authenticator.token.is_verified:
            abort(401)
        return view(*args, **kwargs)

    return decorated


def group_membership_required(allowed_groups: List[str]):
    def inner_decorator(view):
        def wrapped(*args, **kwargs):
            access_token = request.cookies.get("access_token_cookie", "")
            authenticator = CognitoAuthenticator(access_token)
            if not authenticator.token.is_verified or not any(
                [authenticator.is_group_member(i) for i in allowed_groups]
            ):
                abort(401)
            resp = make_response(view(*args, **kwargs))
            resp.set_cookie("cognito_username", authenticator.token.claims["username"])
            resp.set_cookie(
                "cognito_groups",
                ",".join(authenticator.token.claims.get("cognito:groups", [])),
            )
            return resp

        return wrapped

    return inner_decorator


def admin_required(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        access_token = request.cookies.get("access_token_cookie", "")
        authenticator = CognitoAuthenticator(access_token)
        if all(
            [
                authenticator.token.is_verified,
                authenticator.is_group_member("admins"),
            ]
        ):
            resp = make_response(view(*args, **kwargs))
            resp.set_cookie("cognito_username", authenticator.token.claims["username"])
            resp.set_cookie(
                "cognito_groups",
                ",".join(authenticator.token.claims.get("cognito:groups", [])),
            )
            return resp
        abort(401)

    return decorated

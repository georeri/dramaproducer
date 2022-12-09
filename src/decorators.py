from functools import wraps
from flask import request, abort
from auth import CognitoAuthenticator
from typing import List


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


def group_membership_required(allowed_groups: List[str]):
    def inner_decorator(view):
        def wrapped(*args, **kwargs):
            access_token = request.cookies.get("access_token_cookie", "")
            authenticator = CognitoAuthenticator(access_token)
            if not authenticator.token.is_verified or not any(
                [authenticator.is_group_member(i) for i in allowed_groups]
            ):
                abort(401)
            view.__globals__["authenticator"] = authenticator
            return view(*args, **kwargs)

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
            view.__globals__["authenticator"] = authenticator
            return view(*args, **kwargs)
        abort(401)

    return decorated

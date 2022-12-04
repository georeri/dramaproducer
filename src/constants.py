import os

#########################
# Application Specific
#########################

REGISTRATION_STATES = {
    "registered": ["cancelled", "attended"],
    "attended": ["cancelled"],
    "cancelled": [],
}
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")

#########################
# AWS
#########################

AWS_DEFAULT_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_COGNITO_DOMAIN = os.environ["AWS_COGNITO_DOMAIN"]
AWS_COGNITO_USER_POOL_ID = os.environ["AWS_COGNITO_USER_POOL_ID"]
AWS_COGNITO_USER_POOL_CLIENT_ID = os.environ["AWS_COGNITO_USER_POOL_CLIENT_ID"]
AWS_COGNITO_USER_POOL_CLIENT_SECRET = os.environ["AWS_COGNITO_USER_POOL_CLIENT_SECRET"]
AWS_COGNITO_REDIRECT_URL = SITE_URL + "/aws_cognito_redirect"

#########################
# Security
#########################

SECRET_KEY = os.environ.get("SECRET_KEY", "ARBITRARY")
JWT_TOKEN_LOCATION = ["cookies"]
JWT_COOKIE_SECURE = True
JWT_COOKIE_CSRF_PROTECT = (
    False  # We're ok to set this off, as Cognito OAuth state provides protection
)
JWT_ALGORITHM = "RS256"
JWT_IDENTITY_CLAIM = "sub"
JWT_PRIVATE_KEY = os.environ["JWT_PRIVATE_KEY"]
JWT_SECRET_KEY = (
    SECRET_KEY  # We're using Cognito to generate keys, so this is never used
)

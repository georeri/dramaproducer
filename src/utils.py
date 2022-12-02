import json
import requests
from constants import AWS_DEFAULT_REGION, AWS_COGNITO_USER_POOL_ID


def get_cognito_public_keys():
    url = f"https://cognito-idp.{AWS_DEFAULT_REGION}.amazonaws.com/{AWS_COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    resp = requests.get(url)
    return json.dumps(json.loads(resp.text)["keys"][1])

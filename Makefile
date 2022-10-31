bootstrap:
	npm install -g serverless
	sls plugin install -n serverless-wsgi
	sls plugin install -n serverless-python-requirements

reqs:
	pipenv requirements > requirements.txt

deploy:
	serverless deploy

package:
	- rm -rf ./dist
	mkdir -p ./dist
	serverless package --package ./dist

serve:
	IS_OFFLINE=1 sls wsgi serve

run:
	FLASK_APP=src/app.py pipenv run flask run
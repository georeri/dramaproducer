bootstrap:
	npm install -g serverless
	sls plugin install -n serverless-wsgi
	sls plugin install -n serverless-python-requirements

reqs:
	pipenv requirements > requirements.txt

clean:
	- rm -rf ./dist
	- pipenv run serverless requirements clean

prep: clean reqs

deploy: prep
	pipenv run serverless deploy

un-deploy:
	pipenv run serverless remove

package: prep
	mkdir -p ./dist
	pipenv run serverless package --package ./dist

serve:
	IS_OFFLINE=1 sls wsgi serve

run:
	FLASK_APP=src/app.py pipenv run flask run

shell:
	pipenv shell


# Level Up Registration App
Front end application - Documentation is a work in progress. Please, add more!

## Setup

- Install docker desktop
- Install VSCode
- Install python 3.8 or greater
- Install node 
- Run ' make bootstrap '

## Contents

### .devcontainer
Build container that spins up an instance of VSCode containerized to allow us to develop and build in an environment that matches the Lambda runtime environment, since we are using cryptography libraries that require compilation for the target kernel. Use VSCode's "Re-open in Container" to build this app when you're ready to deploy.

### docker-compose.yml

Allows you to run dynamodb locally for testing, as needed.
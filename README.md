# Usage

## KeyError problem

0. install poetry
1. `poetry install`
2. `poetry run httpx-h2-testing server`
3. In another shell: `poetry run httpx-h2-testing client 1000`
4. You might need to ctrl-c the client to see the exception.

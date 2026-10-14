from fastapi import FastAPI

# TODO 2 (name): this app is called `server`. Either rename it to `app`, or keep the name and
#   write it in the entrypoint in pyproject.toml. The two files must agree.
server = FastAPI()


# TODO 3 (route): add `GET /` here. It returns {"message": "Hello World"}.

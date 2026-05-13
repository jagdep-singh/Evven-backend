from fastapi import FastAPI  # type: ignore

from routes.auth import router as auth_router

app = FastAPI()

app.include_router(auth_router)


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"message": "EvenUp"}

from fastapi import FastAPI

from routes.auth import router as auth_router
from routes.groups import router as groups_router
from routes.users import router as users_router

app = FastAPI(
    title="EvenUp API",
    description="API for Group and Personal Expense Management",
    version="0.0.1",
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(groups_router)


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def EvenUp():
    return {"message": "EvenUp"}

from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routes.auth import router as auth_router
from routes.group_expenses import router as groups_expense_router
from routes.group_member import router as group_member_router
from routes.groups import router as groups_router
from routes.users import router as users_router

app = FastAPI(
    title="EvenUp API",
    description="API for Group and Personal Expense Management",
    version="0.0.1",
    docs_url=None,
    redoc_url=None,
)
FAVICON_URL = "/static/EvenUp-white.svg"

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="EvenUp Docs",
        swagger_favicon_url=FAVICON_URL,
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title="EvenUp ReDoc",
        redoc_favicon_url=FAVICON_URL,
    )


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(groups_router)
app.include_router(group_member_router)
app.include_router(groups_expense_router)


@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse("templates/index.html")

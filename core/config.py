import os

from dotenv import load_dotenv  # type: ignore

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") or "30")
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS") or "30")

RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES") or "15")

# Resend email
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM = os.getenv("RESEND_FROM")

# celery
# CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
# CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")

# backed frontend url
BACKEND_URL = os.getenv("BACKEND_URL")

# GOOGLE client id
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


# Rate limiting
FORGOT_PASSWORD_BUCKET_CAPACITY = int(os.getenv("FORGOT_PASSWORD_BUCKET_CAPACITY", "5"))
FORGOT_PASSWORD_REFILL_RATE = float(os.getenv("FORGOT_PASSWORD_REFILL_RATE", "1"))

RESET_PASSWORD_PAGE_BUCKET_CAPACITY = int(
    os.getenv("RESET_PASSWORD_PAGE_BUCKET_CAPACITY", "20")
)
RESET_PASSWORD_PAGE_REFILL_RATE = float(
    os.getenv("RESET_PASSWORD_PAGE_REFILL_RATE", "2")
)

RESET_PASSWORD_BUCKET_CAPACITY = int(os.getenv("RESET_PASSWORD_BUCKET_CAPACITY", "5"))
RESET_PASSWORD_REFILL_RATE = float(os.getenv("RESET_PASSWORD_REFILL_RATE", "1"))

GOOGLE_AUTH_BUCKET_CAPACITY = int(os.getenv("GOOGLE_AUTH_BUCKET_CAPACITY", "10"))
GOOGLE_AUTH_REFILL_RATE = float(os.getenv("GOOGLE_AUTH_REFILL_RATE", "2"))

# ops logging
OPS_USERNAME = os.getenv("OPS_USERNAME")
OPS_PASSWORD = os.getenv("OPS_PASSWORD")
DEPLOY_WEBHOOK_SECRET = os.getenv("DEPLOY_WEBHOOK_SECRET")
OPS_SESSION_TTL_DAYS = int(os.getenv("OPS_SESSION_TTL_DAYS", "7"))
ERROR_LOG_RETENTION_DAYS = int(os.getenv("ERROR_LOG_RETENTION_DAYS", "90"))
DEPLOY_LOG_RETENTION_DAYS = int(os.getenv("DEPLOY_LOG_RETENTION_DAYS", "365"))

ERRORS_INGEST_BUCKET_CAPACITY = int(os.getenv("ERRORS_INGEST_BUCKET_CAPACITY", "30"))
ERRORS_INGEST_REFILL_RATE = float(os.getenv("ERRORS_INGEST_REFILL_RATE", "2"))

OPS_LOGIN_BUCKET_CAPACITY = int(os.getenv("OPS_LOGIN_BUCKET_CAPACITY", "5"))
OPS_LOGIN_REFILL_RATE = float(os.getenv("OPS_LOGIN_REFILL_RATE", "1"))

for _var in ("OPS_USERNAME", "OPS_PASSWORD", "DEPLOY_WEBHOOK_SECRET"):
    if not os.getenv(_var):
        raise RuntimeError(f"Missing required env var: {_var}")

if not SECRET_KEY:
    raise RuntimeError("Missing required env var: SECRET_KEY")
if not ALGORITHM:
    raise RuntimeError("Missing required env var: ALGORITHM")
# end ops logging

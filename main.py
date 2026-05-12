from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Data(BaseModel):
    data: str

@app.get("/")
def read_root():
    return {"message": "EvenUp"}

@app.post("/")
def PingPong(payload: Data):
    if payload.data == "ping":
        return {"ping": "pong"}
    else:
        return {"message": f"should have sent ping instead of '{payload.data}' you dumb ass"}
    
    
@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}
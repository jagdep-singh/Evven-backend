from database import AsyncSessionLocal, engine

from fastapi import Depends, HTTPException, status
from uuid import UUID
from services.auth_service import decode_token
from 

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
        
async def get_current_user(token: str = Depends(decode_token)):
    #will complete this 
    return None

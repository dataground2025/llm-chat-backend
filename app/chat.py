from fastapi import APIRouter, Depends, HTTPException, status, Header, Body
from sqlalchemy.orm import Session
from . import schemas, models, database, utils
from .agent_simple import SimpleDataGroundAgent
import openai
import os
from typing import List, Optional, Dict
from datetime import datetime
from .schemas import ChatOut, MessageOut
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# Initialize the DataGround agent lazily
_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = SimpleDataGroundAgent()
    return _agent

# Dependency to get DB session

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(Authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    if not Authorization or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = Authorization.split(" ")[1]
    payload = utils.decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.get('/chats', response_model=List[schemas.ChatOut])
def list_chats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chats = db.query(models.Chat).filter(models.Chat.user_id == current_user.id).all()
    return chats

@router.post('/chats', response_model=schemas.ChatOut)
def create_chat(title: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = models.Chat(user_id=current_user.id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

@router.get('/chats/{chat_id}/messages', response_model=List[schemas.MessageOut])
def get_messages(chat_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat.messages

@router.post('/chats/{chat_id}/messages', response_model=schemas.MessageOut)
def send_message(chat_id: int, content: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Store user message
    user_msg = models.Message(chat_id=chat_id, sender="user", content=content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    
    # Use DataGround agent for AI response
    try:
        agent = get_agent()
        ai_content = agent.process_message(content)
    except Exception as e:
        ai_content = f"[AI Error: {str(e)}]"
    
    # Store AI message
    ai_msg = models.Message(chat_id=chat_id, sender="ai", content=ai_content)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    return ai_msg

@router.patch('/chats/{chat_id}/title', response_model=schemas.ChatOut)
def update_chat_title(chat_id: int, title: str = Body(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    chat.title = title
    db.commit()
    db.refresh(chat)
    return chat

@router.post('/chats/first', response_model=dict)
def create_chat_with_first_message(
    title: str = Body(...),
    content: str = Body(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    chat = models.Chat(user_id=current_user.id, title=title, created_at=datetime.utcnow())
    db.add(chat)
    db.commit()
    db.refresh(chat)
    user_msg = models.Message(chat_id=chat.id, sender="user", content=content, created_at=chat.created_at)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)
    return {
        "chat": ChatOut.model_validate(chat),
        "message": MessageOut.model_validate(user_msg)
    }

@router.post('/chats/{chat_id}/ai_response', response_model=schemas.MessageOut)
def generate_ai_response(chat_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    # Get the last user message to process
    last_user_message = None
    for message in reversed(chat.messages):
        if message.sender == "user":
            last_user_message = message
            break
    
    if not last_user_message:
        ai_content = "I don't see any user messages to respond to."
    else:
        # Use DataGround agent for AI response
        try:
            agent = get_agent()
            ai_content = agent.process_message(last_user_message.content)
        except Exception as e:
            ai_content = f"[AI Error: {str(e)}]"
    
    # Store AI message
    ai_msg = models.Message(chat_id=chat_id, sender="ai", content=ai_content)
    db.add(ai_msg)
    db.commit()
    db.refresh(ai_msg)
    return ai_msg

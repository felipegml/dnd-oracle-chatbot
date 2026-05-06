from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
from pathlib import Path

from rag import retrieve
from llm import ask

app = FastAPI(title="D&D 5e Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory chat history (resets on server restart)
chat_history: list[dict] = []


class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    reply: str
    sources: list[str]
    timestamp: str


@app.get("/")
def root():
    return {"status": "ok", "message": "D&D 5e Chatbot API with RAG + Groq"}


@app.post("/chat", response_model=MessageResponse)
def chat(req: MessageRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    user_msg = req.message.strip()
    timestamp = datetime.now().isoformat()

    # 1. Retrieve relevant chunks from ChromaDB
    chunks = retrieve(user_msg, n_results=4)

    # 2. Ask Groq LLM with the retrieved context
    reply = ask(user_msg, chunks)

    # 3. Store in history
    chat_history.append({"role": "user",  "text": user_msg, "timestamp": timestamp})
    chat_history.append({"role": "bot",   "text": reply,    "timestamp": timestamp})

    return MessageResponse(reply=reply, sources=chunks, timestamp=timestamp)


@app.get("/history")
def get_history():
    return {"history": chat_history}


@app.delete("/history")
def clear_history():
    chat_history.clear()
    return {"status": "cleared"}


@app.get("/dialogs")
def get_dialogs():
    dialogs_path = Path(__file__).parent / "dialogs.json"
    with open(dialogs_path, "r", encoding="utf-8") as f:
        return json.load(f)
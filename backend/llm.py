import os
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Try loading .env from multiple possible locations
for _candidate in [
    Path(__file__).parent / ".env",        # next to llm.py
    Path.cwd() / ".env",                   # current working directory
    Path.cwd() / "backend" / ".env",       # if launched from project root
]:
    if _candidate.exists():
        load_dotenv(dotenv_path=_candidate, override=True)
        print(f"[LLM] Loaded .env from: {_candidate}")
        break
else:
    print(f"[LLM] WARNING: No .env file found. Falling back to system environment.")

_client = None

SYSTEM_PROMPT = """You are a knowledgeable D&D 5e assistant specialising in SRD classes.
Answer questions clearly and accurately using ONLY the context provided below.
If the context does not contain enough information to answer, say so honestly.
Keep answers concise but complete. Use markdown bold (**text**) for class names,
dice, and key terms. Do not invent rules or features not present in the context."""


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not found in environment or .env file.\n"
                "Set it in your terminal before starting uvicorn:\n"
                "  Windows CMD:        set GROQ_API_KEY=gsk_xxx\n"
                "  Windows PowerShell: $env:GROQ_API_KEY='gsk_xxx'\n"
                "  Mac/Linux:          export GROQ_API_KEY=gsk_xxx"
            )
        print(f"[LLM] Groq client initialised (key: {api_key[:8]}...)")
        _client = Groq(api_key=api_key)
    return _client


def ask(user_message: str, context_chunks: list[str]) -> str:
    """Send user message + RAG context to Groq and return the reply."""
    context = "\n\n".join(f"- {chunk}" for chunk in context_chunks)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Context from the D&D 5e SRD knowledge base:\n{context}\n\n"
                f"Question: {user_message}"
            ),
        },
    ]

    client = _get_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=512,
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()
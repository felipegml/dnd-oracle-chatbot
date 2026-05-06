# Simple Chatbot

## Folder Structure

```
chatbot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── bot.py               # Bot logic
│   ├── dialogs.json         # Dialog database
│   └── requirements.txt
└── frontend/
    ├── public/
    │   └── index.html
    ├── src/
    │   ├── App.jsx
    │   ├── App.css
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

## Run

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

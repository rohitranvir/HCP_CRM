# HCP CRM — Important File Locations

---

## 🗂️ Root Level

| File | What it does |
|------|-------------|
| [start.bat](file:///d:/Project/hcp_crm/start.bat) | **One-click launcher** — starts both backend & frontend together |
| [README.md](file:///d:/Project/hcp_crm/README.md) | Project overview and setup instructions |

---

## 🐍 Backend (Django) — `backend/`

| File | What it does |
|------|-------------|
| [manage.py](file:///d:/Project/hcp_crm/backend/manage.py) | **Django entry point** — used to run the server (`python manage.py runserver`) |
| [requirements.txt](file:///d:/Project/hcp_crm/backend/requirements.txt) | List of all Python packages needed |

### ⚙️ Project Config — `backend/hcp_crm/`

| File | What it does |
|------|-------------|
| [settings.py](file:///d:/Project/hcp_crm/backend/hcp_crm/settings.py) | **Main config** — database, API keys, installed apps, CORS settings |
| [urls.py](file:///d:/Project/hcp_crm/backend/hcp_crm/urls.py) | **Root URL router** — connects all API endpoints |

### 🔁 Interactions App — `backend/interactions/`

| File | What it does |
|------|-------------|
| [models.py](file:///d:/Project/hcp_crm/backend/interactions/models.py) | **Database tables** — defines HCP, Interaction, and related data models |
| [views.py](file:///d:/Project/hcp_crm/backend/interactions/views.py) | **API logic** — handles all requests (create, list, update, delete) |
| [serializers.py](file:///d:/Project/hcp_crm/backend/interactions/serializers.py) | Converts database data to/from JSON for the API |
| [api_urls.py](file:///d:/Project/hcp_crm/backend/interactions/api_urls.py) | All API route definitions for interactions |
| [agent.py](file:///d:/Project/hcp_crm/backend/interactions/agent.py) | **AI Agent** — the main AI brain that processes user queries |
| [agent_router.py](file:///d:/Project/hcp_crm/backend/interactions/agent_router.py) | Decides which AI tool/action to call based on the query |
| [admin.py](file:///d:/Project/hcp_crm/backend/interactions/admin.py) | Registers models in Django admin panel |

### 🤖 AI Module — `backend/interactions/ai/`

| File | What it does |
|------|-------------|
| [pipeline.py](file:///d:/Project/hcp_crm/backend/interactions/ai/pipeline.py) | **AI processing pipeline** — chains LLM steps together (summarize, sentiment, etc.) |

---

## ⚛️ Frontend (React + Vite) — `frontend/`

| File | What it does |
|------|-------------|
| [index.html](file:///d:/Project/hcp_crm/frontend/index.html) | **HTML entry point** — the single page the browser loads |
| [package.json](file:///d:/Project/hcp_crm/frontend/package.json) | Lists all JS packages and npm scripts |
| [vite.config.js](file:///d:/Project/hcp_crm/frontend/vite.config.js) | Vite dev server config (port, proxy, etc.) |

### 🧩 Source Code — `frontend/src/`

| File | What it does |
|------|-------------|
| [main.jsx](file:///d:/Project/hcp_crm/frontend/src/main.jsx) | **React entry point** — mounts the app into the HTML page |
| [App.jsx](file:///d:/Project/hcp_crm/frontend/src/App.jsx) | **Root component** — top-level layout and routing |
| [index.css](file:///d:/Project/hcp_crm/frontend/src/index.css) | Global styles applied across the whole app |

### 🎨 Components — `frontend/src/components/`

| File | What it does |
|------|-------------|
| [AIAssistant.jsx](file:///d:/Project/hcp_crm/frontend/src/components/AIAssistant.jsx) | **AI Chat UI** — the chat interface where users talk to the AI |
| [InteractionForm.jsx](file:///d:/Project/hcp_crm/frontend/src/components/InteractionForm.jsx) | Form to log a new HCP interaction |
| [SentimentSelector.jsx](file:///d:/Project/hcp_crm/frontend/src/components/SentimentSelector.jsx) | UI widget to pick sentiment (positive/neutral/negative) |

### 🔌 API & State — `frontend/src/`

| File | What it does |
|------|-------------|
| [api/chatApi.js](file:///d:/Project/hcp_crm/frontend/src/api/chatApi.js) | Sends chat messages to the backend AI endpoint |
| [store/store.js](file:///d:/Project/hcp_crm/frontend/src/store/store.js) | **Redux store** — central state management setup |
| [store/slices/interactionSlice.js](file:///d:/Project/hcp_crm/frontend/src/store/slices/interactionSlice.js) | State + actions for interactions (fetch, create, etc.) |
| [store/slices/chatSlice.js](file:///d:/Project/hcp_crm/frontend/src/store/slices/chatSlice.js) | State + actions for the AI chat session |

---

## 🧭 Quick Summary (for video intro)

```
hcp_crm/
├── start.bat                        ← Run everything from here
├── backend/
│   ├── manage.py                    ← Start Django server
│   ├── hcp_crm/
│   │   ├── settings.py              ← Config & secrets
│   │   └── urls.py                  ← API routing root
│   └── interactions/
│       ├── models.py                ← Database structure
│       ├── views.py                 ← API logic
│       ├── agent.py                 ← AI brain
│       ├── agent_router.py          ← AI decision router
│       └── ai/pipeline.py           ← AI processing chain
└── frontend/
    ├── index.html                   ← Browser entry
    └── src/
        ├── main.jsx                 ← React starts here
        ├── App.jsx                  ← Main layout
        ├── components/
        │   ├── AIAssistant.jsx      ← Chat UI
        │   └── InteractionForm.jsx  ← Log interactions
        ├── api/chatApi.js           ← Talks to backend
        └── store/store.js           ← App state (Redux)
```

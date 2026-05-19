# HCP CRM — AI-First Healthcare CRM

An AI-First Customer Relationship Management module for managing Healthcare Professionals (HCPs) and Interactions, powered by a **LangGraph Agent** and **Django REST API**.

## 🖥️ Split-Screen UI
The application features a responsive split-screen interface:
- **Left Panel (60%)**: A highly structured, read-only Interaction Form displaying fields like "HCP Name", "Topics Discussed", "Sentiment", and "Follow-up Actions". These fields are bound to Redux and cannot be edited manually.
- **Right Panel (40%)**: An **AI Assistant** chat interface where reps log interaction details using natural language. The AI agent processes the input, uses the appropriate tool, and automatically updates the Left Panel in real-time.

## 🛠️ Tech Stack
| Component | Technology |
|---|---|
| **Backend API** | Django, Django REST Framework |
| **Database** | PostgreSQL |
| **AI Orchestration** | LangGraph, LangChain |
| **LLM Inference** | Groq (`gemma2-9b-it`) |
| **Frontend** | React, Vite |
| **State Management** | Redux Toolkit (`react-redux`) |

---

## ⚙️ Backend Setup Instructions

1. **Clone repo** (if applicable)
2. **Create virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   ```
3. **Activate venv:**
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Create `.env` file** in `backend/` with:
   ```env
   GROQ_API_KEY=your_groq_api_key
   DB_NAME=hcp_crm
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```
6. **Create PostgreSQL database manually:**
   ```sql
   CREATE DATABASE hcp_crm;
   ```
7. **Run migrations:**
   ```bash
   python manage.py makemigrations && python manage.py migrate
   ```
8. **Seed sample data:**
   ```bash
   python manage.py seed_data
   ```
9. **Start Django server:**
   ```bash
   python manage.py runserver
   ```

---

## 🎨 Frontend Setup Instructions

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```
2. **Install dependencies:**
   ```bash
   npm install
   ```
3. **Create `.env` file** in `frontend/`:
   ```env
   REACT_APP_API_URL=http://localhost:8000/api
   VITE_API_URL=http://localhost:8000/api
   ```
4. **Start React App:**
   ```bash
   npm run dev
   ```

---

## 🤖 LangGraph Agent Tools & Examples

The LangGraph Agent manages 5 primary tools. Input natural language via the AI chat to trigger them.

### Tool 1: Log Interaction
Creates a new interaction record and links it to an existing HCP.
- **Example Prompt:** *"Met Dr. Smith today, discussed Product X efficiency, sentiment positive, shared brochures"*

### Tool 2: Edit Interaction
Updates specific fields in a currently active interaction without overwriting the entire record.
- **Example Prompt:** *"Change the name to Dr. John and sentiment to negative"*

### Tool 3: Suggest Follow-up
Generates 3 contextual follow-up actions based on the interaction's topics and outcomes.
- **Example Prompt:** *"Suggest follow-up actions for this interaction"*

### Tool 4: Search HCP
Finds a specific HCP in the PostgreSQL database.
- **Example Prompt:** *"Search for Dr. Smith in the database"*

### Tool 5: Summarize History
Aggregates and summarizes all historical interactions for a specific HCP.
- **Example Prompt:** *"Summarize all past interactions with Dr. Smith"*

---

## 📡 API Endpoint Documentation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/` | Send natural language message to the AI agent |
| `GET` | `/api/interactions/` | List all interactions (paginated) |
| `GET` | `/api/interactions/<id>/` | Get single interaction detail |
| `GET` | `/api/hcp/` | List all active HCPs |
| `GET` | `/api/hcp/search/?name=<query>` | Search HCP by name (autocomplete) |
| `POST` | `/api/interactions/<id>/followup/` | Trigger AI to generate follow-up suggestions |

*(Note: Legacy endpoints from earlier phases are still available under `/api/v1/`)*

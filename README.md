# Real-Time and Event-Driven Agents Training Code

This repository contains the teaching code that matches the slide deck on **FastAPI, WebSockets, and event-driven agents**.

The code is intentionally designed for a training session:
- readable first
- easy to run locally
- simple enough for students to extend after class

---

## Repository structure

```text
realtime_agents_training_code/
├── 01_basic_rest_api/
│   └── app.py
├── 02_basic_websocket/
│   └── app.py
├── 03_event_driven_agent_demo/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── agent.py            # LLM-powered agent (LangChain + OpenAI)
│   │   ├── connection_manager.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── storage.py          # SQLite-backed persistence
│   ├── sample_events/          # Ready-to-use test payloads
│   │   ├── 01_billing_enterprise.json
│   │   ├── 02_incident_standard.json
│   │   ├── 03_access_issue.json
│   │   ├── 04_general_inquiry.json
│   │   ├── 05_critical_outage_enterprise.json
│   │   ├── 06_ticket_updated.json
│   │   ├── 07_unknown_event_type.json
│   │   └── 08_billing_payment_standard.json
│   ├── static/
│   │   └── dashboard.html      # Live dashboard with ticket submission
│   ├── .env.example
│   └── sample_event.json
├── .gitignore
├── requirements.txt
└── README.md
```

---

## What each example teaches

### 1) `01_basic_rest_api`
Use this first when teaching API fundamentals.

It demonstrates:
- what a REST API route looks like
- how request/response models work
- how to define `GET` and `POST` endpoints
- how FastAPI validates input automatically

### 2) `02_basic_websocket`
Use this second when introducing WebSockets.

It demonstrates:
- what a WebSocket connection looks like
- how a browser connects to the server
- how a server receives and sends messages
- how the communication stays open after the first message

### 3) `03_event_driven_agent_demo`
Use this as the main use case for the session.

It demonstrates:
- event ingestion through a REST API
- asynchronous background processing with a queue
- an LLM-powered support agent (LangChain + OpenAI) that classifies and routes tickets
- SQLite-backed persistence for events and ticket state
- event publication and state transitions
- a reactive dashboard: submit tickets from the UI and watch the agent process them in real time via WebSocket

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (fast Python package manager)
- An OpenAI API key (used by the event-driven agent demo)

Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Setup instructions

### 1. Create the virtual environment and install dependencies

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

On Windows (PowerShell):

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

### 2. Set your OpenAI API key

The event-driven agent demo uses OpenAI via LangChain.
Copy the example env file and add your key:

```bash
cd 03_event_driven_agent_demo
cp .env.example .env
```

Edit `.env` and replace the placeholder with your real key:

```text
OPENAI_API_KEY=sk-your-key-here
```

The app loads this automatically via `python-dotenv` at startup.

---

## How to run each example

### Example 1: Basic REST API

From the repository root:

```bash
cd 01_basic_rest_api
uvicorn app:app --reload --port 8000
```

Open the interactive docs:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:
- `GET /` -- verify the API is running
- `GET /tasks` -- list all tasks
- `POST /tasks` -- create a task
- `GET /tasks/{task_id}` -- get a single task

Sample `curl` request:

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Prepare slides for the FastAPI session", "completed": false}'
```

---

### Example 2: Basic WebSocket

From the repository root:

```bash
cd 02_basic_websocket
uvicorn app:app --reload --port 8001
```

Open in the browser:

```text
http://127.0.0.1:8001/
```

Type a message and send it. The server echoes it back over the same WebSocket connection.

Key teaching points:
- HTTP is one request, one response
- WebSockets keep an ongoing connection open
- the server can push data at any time without the client polling

---

### Example 3: Event-driven support agent demo

From the repository root:

```bash
cd 03_event_driven_agent_demo
uvicorn app.main:app --reload --port 8002
```

Open these URLs:

| URL | What it shows |
|-----|---------------|
| `http://127.0.0.1:8002/dashboard` | Live dashboard with ticket submission form |
| `http://127.0.0.1:8002/docs` | FastAPI Swagger UI |
| `http://127.0.0.1:8002/health` | Health check |

#### What happens in this demo

1. A user submits a ticket from the dashboard (or sends a `POST /events` request).
2. The API validates the request and places the event on an internal async queue.
3. A background worker picks up the event.
4. The LLM-powered agent (OpenAI via LangChain) classifies the ticket's category, priority, and assigned team.
5. The agent publishes intermediate and final events, each persisted in SQLite.
6. The dashboard receives every event over WebSocket and updates instantly.

#### Using the dashboard

Open `http://127.0.0.1:8002/dashboard`, type a support message, pick a customer tier, and click **Submit Ticket**. The event log and ticket state table update live as the agent processes the ticket.

#### Sending sample events via curl

From inside `03_event_driven_agent_demo/`:

```bash
curl -X POST http://127.0.0.1:8002/events \
  -H "Content-Type: application/json" \
  -d @sample_event.json
```

The `sample_events/` directory has eight events covering every agent path:

```bash
# Billing + enterprise (high priority, escalated)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/01_billing_enterprise.json

# Incident + standard (routed to incident-response)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/02_incident_standard.json

# Access issue (routed to identity-support)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/03_access_issue.json

# General inquiry (routed to general-support)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/04_general_inquiry.json

# Critical outage + enterprise (high priority, escalated)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/05_critical_outage_enterprise.json

# Follow-up update on existing ticket
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/06_ticket_updated.json

# Unknown event type (triggers unhandled path)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/07_unknown_event_type.json

# Billing/payment + standard (routed to billing-support)
curl -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @sample_events/08_billing_payment_standard.json
```

Or send all at once:

```bash
for f in sample_events/*.json; do
  echo "Sending $f ..."
  curl -s -X POST http://127.0.0.1:8002/events -H "Content-Type: application/json" -d @"$f"
  echo ""
  sleep 1
done
```

---

## API routes reference

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/events` | Accept a new event and queue it for processing |
| `GET` | `/events/log` | Return the full event log from SQLite |
| `GET` | `/tickets` | Return the latest state for all tickets |
| `GET` | `/tickets/{ticket_id}` | Return the state of a single ticket |
| `GET` | `/dashboard` | Serve the live dashboard |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | FastAPI Swagger UI |

---

## Suggested teaching flow

1. Run the basic REST example and show how `GET` and `POST` work
2. Run the basic WebSocket example and show how the browser keeps a live connection open
3. Run the event-driven agent demo
4. Open the dashboard, submit a ticket from the UI
5. Walk through how the event flows: REST intake -> async queue -> LLM agent -> SQLite persistence -> WebSocket broadcast
6. Send sample events via curl to show the API side
7. Query `/events/log` and `/tickets` to inspect persisted state

---

## Design choices

This code keeps things simple on purpose:

- **SQLite** for persistence without needing a database server
- **aiosqlite** for non-blocking database access
- **async queue** instead of Redis, Kafka, or RabbitMQ
- **LangChain + OpenAI** for ticket classification with structured output
- **python-dotenv** for API key management
- **plain HTML dashboard** instead of React or another frontend framework

These choices make the architecture easy to understand before introducing more moving parts.

---

## What students can extend later

Good follow-up exercises:

1. Add authentication to the API and WebSocket routes
2. Broadcast updates only to specific ticket rooms
3. Add retry logic and dead-letter handling for failed LLM calls
4. Replace the async queue with Redis or Kafka
5. Swap SQLite for PostgreSQL
6. Add a multi-step agent that can take actions (e.g. send an email, create a JIRA ticket)

---

## Production notes

This repository is built for teaching, not production.

For a real deployment, consider adding:
- proper authentication and authorization
- structured logging
- observability and tracing
- retry policies
- rate limiting
- external message brokers
- horizontal scaling for WebSocket connections

---

## Troubleshooting

### Port already in use

Run the app on a different port:

```bash
uvicorn app:app --reload --port 8010
```

Or for the main demo:

```bash
uvicorn app.main:app --reload --port 8012
```

### `ModuleNotFoundError`

Make sure:
- the virtual environment is activated (`source .venv/bin/activate`)
- dependencies are installed (`uv pip install -r requirements.txt`)
- you are running the command from the correct folder

### WebSocket page connects but no updates appear

Check that:
- the demo app is running on port `8002`
- the dashboard is opened from the same app instance
- you submitted a ticket from the dashboard or sent a `POST /events` request

### OpenAI errors

Make sure:
- `.env` exists inside `03_event_driven_agent_demo/` with a valid `OPENAI_API_KEY`
- your API key has credit/quota available
- you can reach the OpenAI API from your network

### Resetting the database

Delete the SQLite file and restart the app:

```bash
rm 03_event_driven_agent_demo/demo.db
```

---

## Quick recap

- `01_basic_rest_api` -- REST basics
- `02_basic_websocket` -- WebSocket basics
- `03_event_driven_agent_demo` -- combines REST, WebSocket, LLM agent, and SQLite into one practical use case

This mirrors the teaching progression in the training session.

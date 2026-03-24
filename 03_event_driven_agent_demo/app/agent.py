"""LLM-powered support operations agent using LangChain and OpenAI.

Uses a language model to classify and route support tickets instead of
hard-coded rules.  The agent receives events, sends them to the LLM for
analysis, and publishes new events as the workflow progresses.

Requires:
    OPENAI_API_KEY environment variable to be set.

Run:
    export OPENAI_API_KEY="sk-..."
    uvicorn app.main:app --reload --port 8002
"""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .models import Event

SYSTEM_PROMPT = """\
You are a support operations agent that triages incoming customer tickets.

Given the customer's message and their account tier, return a structured
classification with these fields:

- category: exactly one of  billing | incident | access | general
- priority: exactly one of  high | normal
- assigned_team: choose from  priority-operations, billing-support, \
incident-response, identity-support, general-support
- summary: a single concise sentence describing the ticket

Guidelines:
  * Enterprise-tier customers or messages mentioning urgency, outages,
    or production issues should be classified as high priority.
  * High-priority tickets are always assigned to priority-operations.
  * For normal priority, match the team to the category \
(billing -> billing-support, incident -> incident-response, \
access -> identity-support, general -> general-support).\
"""


class TicketClassification(BaseModel):
    """Structured LLM output for ticket triage."""

    category: str = Field(description="billing | incident | access | general")
    priority: str = Field(description="high | normal")
    assigned_team: str = Field(
        description="priority-operations, billing-support, "
        "incident-response, identity-support, or general-support",
    )
    summary: str = Field(description="One-sentence summary of the ticket")


class SupportOperationsAgent:
    """Handle support events using an LLM for classification and routing."""

    def __init__(self, publish_event_callback) -> None:
        self.publish_event = publish_event_callback

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "Customer tier: {customer_tier}\nMessage: {message}"),
        ])

        self.classifier = prompt | llm.with_structured_output(TicketClassification)

    async def handle_event(self, event: Event) -> None:
        """Route an incoming event to the correct handler."""

        if event.event_type == "ticket.created":
            await self._handle_ticket_created(event)
        elif event.event_type == "ticket.updated":
            await self._handle_ticket_updated(event)
        else:
            await self.publish_event(
                Event(
                    event_type="ticket.unhandled",
                    ticket_id=event.ticket_id,
                    correlation_id=event.correlation_id,
                    payload={"message": f"Unhandled event type: {event.event_type}"},
                )
            )

    async def _handle_ticket_created(self, event: Event) -> None:
        """Classify a new ticket with the LLM and route it."""

        message = str(event.payload.get("message", ""))
        customer_tier = str(event.payload.get("customer_tier", "standard"))

        await self.publish_event(
            Event(
                event_type="ticket.processing.started",
                ticket_id=event.ticket_id,
                correlation_id=event.correlation_id,
                payload={"stage": "classification", "message": "Ticket received. LLM analysis in progress."},
            )
        )

        result: TicketClassification = await self.classifier.ainvoke({
            "message": message,
            "customer_tier": customer_tier,
        })

        await self.publish_event(
            Event(
                event_type="ticket.classified",
                ticket_id=event.ticket_id,
                correlation_id=event.correlation_id,
                payload={
                    "category": result.category,
                    "priority": result.priority,
                    "assigned_team": result.assigned_team,
                    "summary": result.summary,
                },
            )
        )

        if result.priority == "high":
            await self.publish_event(
                Event(
                    event_type="ticket.escalated",
                    ticket_id=event.ticket_id,
                    correlation_id=event.correlation_id,
                    payload={
                        "reason": result.summary,
                        "assigned_team": result.assigned_team,
                    },
                )
            )
        else:
            await self.publish_event(
                Event(
                    event_type="ticket.routed",
                    ticket_id=event.ticket_id,
                    correlation_id=event.correlation_id,
                    payload={
                        "assigned_team": result.assigned_team,
                        "message": f"Ticket routed to {result.assigned_team}.",
                    },
                )
            )

    async def _handle_ticket_updated(self, event: Event) -> None:
        """Handle follow-up updates from another system or agent step."""

        await self.publish_event(
            Event(
                event_type="ticket.update.received",
                ticket_id=event.ticket_id,
                correlation_id=event.correlation_id,
                payload=event.payload,
            )
        )

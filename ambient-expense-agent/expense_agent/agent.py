import base64
import json
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.events.event import Event
from google.adk.events.request_input import RequestInput
from google.adk.workflow import Workflow, node
from pydantic import BaseModel

from .config import MODEL_NAME, THRESHOLD_AMOUNT

class ExpenseData(BaseModel):
    amount: float
    submitter: str
    category: str
    description: str
    date: str

class RiskAssessment(BaseModel):
    risk_factors: str
    alert_raised: bool
    summary: str

class ApprovalOutcome(BaseModel):
    expense: ExpenseData
    decision: str
    reason: str = ""

@node
def extract_expense(node_input: Any) -> Event:
    """Extracts expense data from Pub/Sub event or plain JSON."""
    data = node_input
    
    # Extract text from types.Content if necessary
    if hasattr(data, "parts") and len(data.parts) > 0 and hasattr(data.parts[0], "text"):
        data = data.parts[0].text

    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception:
            pass

    # Handle Pub/Sub wrapper
    if isinstance(data, dict) and "message" in data and "data" in data["message"]:
        raw_data = data["message"]["data"]
    elif isinstance(data, dict) and "data" in data:
        raw_data = data["data"]
    else:
        raw_data = data

    # Try base64 decode if it's a string
    if isinstance(raw_data, str):
        try:
            decoded = base64.b64decode(raw_data).decode('utf-8')
            expense_dict = json.loads(decoded)
        except Exception:
            try:
                expense_dict = json.loads(raw_data)
            except Exception:
                expense_dict = raw_data
    else:
        expense_dict = raw_data
            
    expense = ExpenseData(**expense_dict)
    
    # Routing logic based on threshold
    if expense.amount < THRESHOLD_AMOUNT:
        return Event(output=expense, route="auto_approve", state={"expense": expense.model_dump()})
    else:
        # Route to security checkpoint instead of directly to LLM
        return Event(output=expense, route="security_check", state={"expense": expense.model_dump()})

@node
def security_checkpoint(ctx: Context, node_input: ExpenseData) -> Event:
    """Scrubs PII and checks for prompt injection before LLM review."""
    description = node_input.description
    redacted_categories = set()
    
    # 1. Scrub PII (SSN and Credit Cards)
    # Basic regex for SSN: XXX-XX-XXXX
    if re.search(r'\b\d{3}-\d{2}-\d{4}\b', description):
        description = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED_SSN]', description)
        redacted_categories.add("SSN")
        
    # Basic regex for Credit Card: 13-16 digits
    if re.search(r'\b(?:\d[ -]*?){13,16}\b', description):
        description = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[REDACTED_CC]', description)
        redacted_categories.add("CREDIT_CARD")
        
    # 2. Defend against prompt injection
    injection_keywords = ["ignore previous", "auto-approve", "system prompt", "bypass", "disregard instructions"]
    is_injection = any(kw in description.lower() for kw in injection_keywords)
    
    # Update the expense with scrubbed description
    clean_expense = node_input.model_copy(update={"description": description})
    
    # Update the context state so downstream nodes see the scrubbed version
    ctx.state["expense"] = clean_expense.model_dump()
    ctx.state["redacted_categories"] = list(redacted_categories)
    
    if is_injection:
        # Synthesize a critical RiskAssessment and bypass the LLM completely
        security_risk = RiskAssessment(
            risk_factors="PROMPT INJECTION",
            alert_raised=True,
            summary="SECURITY EVENT: Description contains malicious instructions. LLM bypassed."
        )
        # Route directly to human approval
        return Event(output=security_risk, route="injection_detected")
        
    # Clean payload, proceed to LLM review
    return Event(output=clean_expense, route="clean")

@node
def auto_approve(ctx: Context, node_input: ExpenseData) -> Event:
    """Instantly approves expenses under threshold."""
    outcome = ApprovalOutcome(
        expense=node_input,
        decision="APPROVED",
        reason=f"Amount ${node_input.amount} is under ${THRESHOLD_AMOUNT} threshold."
    )
    return Event(output=outcome)

# LLM Node: Reviews expenses >= $100 for risk factors
llm_review = LlmAgent(
    name="llm_review",
    model=MODEL_NAME,
    instruction="""You are a risk analysis agent. Review the expense details and identify any risk factors or anomalies.
Be concise. Focus on the category, description, and amount.
Return a structured RiskAssessment highlighting if an alert should be raised.""",
    output_schema=RiskAssessment,
)

@node(rerun_on_resume=True)
async def human_approval(ctx: Context, node_input: RiskAssessment):
    """Pauses for human to approve or reject based on LLM review."""
    # If no human input is available yet, pause and request it
    if not ctx.resume_inputs:
        msg = f"Alert! Risk Assessment:\n{node_input.summary}\n\nDo you approve or reject this expense?"
        yield Event(output=node_input)
        yield RequestInput(interrupt_id="approval_decision", message=msg)
        return
        
    # Resume execution with the human's response
    decision = ctx.resume_inputs.get("approval_decision", "").upper()
    expense_dict = ctx.state.get("expense", {})
    expense = ExpenseData(**expense_dict)
    
    outcome = ApprovalOutcome(
        expense=expense,
        decision="APPROVED" if "APPROVE" in decision else "REJECTED",
        reason=f"Human decision after risk review: {decision}"
    )
    yield Event(output=outcome)

@node
def record_outcome(node_input: ApprovalOutcome) -> ApprovalOutcome:
    """Records the final outcome."""
    print(f"--- RECORDING OUTCOME ---")
    print(f"Submitter: {node_input.expense.submitter}")
    print(f"Amount: ${node_input.expense.amount}")
    print(f"Decision: {node_input.decision}")
    print(f"Reason: {node_input.reason}")
    print(f"-------------------------")
    return node_input

# Wire the nodes together into the Workflow graph
from google.adk.workflow import Edge

root_agent = Workflow(
    name="expense_approval_workflow",
    edges=[
        ('START', extract_expense),
        # Route 1: Under threshold
        Edge(from_node=extract_expense, to_node=auto_approve, route="auto_approve"),
        # Route 2: Over threshold -> goes to security check first
        Edge(from_node=extract_expense, to_node=security_checkpoint, route="security_check"),
        
        # Security routing
        Edge(from_node=security_checkpoint, to_node=llm_review, route="clean"),
        Edge(from_node=security_checkpoint, to_node=human_approval, route="injection_detected"),
        
        # Next steps
        (auto_approve, record_outcome),
        (llm_review, human_approval),
        (human_approval, record_outcome),
    ]
)

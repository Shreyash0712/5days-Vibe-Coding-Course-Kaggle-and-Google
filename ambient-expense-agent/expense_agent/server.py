import json
import logging
from fastapi import FastAPI, Request, Response
from google.adk.runners import InMemoryRunner
from app.app_utils.telemetry import setup_telemetry
from google.genai.types import Content, Part
from dotenv import load_dotenv

from . import app as adk_app

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup telemetry
setup_telemetry()

app = FastAPI()
runner = InMemoryRunner(app=adk_app)

@app.post("/")
async def handle_pubsub(request: Request):
    try:
        body = await request.json()
    except Exception:
        logger.error("Invalid JSON received")
        return Response(status_code=400, content=json.dumps({"status": "error", "message": "Invalid JSON payload"}), media_type="application/json")
    
    message = body.get("message", {})
    subscription = body.get("subscription", "unknown_sub")
    
    if "data" not in message:
        return Response(status_code=400, content=json.dumps({"status": "error", "message": "Missing 'data' in Pub/Sub message"}), media_type="application/json")
    
    # Normalize subscription path to short name
    short_sub = subscription.split("/")[-1]
    
    # Use short_sub and messageId as the session_id to keep records readable
    message_id = message.get("messageId", "unknown_id")
    session_id = f"{short_sub}_{message_id}"
    
    logger.info(f"Received pubsub message: {message_id} from subscription: {short_sub}")
    
    from google.adk.errors.already_exists_error import AlreadyExistsError
    try:
        session = await runner.session_service.create_session(
            app_name="expense_agent", 
            user_id="pubsub_system", 
            session_id=session_id
        )
    except AlreadyExistsError:
        session = await runner.session_service.get_session(
            app_name="expense_agent",
            user_id="pubsub_system",
            session_id=session_id
        )
    
    content = Content(role="user", parts=[Part.from_text(text=json.dumps(body))])
    
    try:
        ai_reply = None
        async for event in runner.run_async(
            user_id="pubsub_system",
            session_id=session.id,
            new_message=content,
        ):
            logger.info(f"Workflow event | Output: {event.output}")
            # The event.output will contain the LLM's risk assessment before pausing for human input
            if event.output is not None:
                ai_reply = event.output
                
        # Convert the ADK response object to a dictionary if possible
        if hasattr(ai_reply, "model_dump"):
            ai_reply = ai_reply.model_dump()
        elif hasattr(ai_reply, "__dict__"):
            ai_reply = vars(ai_reply)
            
        return Response(
            status_code=200, 
            content=json.dumps({
                "status": "success", 
                "message": "Expense workflow triggered successfully", 
                "session_id": session_id,
                "ai_reply": ai_reply
            }), 
            media_type="application/json"
        )
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        return Response(status_code=500, content=json.dumps({"status": "error", "message": str(e)}), media_type="application/json")

import asyncio
import json
import os
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from expense_agent import app

async def main():
    with open("tests/eval/datasets/basic-dataset.json", "r") as f:
        dataset = json.load(f)
        
    runner = InMemoryRunner(app=app)
    traces = []
    
    for case in dataset["eval_cases"]:
        case_id = case["eval_case_id"]
        prompt_text = case["prompt"]["parts"][0]["text"]
        
        session_id = f"eval_session_{case_id}"
        from google.adk.errors.already_exists_error import AlreadyExistsError
        try:
            session = await runner.session_service.create_session(
                app_name="expense_agent", 
                user_id="eval_user", 
                session_id=session_id
            )
        except AlreadyExistsError:
            session = await runner.session_service.get_session(
                app_name="expense_agent", 
                user_id="eval_user", 
                session_id=session_id
            )
            
        content = Content(role="user", parts=[Part.from_text(text=prompt_text)])
        
        events_list = [
            {"author": "user", "content": {"parts": [{"text": prompt_text}]}}
        ]
        
        last_output = None
        
        # Run workflow
        async for event in runner.run_async(user_id="eval_user", session_id=session.id, new_message=content):
            if getattr(event, "output", None) is not None:
                def to_dict(obj):
                    if hasattr(obj, "model_dump"): return obj.model_dump()
                    if isinstance(obj, dict): return obj
                    if hasattr(obj, "__dict__"): return vars(obj)
                    return str(obj)
                
                out_dict = to_dict(event.output)
                events_list.append({
                    "author": "expense_agent",
                    "content": {"parts": [{"text": json.dumps(out_dict)}]}
                })
                last_output = out_dict
                
            if getattr(event, "request_input", None) is not None:
                # Automate human input
                msg = event.request_input.message
                if "PROMPT INJECTION" in msg:
                    decision = "REJECT"
                else:
                    decision = "APPROVE"
                    
                events_list.append({
                    "author": "user",
                    "content": {"parts": [{"text": decision}]}
                })
                
                # Resume runner
                async for res_event in runner.resume_async(
                    user_id="eval_user",
                    session_id=session.id,
                    inputs={"approval_decision": decision}
                ):
                    if getattr(res_event, "output", None) is not None:
                        res_out = to_dict(res_event.output)
                        events_list.append({
                            "author": "expense_agent",
                            "content": {"parts": [{"text": json.dumps(res_out)}]}
                        })
                        last_output = res_out

        traces.append({
            "eval_case_id": case_id,
            "prompt": case["prompt"],
            "response": {"role": "model", "parts": [{"text": json.dumps(last_output)}]},
            "agent_data": {
                "turns": [{
                    "turn_index": 0,
                    "events": events_list
                }]
            }
        })
        
    os.makedirs("artifacts/traces", exist_ok=True)
    with open("artifacts/traces/generated_traces.json", "w") as f:
        json.dump({"eval_cases": traces}, f, indent=2)
        
    print("Traces successfully generated to artifacts/traces/generated_traces.json")

if __name__ == "__main__":
    asyncio.run(main())

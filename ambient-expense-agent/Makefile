.PHONY: install playground

install:
	uv sync

playground:
	uv run adk web expense_agent

run:
	uv run uvicorn expense_agent.server:app --port 8080 --host 0.0.0.0

generate-traces:
	uv run python tests/eval/generate_traces.py

grade:
	agents-cli eval grade --traces artifacts/traces/generated_traces.json --config tests/eval/eval_config.yaml

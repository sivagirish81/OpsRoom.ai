.PHONY: demo demo-stop chaos seed test

demo:
	@chmod +x scripts/demo.sh scripts/demo-stop.sh
	@./scripts/demo.sh

demo-stop:
	@chmod +x scripts/demo-stop.sh
	@./scripts/demo-stop.sh

chaos:
	@. .venv/bin/activate 2>/dev/null || true; \
	python -m samples.kafka_lag_incident.replay_incident --reset --chaos

seed:
	@. .venv/bin/activate 2>/dev/null || true; \
	python -m samples.kafka_lag_incident.seed_redis

test:
	@. .venv/bin/activate 2>/dev/null || true; \
	pytest tests/ -v

eval:
	@. .venv/bin/activate 2>/dev/null || true; \
	python -m evals.evaluate_incident_agent --seed

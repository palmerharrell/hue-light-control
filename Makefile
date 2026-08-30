.PHONY: dev dev-backend dev-frontend dev-demo dev-backend-demo pair-bridge

dev-backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@trap 'kill 0' EXIT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-frontend & \
	wait

# Runs on in-memory fixture data instead of a real bridge -- no config.yaml
# or bridge on the network needed. See backend/app/mock_hue_client.py.
dev-backend-demo:
	cd backend && . .venv/bin/activate && HUE_DEMO_MODE=true uvicorn app.main:app --reload --port 8000

dev-demo:
	@trap 'kill 0' EXIT; \
	$(MAKE) dev-backend-demo & \
	$(MAKE) dev-frontend & \
	wait

pair-bridge:
	cd backend && . .venv/bin/activate && python scripts/pair_bridge.py

.PHONY: dev dev-backend dev-frontend pair-bridge

dev-backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@trap 'kill 0' EXIT; \
	$(MAKE) dev-backend & \
	$(MAKE) dev-frontend & \
	wait

pair-bridge:
	cd backend && . .venv/bin/activate && python scripts/pair_bridge.py

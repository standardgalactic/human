.PHONY: api web agent

api:
	cd zebratube-api && uvicorn app.main:app --reload

web:
	cd zebratube-web && npm install && npm run dev

agent:
	cd zebra-agent && python -m src.agent --scan-dir ..

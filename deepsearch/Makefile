.PHONY: install-backend install-frontend start-backend start-frontend dev clean

# Backend commands
install-backend:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt

start-backend:
	. venv/bin/activate && python main.py

# Frontend commands
install-frontend:
	cd web && npm install

start-frontend:
	cd web && npm run start

# Development commands
dev:
	@echo "Starting both frontend and backend services..."
	@make start-backend & make start-frontend

# Clean up
clean:
	rm -rf venv
	cd web && rm -rf node_modules

# Help command
help:
	@echo "Available commands:"
	@echo "  make install-backend    - Install backend dependencies"
	@echo "  make install-frontend   - Install frontend dependencies"
	@echo "  make start-backend      - Start backend server"
	@echo "  make start-frontend     - Start frontend development server"
	@echo "  make dev               - Start both frontend and backend services"
	@echo "  make clean             - Clean up dependencies"
	@echo "  make help              - Show this help message" 

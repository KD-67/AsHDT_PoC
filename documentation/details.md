**Run the backend from cli:**
uvicorn main:app --reload --port 8000

##### Run the frontend from cli:
npm run dev
http://localhost:8000

##### Run the Stucturizr C4 diagrams:
Make sure docker desktop is running
docker compose -f documentation/architecture/docker-compose.yml up   
Open at http://localhost:8080
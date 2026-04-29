"""
Avvia il backend FastAPI in modalità sviluppo.
Uso: python run_api.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8765,
        reload=True,
        reload_dirs=["api", "db", "catasto_db_manager.py", "config.py"],
    )

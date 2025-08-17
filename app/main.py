from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from app.db.session import get_db, engine, SessionLocal
from app.db import models
from app.routers import auth, machines, users, service_report, dashboard
from app.middleware.auth import auth_middleware

# Load environment variables
load_dotenv()

# Create tables in the database
models.Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title="VacuuMVP API",
    description="Backend API for VacuuMVP application",
    version="0.1.0"
)

# Add authentication middleware
app.middleware("http")(auth_middleware)

# Initialize database
def init_db():
    db = SessionLocal()
    try:
        # Any necessary database initialization can be added here
        print("Database initialized and Connected")
        pass
    except Exception as e:
        db.rollback()
        print(f"Error initializing database: {e}")
    finally:
        db.close()

# Call init_db function
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(machines.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(service_report.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

# Root endpoint
@app.get("/")
def root():
    return {
        "message": "Welcome to VacuuMVP API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Health check endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Try to execute a simple query to check database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": str(import_time)
    }

# Import time for the health check
import time
import_time = time.time()

# Run the application
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
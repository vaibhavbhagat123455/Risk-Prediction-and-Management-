# app.py - Fixed Version with Better Parameter Handling
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import sqlite3
import datetime
from typing import Dict, List, Optional
import os

# Initialize FastAPI app
app = FastAPI(
    title="ConstructSafe AI MVP",
    description="Intelligent Construction Risk Management",
    version="2.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enhanced risk patterns with mitigation suggestions
RISK_PATTERNS = {
    "schedule": {
        "keywords": ["delay", "behind schedule", "late", "postpone", "extension", "timeline"],
        "mitigation": "Add buffer time, expedite critical path, monitor progress daily"
    },
    "cost": {
        "keywords": ["over budget", "cost overrun", "expensive", "price increase", "additional cost", "budget issue"],
        "mitigation": "Value engineering, negotiate contracts, monitor expenses weekly"
    },
    "safety": {
        "keywords": ["accident", "injury", "unsafe", "hazard", "danger", "violation", "safety concern"],
        "mitigation": "Safety training, daily inspections, implement safety protocols"
    },
    "quality": {
        "keywords": ["defect", "poor quality", "rework", "failure", "issue", "problem", "non-conformance"],
        "mitigation": "Quality control checks, supplier evaluation, testing protocols"
    }
}

# ===== DATABASE HELPER FUNCTIONS =====
def get_db_connection():
    conn = sqlite3.connect('construction_risks.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with error handling"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Projects table
        c.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'Planning',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Risks table
        c.execute('''
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                probability REAL,
                impact REAL,
                risk_score REAL,
                status TEXT DEFAULT 'Identified',
                priority TEXT,
                mitigation_plan TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if we have sample projects
        c.execute("SELECT COUNT(*) FROM projects")
        if c.fetchone()[0] == 0:
            sample_projects = [
                ('Downtown Office Tower', 'Commercial office building - 20 floors'),
                ('River Bridge Construction', 'Highway bridge across River'),
                ('Hospital Renovation', 'Medical facility upgrade')
            ]
            c.executemany(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                sample_projects
            )
            print("Sample projects inserted")
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database on startup
init_db()

# ===== ENHANCED ROUTES =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Enhanced dashboard with metrics"""
    try:
        conn = get_db_connection()
        
        # Get project statistics
        projects = conn.execute('''
            SELECT p.*, COUNT(r.id) as risk_count 
            FROM projects p 
            LEFT JOIN risks r ON p.id = r.project_id 
            GROUP BY p.id
        ''').fetchall()
        
        # Get risk statistics
        high_priority_result = conn.execute(
            "SELECT COUNT(*) FROM risks WHERE priority = 'HIGH' AND status != 'Closed'"
        ).fetchone()
        high_priority_risks = high_priority_result[0] if high_priority_result else 0
        
        total_risks_result = conn.execute("SELECT COUNT(*) FROM risks").fetchone()
        total_risks = total_risks_result[0] if total_risks_result else 0
        
        # Recent risks
        recent_risks = conn.execute('''
            SELECT r.*, p.name as project_name 
            FROM risks r 
            JOIN projects p ON r.project_id = p.id 
            ORDER BY r.created_date DESC 
            LIMIT 5
        ''').fetchall()
        
        conn.close()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "projects": projects,
            "high_priority_risks": high_priority_risks,
            "total_risks": total_risks,
            "recent_risks": recent_risks
        })
    except Exception as e:
        print(f"Dashboard error: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e)
        })

@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    """Enhanced projects management page"""
    try:
        conn = get_db_connection()
        projects = conn.execute('''
            SELECT p.*, COUNT(r.id) as risk_count 
            FROM projects p 
            LEFT JOIN risks r ON p.id = r.project_id 
            GROUP BY p.id
        ''').fetchall()
        conn.close()
        
        return templates.TemplateResponse("projects.html", {
            "request": request,
            "projects": projects
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Projects error: {e}"
        })

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """Enhanced risk analysis page"""
    try:
        conn = get_db_connection()
        projects = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        return templates.TemplateResponse("analyze.html", {
            "request": request,
            "projects": projects
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Analyze error: {e}"
        })

# Add this special route to handle empty project_id
@app.get("/risks", response_class=HTMLResponse)
async def risks_page_empty(request: Request):
    """Handle risks page without project_id parameter"""
    return await risks_page_main(request, None)

@app.get("/risks", response_class=HTMLResponse)
async def risks_page_main(request: Request, project_id: Optional[str] = None):
    """New risks management page - main implementation"""
    try:
        conn = get_db_connection()
        
        # Convert project_id to integer if it's not empty, otherwise use None
        project_id_int = None
        if project_id and project_id.strip():  # Check if not empty or just whitespace
            try:
                project_id_int = int(project_id)
            except ValueError:
                # If it's not a valid integer, treat it as no filter
                project_id_int = None
        
        if project_id_int:
            risks = conn.execute('''
                SELECT r.*, p.name as project_name 
                FROM risks r 
                JOIN projects p ON r.project_id = p.id 
                WHERE r.project_id = ?
                ORDER BY r.risk_score DESC
            ''', (project_id_int,)).fetchall()
        else:
            risks = conn.execute('''
                SELECT r.*, p.name as project_name 
                FROM risks r 
                JOIN projects p ON r.project_id = p.id 
                ORDER BY r.risk_score DESC
            ''').fetchall()
        
        projects = conn.execute("SELECT * FROM projects").fetchall()
        conn.close()
        
        return templates.TemplateResponse("risks.html", {
            "request": request,
            "risks": risks,
            "projects": projects,
            "selected_project_id": project_id_int
        })
    except Exception as e:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Risks error: {e}"
        })

# ===== ENHANCED API ENDPOINTS =====
@app.post("/api/projects")
async def create_project(
    name: str = Form(...),
    description: str = Form(None)
):
    """Create a new project with enhanced details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description or "")
        )
        
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"success": True, "project_id": project_id, "message": f"Project '{name}' created"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/analyze/text")
async def analyze_text(text: str = Form(...), project_id: int = Form(...)):
    """Enhanced text analysis with database storage"""
    try:
        detected_risks = []
        text_lower = text.lower()
        
        # Analyze text for risks
        for category, data in RISK_PATTERNS.items():
            found_keywords = []
            for keyword in data["keywords"]:
                if keyword in text_lower:
                    found_keywords.append(keyword)
            
            if found_keywords:
                # Calculate enhanced risk score
                probability = min(len(found_keywords) * 0.15, 0.9)
                impact = 0.7 if category in ['safety', 'cost'] else 0.5
                risk_score = probability * impact
                
                detected_risks.append({
                    "category": category.upper(),
                    "keywords_found": found_keywords,
                    "probability": probability,
                    "impact": impact,
                    "risk_score": risk_score,
                    "priority": "HIGH" if risk_score > 0.5 else "MEDIUM" if risk_score > 0.2 else "LOW",
                    "mitigation": data["mitigation"]
                })
        
        # Store analysis in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save individual risks
        for risk in detected_risks:
            cursor.execute('''
                INSERT INTO risks (
                    project_id, title, description, category, probability, impact, risk_score,
                    priority, mitigation_plan, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id,
                f"{risk['category']} Risk - {', '.join(risk['keywords_found'][:3])}",
                f"Automatically identified from text analysis. Keywords: {', '.join(risk['keywords_found'])}",
                risk['category'],
                risk['probability'],
                risk['impact'],
                risk['risk_score'],
                risk['priority'],
                risk['mitigation'],
                'Identified'
            ))
        
        conn.commit()
        conn.close()
        
        overall_score = sum(risk["risk_score"] for risk in detected_risks) / len(detected_risks) if detected_risks else 0
        
        return {
            "success": True,
            "total_risks_detected": len(detected_risks),
            "overall_risk_score": overall_score,
            "detected_risks": detected_risks,
            "risk_level": "HIGH" if overall_score > 0.6 else "MEDIUM" if overall_score > 0.3 else "LOW"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/risks/{risk_id}/update")
async def update_risk(
    risk_id: int,
    status: str = Form(...)
):
    """Update risk status and details"""
    try:
        conn = get_db_connection()
        conn.execute('UPDATE risks SET status = ? WHERE id = ?', (status, risk_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Risk updated successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===== HEALTH CHECK =====
@app.get("/health")
async def health_check():
    """Enhanced health check"""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return {"status": "healthy", "database": "connected", "version": "2.0.0"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
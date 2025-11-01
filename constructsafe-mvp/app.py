# app.py - Day 1 Foundation
from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from typing import Dict, List

# Initialize FastAPI app
app = FastAPI(
    title="ConstructSafe AI MVP",
    description="Intelligent Construction Risk Management",
    version="1.0.0"
)

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Simple in-memory storage (we'll replace with database later)
projects: Dict[int, Dict] = {
    1: {"id": 1, "name": "Downtown Office Tower", "status": "Planning"},
    2: {"id": 2, "name": "River Bridge Construction", "status": "Active"}
}

risks: List[Dict] = []

# Risk patterns for basic detection
RISK_PATTERNS = {
    "schedule": ["delay", "behind schedule", "late", "postpone", "extension"],
    "cost": ["over budget", "cost overrun", "expensive", "price increase", "additional cost"],
    "safety": ["accident", "injury", "unsafe", "hazard", "danger", "violation"],
    "quality": ["defect", "poor quality", "rework", "failure", "issue", "problem"]
}

# ===== BASIC ROUTES =====
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "projects": projects,
            "total_risks": len(risks),
            "active_projects": len([p for p in projects.values() if p["status"] == "Active"])
        }
    )

@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    """Projects management page"""
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects})

@app.get("/analyze", response_class=HTMLResponse)
async def analyze_page(request: Request):
    """Risk analysis page"""
    return templates.TemplateResponse("analyze.html", {"request": request, "projects": projects})

# ===== BASIC API ENDPOINTS =====
@app.post("/api/projects")
async def create_project(project_name: str = Form(...)):
    """Create a new project"""
    new_id = max(projects.keys()) + 1 if projects else 1
    projects[new_id] = {
        "id": new_id,
        "name": project_name,
        "status": "Planning"
    }
    return {"success": True, "project_id": new_id, "message": f"Project '{project_name}' created"}

@app.post("/api/analyze/text")
async def analyze_text(text: str = Form(...), project_id: int = Form(...)):
    """Basic text analysis for risk detection"""
    
    detected_risks = []
    text_lower = text.lower()
    
    # Simple keyword matching
    for category, keywords in RISK_PATTERNS.items():
        found_keywords = []
        for keyword in keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        if found_keywords:
            # Calculate simple risk score
            risk_score = min(len(found_keywords) * 0.2, 1.0)
            
            detected_risks.append({
                "category": category.upper(),
                "keywords_found": found_keywords,
                "risk_score": risk_score,
                "priority": "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.3 else "LOW"
            })
    
    # Create risk summary
    total_risk_score = sum(risk["risk_score"] for risk in detected_risks) / len(detected_risks) if detected_risks else 0
    
    # Store the risks
    for risk in detected_risks:
        risk_record = {
            "id": len(risks) + 1,
            "project_id": project_id,
            "category": risk["category"],
            "description": f"Found keywords: {', '.join(risk['keywords_found'])}",
            "risk_score": risk["risk_score"],
            "priority": risk["priority"],
            "source_text": text[:100] + "..." if len(text) > 100 else text
        }
        risks.append(risk_record)
    
    return {
        "success": True,
        "total_risks_detected": len(detected_risks),
        "overall_risk_score": total_risk_score,
        "detected_risks": detected_risks,
        "risk_level": "HIGH" if total_risk_score > 0.7 else "MEDIUM" if total_risk_score > 0.4 else "LOW"
    }

@app.get("/api/risks")
async def get_risks():
    """Get all identified risks"""
    return {"success": True, "risks": risks}

# ===== HEALTH CHECK =====
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "projects_count": len(projects),
        "risks_count": len(risks),
        "version": "1.0.0"
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Set
from auth import TokenData, get_current_roles

app = FastAPI(title="service-a", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

def require_roles(required: Set[str]):
    def checker(roles: Set[str] = Depends(get_current_roles)):
        if not (roles & required):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: insufficient role")
        return True
    return checker

@app.get("/reports")
def reports(_: bool = Depends(require_roles({"admin", "analyst"}))):
    # Exemplo de payload
    return {"reports": [{"id": 1, "title": "Monthly KPIs"}, {"id": 2, "title": "Security Events"}]}

@app.get("/admin")
def admin(_: bool = Depends(require_roles({"admin"}))):
    return {"admin": {"message": "Welcome, admin!"}}

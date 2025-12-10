#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
programista_endpoint.py - Code Execution API
Używa core/executor.py (Programista class)
"""

from response_adapter import adapt
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os

from dataclasses import dataclass, asdict
from core.executor import Programista, ExecResult
from core.auth import check_auth

def _wrap_for_ui(payload):
    try:
        return adapt(payload)
    except Exception:
        return _wrap_for_ui({"text": str(payload), "sources": []})

router = APIRouter(prefix="/api/code")

# Auth
def _auth(req: Request):
    if not check_auth(req):
        raise HTTPException(401, "unauthorized")

# Models
class ExecRequest(BaseModel):
    cmd: str
    cwd: Optional[str] = None
    timeout: Optional[float] = None
    confirm: bool = False
    dry_run: bool = False
    shell: bool = False

class WriteFileRequest(BaseModel):
    path: str
    content: str
    confirm: bool = False

class ProjectInitRequest(BaseModel):
    name: str
    kind: str = "py-lib"  # py-lib | py-cli | py-api | js-lib | js-app

class PlanRequest(BaseModel):
    goal: str
    stack: str = "python"  # python | javascript

class LintRequest(BaseModel):
    tool: str = "ruff"  # ruff | flake8 | eslint
    fix: bool = False
    confirm: bool = False

class TestRequest(BaseModel):
    framework: str = "pytest"  # pytest | jest
    coverage: bool = False
    confirm: bool = False

class GitRequest(BaseModel):
    subcommand: str  # status | add | commit | push | pull
    args: str = ""
    confirm: bool = False

class DockerBuildRequest(BaseModel):
    tag: str
    dockerfile: str = "Dockerfile"
    confirm: bool = False

class DepsInstallRequest(BaseModel):
    manager: str = "pip"  # pip | npm | yarn
    file: str = ""  # requirements.txt | package.json
    confirm: bool = False

# ===== ENDPOINTS =====

@router.get("/snapshot")
async def snapshot(_=Depends(_auth)):
    """
    📊 System snapshot - dostępne narzędzia
    
    Zwraca informacje o dostępnych narzędziach programistycznych
    """
    try:
        prog = Programista()
        snap = prog.snapshot()
        return _wrap_for_ui({"ok": True, **snap})
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/exec")
async def exec_command(body: ExecRequest, _=Depends(_auth)):
    """
    🔧 Execute shell command
    
    Wymaga confirm=True dla bezpieczeństwa!
    Użyj dry_run=True dla preview.
    """
    try:
        prog = Programista()
        result = prog.exec(
            body.cmd,
            cwd=body.cwd,
            timeout=body.timeout,
            confirm=body.confirm,
            dry_run=body.dry_run,
            shell=body.shell
        )
        return _wrap_for_ui(result)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/write")
async def write_file(body: WriteFileRequest, _=Depends(_auth)):
    """
    📝 Write file
    
    Wymaga confirm=True!
    """
    try:
        prog = Programista()
        result = prog.write_file(body.path, body.content, confirm=body.confirm)
        return _wrap_for_ui(result)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.get("/read")
async def read_file(path: str, _=Depends(_auth)):
    """
    📖 Read file
    """
    try:
        prog = Programista()
        content = prog.read_file(path)
        return _wrap_for_ui({"ok": True, "path": path, "content": content})
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.get("/tree")
async def read_tree(max_depth: int = 3, max_files: int = 200, _=Depends(_auth)):
    """
    🌳 Read project tree
    """
    try:
        import os
        from pathlib import Path
        dev_root = os.getenv("DEV_ROOT", ".")
        
        def get_tree(path: Path, depth: int = 0, max_d: int = 3) -> list:
            if depth >= max_d:
                return []
            items = []
            try:
                for item in sorted(path.iterdir())[:50]:
                    if item.name.startswith('.'):
                        continue
                    if item.is_dir():
                        items.append({"name": item.name, "type": "dir", "children": get_tree(item, depth+1, max_d)})
                    else:
                        items.append({"name": item.name, "type": "file", "size": item.stat().st_size})
            except:
                pass
            return items
        
        tree = get_tree(Path(dev_root), 0, max_depth)
        return {"ok": True, "tree": tree, "root": dev_root}
    except Exception as e:
        return {"ok": True, "tree": [], "note": f"Tree unavailable: {str(e)[:50]}"}

@router.post("/init")
async def project_init(body: ProjectInitRequest, _=Depends(_auth)):
    """
    🆕 Initialize new project
    
    Creates: src/, tests/, README.md, pyproject.toml/package.json
    """
    try:
        prog = Programista()
        result = prog.project_init(body.name, body.kind)
        return _wrap_for_ui(result)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/plan")
async def plan(body: PlanRequest, _=Depends(_auth)):
    """
    📋 Plan project steps
    
    Zwraca rekomendowane kroki dla projektu
    """
    try:
        prog = Programista()
        plan = prog.plan(body.goal, body.stack)
        return plan
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/lint")
async def lint(body: LintRequest, _=Depends(_auth)):
    """
    ✨ Lint code
    
    Wymaga confirm=True jeśli fix=True!
    """
    if not body.confirm:
        return {"ok": True, "status": "dry_run", "message": "Set confirm=True to run lint"}
    return {"ok": True, "status": "lint_skipped", "note": "Lint requires external tools"}

@router.post("/test")
async def test(body: TestRequest, _=Depends(_auth)):
    """
    🧪 Run tests
    
    Wymaga confirm=True!
    """
    if not body.confirm:
        return {"ok": True, "status": "dry_run", "message": "Set confirm=True to run tests"}
    return {"ok": True, "status": "test_skipped", "note": "Tests require external tools"}

@router.post("/format")
async def format_code(tool: str = "black", check: bool = False, confirm: bool = False, _=Depends(_auth)):
    """
    💅 Format code
    
    Wymaga confirm=True jeśli check=False!
    """
    if not confirm:
        return {"ok": True, "status": "dry_run", "message": "Set confirm=True to format"}
    return {"ok": True, "status": "format_skipped", "note": "Format requires external tools"}

@router.post("/git")
async def git(body: GitRequest, _=Depends(_auth)):
    """
    🔀 Git operations
    
    Wymaga confirm=True dla destructive ops (commit, push)!
    """
    try:
        prog = Programista()
        result = prog.git(body.subcommand, body.args, confirm=body.confirm)
        return _wrap_for_ui(result)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/docker/build")
async def docker_build(body: DockerBuildRequest, _=Depends(_auth)):
    """
    🐳 Build Docker image
    
    Wymaga confirm=True!
    """
    try:
        prog = Programista()
        result = prog.docker_build(body.tag, body.dockerfile, confirm=body.confirm)
        return _wrap_for_ui(result)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/docker/run")
async def docker_run(image: str, args: str = "", confirm: bool = False, _=Depends(_auth)):
    """
    🚀 Run Docker container
    
    Wymaga confirm=True!
    """
    try:
        prog = Programista()
        result = prog.docker_run(image, args, confirm=confirm)
        return _wrap_for_ui(result)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")

@router.post("/deps/install")
async def deps_install(body: DepsInstallRequest, _=Depends(_auth)):
    """
    📦 Install dependencies
    
    Wymaga confirm=True!
    """
    if not body.confirm:
        return {"ok": True, "status": "dry_run", "message": "Set confirm=True to install deps"}
    return {"ok": True, "status": "deps_skipped", "note": "Deps install requires external tools"}

# Helpers
def _get_personality_type(state: Dict[str, float]) -> str:
    """Interpret Big Five personality"""
    o = state.get('openness', 0.5)
    c = state.get('conscientiousness', 0.5)
    e = state.get('energy', 0.5)
    a = state.get('agreeableness', 0.5)
    n = state.get('neuroticism', 0.5)
    
    if o > 0.7 and c > 0.7:
        return "Innovator"
    elif c > 0.7 and a > 0.7:
        return "Organizer"
    elif e > 0.7 and a > 0.7:
        return "Social"
    elif o > 0.7 and e > 0.7:
        return "Explorer"
    elif c > 0.7 and n < 0.3:
        return "Reliable"
    else:
        return "Balanced"

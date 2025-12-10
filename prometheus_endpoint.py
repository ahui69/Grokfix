#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus metrics endpoint - monitoring i statystyki
"""

from fastapi import APIRouter, Response
from typing import Dict, Any
import time
import psutil
import os

router = APIRouter()

# In-memory metrics
_metrics = {
    "requests_total": 0,
    "errors_total": 0,
    "start_time": time.time()
}


def _get_system_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent
        }
    except:
        return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}


@router.get("/metrics")
async def get_prometheus_metrics():
    """Endpoint dla Prometheus - metryki w formacie tekstowym"""
    _metrics["requests_total"] += 1
    sys = _get_system_metrics()
    uptime = time.time() - _metrics["start_time"]
    
    content = f"""# HELP mordzix_requests_total Total requests
# TYPE mordzix_requests_total counter
mordzix_requests_total {_metrics["requests_total"]}

# HELP mordzix_errors_total Total errors
# TYPE mordzix_errors_total counter
mordzix_errors_total {_metrics["errors_total"]}

# HELP mordzix_uptime_seconds Uptime in seconds
# TYPE mordzix_uptime_seconds gauge
mordzix_uptime_seconds {uptime:.2f}

# HELP mordzix_cpu_percent CPU usage percent
# TYPE mordzix_cpu_percent gauge
mordzix_cpu_percent {sys["cpu_percent"]}

# HELP mordzix_memory_percent Memory usage percent
# TYPE mordzix_memory_percent gauge
mordzix_memory_percent {sys["memory_percent"]}
"""
    return Response(content=content, media_type="text/plain")


@router.get("/health")
async def health_check():
    """Health check dla Prometheus"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - _metrics["start_time"]
    }


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """Statystyki w formacie JSON"""
    sys = _get_system_metrics()
    return {
        "ok": True,
        "requests_total": _metrics["requests_total"],
        "errors_total": _metrics["errors_total"],
        "uptime_seconds": time.time() - _metrics["start_time"],
        "system": sys
    }

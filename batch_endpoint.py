#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM Batch Processing Endpoint - API do wsadowego przetwarzania zapytań LLM
Pozwala na wydajne wykonywanie wielu zapytań LLM jednocześnie.
"""

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import List, Dict, Any, Optional
import asyncio
import time

from core.auth import verify_token
from batch_processing import (
    process_batch, 
    call_llm_batch, 
    get_batch_metrics, 
    shutdown_batch_processor
)

# Utwórz router
router = APIRouter(
    prefix="/api/batch",
    tags=["LLM Batch Processing"],
    responses={404: {"description": "Not found"}},
)


@router.post("/process", summary="Wykonuje wsadowe przetwarzanie zapytań LLM")
async def batch_process_endpoint(
    data: Dict[str, Any] = Body(...),
    auth=Depends(verify_token)
):
    """
    Wykonuje wsadowe przetwarzanie wielu zapytań LLM jednocześnie
    
    Args:
        data: Zawiera:
            - messages_list: Lista list wiadomości (każda lista to wiadomości dla jednego wywołania LLM)
            - params_list: (opcjonalne) Lista parametrów dla każdego wywołania
            
    Returns:
        Lista odpowiedzi LLM
    """
    try:
        # Sprawdź wymagane pola
        messages_list = data.get("messages_list")
        
        if not messages_list:
            raise HTTPException(status_code=400, detail="Brakujące pole: messages_list")
        
        # Sprawdź poprawność danych
        if not isinstance(messages_list, list):
            raise HTTPException(status_code=400, detail="messages_list musi być listą")
        
        if not all(isinstance(msgs, list) for msgs in messages_list):
            raise HTTPException(status_code=400, detail="Każdy element messages_list musi być listą")
        
        # Opcjonalne parametry
        params_list = data.get("params_list", [{} for _ in range(len(messages_list))])
        
        # Sprawdź poprawność params_list
        if not isinstance(params_list, list):
            raise HTTPException(status_code=400, detail="params_list musi być listą")
        
        if len(params_list) != len(messages_list):
            raise HTTPException(status_code=400, 
                               detail="params_list musi mieć taką samą długość jak messages_list")
        
        # Wykonaj wsadowe przetwarzanie
        start_time = time.time()
        results = await process_batch(messages_list, params_list)
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "results": results,
            "count": len(results),
            "processing_time_ms": round(duration * 1000, 2)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/submit", summary="Dodaje pojedyncze zapytanie do wsadowego przetwarzania")
async def batch_submit_endpoint(
    data: Dict[str, Any] = Body(...),
    auth=Depends(verify_token)
):
    """
    Dodaje pojedyncze zapytanie do wsadowego przetwarzania
    
    Args:
        data: Zawiera:
            - messages: Lista wiadomości dla LLM
            - params: (opcjonalne) Parametry dla LLM
            - priority: (opcjonalne) Priorytet zapytania
            - request_id: (opcjonalne) Identyfikator zapytania
            
    Returns:
        Odpowiedź LLM
    """
    try:
        # Sprawdź wymagane pola
        messages = data.get("messages")
        
        if not messages:
            raise HTTPException(status_code=400, detail="Brakujące pole: messages")
        
        # Opcjonalne pola
        params = data.get("params", {})
        priority = data.get("priority", 0)
        request_id = data.get("request_id")
        
        # Dodaj do wsadowego przetwarzania
        start_time = time.time()
        result = await call_llm_batch(
            messages=messages,
            params=params,
            priority=priority,
            request_id=request_id
        )
        duration = time.time() - start_time
        
        return {
            "status": "success",
            "result": result,
            "processing_time_ms": round(duration * 1000, 2)
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/metrics", summary="Pobiera metryki procesora wsadowego")
async def batch_metrics_endpoint(auth=Depends(verify_token)):
    """
    Pobiera metryki i statystyki procesora wsadowego
    
    Returns:
        Metryki procesora wsadowego
    """
    try:
        metrics = get_batch_metrics()
        
        return {
            "status": "success",
            "metrics": metrics
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.post("/shutdown", summary="Zatrzymuje procesor wsadowy")
async def batch_shutdown_endpoint(auth=Depends(verify_token)):
    """
    Zatrzymuje procesor wsadowy
    
    Returns:
        Status operacji
    """
    try:
        await shutdown_batch_processor()
        
        return {
            "status": "success",
            "message": "Procesor wsadowy zatrzymany"
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
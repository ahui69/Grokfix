#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fashion Endpoint - AI Fashion Manager API
Stylizacje, trendy, rozpoznawanie marek, opisy aukcji
"""

import os
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from .auth import check_auth
from .helpers import log_info, log_error
from .ai_fashion import AIFashionManager
from .ai_auction import AIAuctionManager

router = APIRouter(prefix="/api/fashion", tags=["AI Fashion"])

# Initialize managers
fashion_manager = AIFashionManager()
auction_manager = AIAuctionManager()

# Auth
def _auth(req: Request):
    if not check_auth(req):
        raise HTTPException(401, "Unauthorized")

# ============================================================================
# MODELS
# ============================================================================

class OutfitRequest(BaseModel):
    occasion: str  # np. "praca", "randka", "impreza"
    weather: str = "umiarkowany"  # "zimno", "ciepło", "gorąco"
    style: str = "casual"  # "elegancki", "sportowy", "streetwear"
    budget: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class DescriptionRequest(BaseModel):
    item_type: str  # "kurtka", "buty", "sukienka"
    brand: str
    condition: str = "bardzo dobry"
    size: str = "M"
    color: str = ""
    material: str = ""
    details: Optional[str] = ""
    platform: str = "vinted"  # "vinted", "olx", "allegro", "vestiaire"

class PriceRequest(BaseModel):
    item_type: str
    brand: str
    condition: str
    category: str = "odzież"
    image_url: Optional[str] = None

class TrendRequest(BaseModel):
    category: str = "all"  # "streetwear", "luxury", "sport", "vintage"
    season: str = "current"
    region: str = "pl"

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/outfit")
async def generate_outfit(req: Request, body: OutfitRequest):
    """Generuj propozycję stylizacji"""
    _auth(req)
    
    try:
        # Słownik stylów i sugestii
        style_suggestions = {
            "casual": ["jeansy", "t-shirt", "sneakersy", "kurtka bomber"],
            "elegancki": ["garnitur/sukienka", "koszula", "buty skórzane", "pasek"],
            "sportowy": ["legginsy/dresy", "bluza", "buty do biegania", "plecak"],
            "streetwear": ["hoodie oversize", "cargo pants", "Jordan/AF1", "nerka"],
            "boho": ["długa spódnica", "bluzka", "sandały", "biżuteria"],
        }
        
        weather_tips = {
            "zimno": "Dodaj: puchówka, szalik, czapka, rękawiczki",
            "ciepło": "Lekkie materiały: len, bawełna, przewiewne tkaniny",
            "gorąco": "Krótkie rękawy, sandały, jasne kolory",
            "umiarkowany": "Warstwowy look - możesz dodać/zdjąć element",
            "deszczowo": "Wodoodporna kurtka, buty przeciwdeszczowe"
        }
        
        base_items = style_suggestions.get(body.style, style_suggestions["casual"])
        weather_tip = weather_tips.get(body.weather, weather_tips["umiarkowany"])
        
        outfit = {
            "occasion": body.occasion,
            "style": body.style,
            "weather": body.weather,
            "suggested_items": base_items,
            "weather_tip": weather_tip,
            "color_palette": ["czarny", "biały", "beżowy", "granatowy"],
            "accessories": ["zegarek", "okulary przeciwsłoneczne", "torba"],
            "tips": [
                f"Na {body.occasion} - postaw na {body.style} look",
                "Dobierz kolory pasujące do siebie",
                "Pamiętaj o wygodzie!"
            ]
        }
        
        if body.budget:
            outfit["budget_tip"] = f"W budżecie {body.budget} - sprawdź second-hand i outlet"
        
        log_info(f"[FASHION] Generated outfit for {body.occasion}/{body.style}")
        return {"success": True, "outfit": outfit}
        
    except Exception as e:
        log_error(f"[FASHION] outfit error: {e}")
        raise HTTPException(500, str(e))


@router.post("/description")
async def generate_description(req: Request, body: DescriptionRequest):
    """Generuj opis aukcji w stylu platform sprzedażowych"""
    _auth(req)
    
    try:
        # Brand tiers dla odpowiedniego tonu
        luxury_brands = ["louis vuitton", "gucci", "prada", "balenciaga", "burberry", "hermes", "chanel", "dior"]
        streetwear_brands = ["supreme", "off-white", "stone island", "palace", "bape", "fear of god", "stussy"]
        premium_brands = ["ralph lauren", "tommy hilfiger", "calvin klein", "hugo boss", "lacoste"]
        
        brand_lower = body.brand.lower()
        
        if any(b in brand_lower for b in luxury_brands):
            tier = "luxury"
            tone = "ekskluzywny, elegancki"
            keywords = ["investment piece", "kultowy model", "ponadczasowy design"]
        elif any(b in brand_lower for b in streetwear_brands):
            tier = "streetwear"
            tone = "hypebeast, limitowany"
            keywords = ["grail", "rare", "sold out", "hype"]
        elif any(b in brand_lower for b in premium_brands):
            tier = "premium"
            tone = "klasyczny, jakościowy"
            keywords = ["ponadczasowy", "versatile", "wardrobe staple"]
        else:
            tier = "standard"
            tone = "praktyczny, modny"
            keywords = ["super stan", "okazja", "polecam"]
        
        # Buduj opis
        condition_map = {
            "nowy": "🏷️ NOWY Z METKĄ - nigdy nieużywany!",
            "idealny": "✨ IDEALNY STAN - jak nowy, bez śladów noszenia",
            "bardzo dobry": "👍 BARDZO DOBRY STAN - minimalne ślady użytkowania",
            "dobry": "👌 DOBRY STAN - widoczne ślady noszenia",
        }
        
        platform_style = {
            "vinted": {"emoji": True, "hashtags": True, "casual": True},
            "olx": {"emoji": True, "hashtags": False, "casual": True},
            "allegro": {"emoji": False, "hashtags": False, "casual": False},
            "vestiaire": {"emoji": False, "hashtags": False, "casual": False, "english": True},
        }
        
        style = platform_style.get(body.platform, platform_style["vinted"])
        cond_text = condition_map.get(body.condition, condition_map["bardzo dobry"])
        
        # Generuj opis
        title = f"{body.brand.upper()} {body.item_type}"
        if body.color:
            title += f" {body.color}"
        
        description_parts = [
            f"🔥 {title} 🔥" if style.get("emoji") else title,
            "",
            cond_text if style.get("emoji") else body.condition.upper(),
            "",
            f"📏 Rozmiar: {body.size}" if style.get("emoji") else f"Rozmiar: {body.size}",
        ]
        
        if body.material:
            description_parts.append(f"🧵 Materiał: {body.material}" if style.get("emoji") else f"Materiał: {body.material}")
        
        if body.details:
            description_parts.append("")
            description_parts.append(body.details)
        
        description_parts.append("")
        description_parts.append(f"✅ {keywords[0].capitalize()}" if style.get("emoji") else keywords[0].capitalize())
        
        if style.get("hashtags"):
            tags = [f"#{body.brand.lower().replace(' ', '')}", f"#{body.item_type}", "#vintage", "#secondhand"]
            description_parts.append("")
            description_parts.append(" ".join(tags[:4]))
        
        description = "\n".join(description_parts)
        
        log_info(f"[FASHION] Generated description for {body.brand} {body.item_type}")
        
        return {
            "success": True,
            "title": title,
            "description": description,
            "tier": tier,
            "platform": body.platform,
            "suggested_keywords": keywords,
            "tips": [
                "Dodaj 4-6 zdjęć z różnych kątów",
                "Pokaż metki i detale",
                "Zmierz i podaj wymiary"
            ]
        }
        
    except Exception as e:
        log_error(f"[FASHION] description error: {e}")
        raise HTTPException(500, str(e))


@router.post("/price")
async def estimate_price(req: Request, body: PriceRequest):
    """Oszacuj cenę przedmiotu na podstawie marki i stanu"""
    _auth(req)
    
    try:
        # Bazowe mnożniki dla marek
        brand_multipliers = {
            "gucci": 15, "louis vuitton": 18, "prada": 12, "balenciaga": 14,
            "supreme": 8, "off-white": 10, "stone island": 6, "palace": 5,
            "ralph lauren": 3, "tommy hilfiger": 2.5, "calvin klein": 2,
            "zara": 0.8, "h&m": 0.5, "reserved": 0.4
        }
        
        condition_multipliers = {
            "nowy": 1.0, "idealny": 0.85, "bardzo dobry": 0.7, "dobry": 0.5, "dostateczny": 0.3
        }
        
        # Bazowa cena według typu
        base_prices = {
            "kurtka": 150, "bluza": 80, "spodnie": 70, "t-shirt": 40,
            "buty": 120, "sukienka": 100, "płaszcz": 200, "torebka": 150,
            "czapka": 30, "szalik": 40, "pasek": 50
        }
        
        base = base_prices.get(body.item_type.lower(), 80)
        brand_mult = brand_multipliers.get(body.brand.lower(), 1.5)
        cond_mult = condition_multipliers.get(body.condition.lower(), 0.7)
        
        estimated_price = int(base * brand_mult * cond_mult)
        
        # Range
        min_price = int(estimated_price * 0.7)
        max_price = int(estimated_price * 1.3)
        
        log_info(f"[FASHION] Price estimate for {body.brand} {body.item_type}: {estimated_price} PLN")
        
        return {
            "success": True,
            "estimated_price": estimated_price,
            "price_range": {"min": min_price, "max": max_price},
            "currency": "PLN",
            "factors": {
                "brand_tier": "luxury" if brand_mult > 10 else "premium" if brand_mult > 3 else "standard",
                "condition_impact": f"{int(cond_mult * 100)}%",
            },
            "tips": [
                "Sprawdź podobne oferty na Vinted/OLX",
                "Oryginalne opakowanie podnosi wartość o 10-20%",
                "Limitowane edycje mogą być warte znacznie więcej"
            ]
        }
        
    except Exception as e:
        log_error(f"[FASHION] price error: {e}")
        raise HTTPException(500, str(e))


@router.post("/trends")
async def get_trends(req: Request, body: TrendRequest):
    """Aktualne trendy modowe"""
    _auth(req)
    
    try:
        trends = {
            "streetwear": {
                "hot": ["gorpcore", "techwear", "vintage Nike", "baggy jeans", "cargo pants"],
                "rising": ["quiet luxury streetwear", "Y2K revival", "archival pieces"],
                "brands": ["Arc'teryx", "Salomon", "New Balance", "Carhartt WIP"],
            },
            "luxury": {
                "hot": ["quiet luxury", "old money aesthetic", "minimalizm", "neutral colors"],
                "rising": ["sustainable luxury", "pre-owned designer", "capsule wardrobe"],
                "brands": ["The Row", "Loro Piana", "Brunello Cucinelli"],
            },
            "sport": {
                "hot": ["athleisure", "running shoes as fashion", "tennis core"],
                "rising": ["hiking fashion", "outdoor tech", "retro sportswear"],
                "brands": ["On Running", "Hoka", "Satisfy", "District Vision"],
            },
            "vintage": {
                "hot": ["80s/90s denim", "vintage band tees", "retro sportswear"],
                "rising": ["70s boho", "Y2K accessories", "vintage luxury bags"],
                "brands": ["Levi's vintage", "Carhartt vintage", "Champion reverse weave"],
            }
        }
        
        category_data = trends.get(body.category, {
            "hot": list(set(sum([t["hot"] for t in trends.values()], []))),
            "rising": list(set(sum([t["rising"] for t in trends.values()], []))),
            "brands": list(set(sum([t["brands"] for t in trends.values()], [])))
        })
        
        log_info(f"[FASHION] Trends for {body.category}")
        
        return {
            "success": True,
            "category": body.category,
            "season": body.season,
            "trends": category_data,
            "tip": "Trendy zmieniają się szybko - inwestuj w klasyki z twistem"
        }
        
    except Exception as e:
        log_error(f"[FASHION] trends error: {e}")
        raise HTTPException(500, str(e))


@router.get("/brands")
async def get_brands(req: Request, category: str = "all"):
    """Lista marek według kategorii"""
    _auth(req)
    
    brands = {
        "luxury": ["Louis Vuitton", "Gucci", "Prada", "Balenciaga", "Burberry", "Dior", "Chanel", "Hermès"],
        "streetwear": ["Supreme", "Off-White", "Stone Island", "Palace", "BAPE", "Fear of God", "Stüssy"],
        "premium": ["Ralph Lauren", "Tommy Hilfiger", "Calvin Klein", "Hugo Boss", "Lacoste", "Gant"],
        "sport": ["Nike", "Adidas", "New Balance", "Puma", "Reebok", "Under Armour", "Asics"],
        "outdoor": ["The North Face", "Arc'teryx", "Patagonia", "Columbia", "Salomon", "Mammut"],
        "fast_fashion": ["Zara", "H&M", "Reserved", "Bershka", "Pull&Bear", "Stradivarius"],
    }
    
    if category == "all":
        all_brands = []
        for cat_brands in brands.values():
            all_brands.extend(cat_brands)
        return {"success": True, "brands": sorted(set(all_brands)), "categories": list(brands.keys())}
    
    return {"success": True, "category": category, "brands": brands.get(category, [])}

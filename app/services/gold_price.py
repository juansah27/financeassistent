"""
Gold Price Service
Fetch current gold prices from Logam Mulia website or fallback API
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Cache for gold price
_price_cache: Dict[str, any] = {
    "price": None,
    "timestamp": None
}
CACHE_DURATION = timedelta(hours=1)


def get_current_gold_price() -> Optional[float]:
    """
    Get current gold price per gram in IDR
    Returns: Price per gram (float) or None if failed
    """
    # Check cache first
    if _price_cache["price"] and _price_cache["timestamp"]:
        if datetime.now() - _price_cache["timestamp"] < CACHE_DURATION:
            logger.info(f"Returning cached gold price: {_price_cache['price']}")
            return _price_cache["price"]
    
    # Try web scraping from Logam Mulia
    price = _scrape_logam_mulia()
    
    # Fallback to alternative sources if scraping fails
    if price is None:
        price = _get_gold_price_fallback()
    
    # Update cache if we got a price
    if price:
        _price_cache["price"] = price
        _price_cache["timestamp"] = datetime.now()
        logger.info(f"Updated gold price cache: {price}")
    
    return price


def _scrape_logam_mulia() -> Optional[float]:
    """
    Scrape gold price from Logam Mulia website
    """
    try:
        url = "https://logammulia.com/id/harga-hari-ini"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Try to find the price for 1 gram gold
        # This selector may need adjustment based on actual website structure
        price_elements = soup.find_all(['td', 'div', 'span'], string=re.compile(r'1\s*gram', re.IGNORECASE))
        
        for element in price_elements:
            # Look for price in nearby elements
            parent = element.parent
            if parent:
                # Find sell price (harga jual)
                price_text = parent.find(string=re.compile(r'Rp[\s\d\.,]+'))
                if price_text:
                    # Extract number from price text
                    price = _extract_price(price_text)
                    if price:
                        logger.info(f"Successfully scraped gold price from Logam Mulia: {price}")
                        return price
        
        # Alternative: look for any price pattern
        all_prices = soup.find_all(string=re.compile(r'Rp[\s\d\.,]+'))
        if all_prices:
            # Try first reasonable price (between 500k - 2M per gram)
            for price_text in all_prices[:10]:  # Check first 10 matches
                price = _extract_price(price_text)
                if price and 500_000 <= price <= 2_000_000:
                    logger.info(f"Found potential gold price: {price}")
                    return price
        
        logger.warning("Could not find gold price in Logam Mulia website")
        return None
        
    except requests.Timeout:
        logger.error("Timeout scraping Logam Mulia website")
        return None
    except requests.RequestException as e:
        logger.error(f"Error scraping Logam Mulia: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in scraping: {e}")
        return None


def _extract_price(text: str) -> Optional[float]:
    """
    Extract price number from text like "Rp 1.050.000" or "Rp 1,050,000"
    """
    try:
        # Remove "Rp", spaces, dots, commas
        cleaned = re.sub(r'[Rp\s\.,]', '', text)
        # Extract digits
        digits = re.findall(r'\d+', cleaned)
        if digits:
            price = float(''.join(digits))
            return price
        return None
    except Exception as e:
        logger.error(f"Error extracting price from '{text}': {e}")
        return None


def _get_gold_price_fallback() -> Optional[float]:
    """
    Fallback method using estimated price based on Pegadaian market data
    In production, this could use a paid API or return last known good price
    """
    logger.warning("Using fallback gold price estimation")
    # Return a reasonable buyback estimate based on Pegadaian data
    # Pegadaian gold prices (Antam) as of Jan 2026: ~Rp 2.759.000 (buy)
    # Buyback price is typically ~10% lower
    return 2_500_000  # Rp per gram (buyback estimate)


def update_gold_asset_price(db, asset_id: int, user_id: int) -> Dict:
    """
    Update a gold asset's price based on current market price
    
    Args:
        db: Database session
        asset_id: Asset ID to update
        user_id: User ID (for verification)
    
    Returns:
        Dict with status, new_value, price_per_gram
    """
    from app.db import crud_extended
    from app.db.models import AssetType
    
    # Get the asset
    asset = crud_extended.get_asset_by_id(db, asset_id, user_id)
    
    if not asset:
        return {
            "success": False,
            "error": "Asset not found"
        }
    
    # Verify it's a gold asset
    if asset.asset_type != AssetType.GOLD:
        return {
            "success": False,
            "error": "Asset is not a gold asset"
        }
    
    # Check if asset has quantity
    if not asset.quantity or asset.quantity <= 0:
        return {
            "success": False,
            "error": "Asset does not have quantity. Please add quantity (in grams) first."
        }
    
    # Get current gold price
    price_per_gram = get_current_gold_price()
    
    if not price_per_gram:
        return {
            "success": False,
            "error": "Failed to fetch current gold price. Please try again later."
        }
    
    # Calculate new value
    new_value = asset.quantity * price_per_gram
    
    # Update asset value
    notes = f"Auto-update harga emas: Rp {price_per_gram:,.0f}/gram × {asset.quantity} gram"
    updated_asset = crud_extended.update_asset_value(
        db, asset_id, user_id, new_value, notes
    )
    
    if updated_asset:
        return {
            "success": True,
            "new_value": new_value,
            "price_per_gram": price_per_gram,
            "quantity": asset.quantity,
            "asset": updated_asset
        }
    else:
        return {
            "success": False,
            "error": "Failed to update asset value"
        }


def clear_price_cache():
    """Clear the price cache (useful for testing)"""
    global _price_cache
    _price_cache = {"price": None, "timestamp": None}
    logger.info("Gold price cache cleared")

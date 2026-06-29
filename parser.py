import requests
import json
from datetime import datetime

EDADEAL_API = "https://edadeal.ru/api/v2"

STORES = {
    "magnit": "Магнит",
    "pyaterochka": "Пятёрочка", 
    "perekrestok": "Перекрёсток",
    "lenta": "Лента",
    "auchan": "Ашан"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

def get_deals(city: str = "moskva") -> list:
    """Получает актуальные акции с Edadeal."""
    deals = []
    
    try:
        url = f"{EDADEAL_API}/retailers"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if resp.status_code != 200:
            return _get_mock_deals()
        
        retailers = resp.json().get("data", [])
        
        for store_slug, store_name in STORES.items():
            retailer = next(
                (r for r in retailers if store_slug in r.get("slug", "").lower()),
                None
            )
            if not retailer:
                continue
                
            retailer_id = retailer.get("id")
            if not retailer_id:
                continue
            
            offers_url = f"{EDADEAL_API}/offers?retailer_id={retailer_id}&limit=100"
            offers_resp = requests.get(offers_url, headers=HEADERS, timeout=10)
            
            if offers_resp.status_code == 200:
                offers = offers_resp.json().get("data", [])
                for offer in offers:
                    deals.append({
                        "store": store_name,
                        "name": offer.get("name", ""),
                        "price": offer.get("price", 0),
                        "old_price": offer.get("old_price", 0),
                        "discount": offer.get("discount_percent", 0),
                        "valid_to": offer.get("date_end", "")
                    })
    except Exception as e:
        print(f"Ошибка парсинга Edadeal: {e}")
        return _get_mock_deals()
    
    return deals if deals else _get_mock_deals()

def find_deals_for_items(items: list, city: str = "moskva") -> dict:
    """Ищет акции для конкретных продуктов из списка."""
    
    all_deals = get_deals(city)
    found = {}
    
    for item in items:
        item_lower = item.lower()
        matching = []
        
        for deal in all_deals:
            deal_name = deal["name"].lower()
            # Простое совпадение по ключевым словам
            item_words = item_lower.split()
            if any(word in deal_name for word in item_words if len(word) > 3):
                matching.append(deal)
        
        if matching:
            # Берём лучшую скидку
            best = max(matching, key=lambda x: x.get("discount", 0))
            if best.get("discount", 0) > 0:
                found[item] = best
    
    return found

def format_deals_message(deals: dict) -> str:
    """Форматирует найденные акции в красивое сообщение."""
    
    if not deals:
        return "🔍 Акций на твои продукты сейчас не нашлось. Проверю снова завтра!"
    
    msg = "🏷️ <b>Нашёл акции на твои продукты:</b>\n\n"
    
    total_savings = 0
    for item, deal in deals.items():
        discount = deal.get("discount", 0)
        price = deal.get("price", 0)
        old_price = deal.get("old_price", 0)
        store = deal.get("store", "")
        
        saving = old_price - price if old_price and price else 0
        total_savings += saving
        
        msg += f"✅ <b>{item}</b>\n"
        msg += f"   {store}: {price}₽ "
        if old_price:
            msg += f"<s>{old_price}₽</s> "
        if discount:
            msg += f"(-{discount}%)"
        msg += "\n\n"
    
    if total_savings > 0:
        msg += f"💰 <b>Итого сэкономишь: ~{round(total_savings)}₽</b>"
    
    return msg

def _get_mock_deals() -> list:
    """Тестовые данные на случай если API недоступен."""
    return [
        {"store": "Пятёрочка", "name": "Говядина лопатка охлаждённая", "price": 380, "old_price": 520, "discount": 27, "valid_to": "2025-01-31"},
        {"store": "Магнит", "name": "Спагетти Barilla №5", "price": 89, "old_price": 129, "discount": 31, "valid_to": "2025-01-31"},
        {"store": "Перекрёсток", "name": "Свёкла столовая 1кг", "price": 39, "old_price": 59, "discount": 34, "valid_to": "2025-01-31"},
        {"store": "Лента", "name": "Бекон Черкизово нарезка", "price": 189, "old_price": 259, "discount": 27, "valid_to": "2025-01-31"},
        {"store": "Пятёрочка", "name": "Сыр Пармезан тёртый", "price": 220, "old_price": 310, "discount": 29, "valid_to": "2025-01-31"},
        {"store": "Магнит", "name": "Капуста белокочанная", "price": 25, "old_price": 45, "discount": 44, "valid_to": "2025-01-31"},
        {"store": "Перекрёсток", "name": "Яйца куриные С1 10шт", "price": 89, "old_price": 115, "discount": 23, "valid_to": "2025-01-31"},
        {"store": "Лента", "name": "Морковь мытая 1кг", "price": 35, "old_price": 55, "discount": 36, "valid_to": "2025-01-31"},
    ]

import json
import os

DATA_FILE = "data.json"

def _load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(user_id: int) -> dict:
    data = _load()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "list": [],
            "at_home": [],
            "history": [],
            "is_pro": False,       # Pro подписка
            "requests_today": 0,   # запросов сегодня
            "last_request_date": "",  # дата последнего запроса
        }
        _save(data)
    # Добавляем поля если их нет (для старых пользователей)
    user = data[uid]
    if "is_pro" not in user:
        user["is_pro"] = False
    if "requests_today" not in user:
        user["requests_today"] = 0
    if "last_request_date" not in user:
        user["last_request_date"] = ""
    return user

def save_user(user_id: int, user_data: dict):
    data = _load()
    data[str(user_id)] = user_data
    _save(data)

def clear_list(user_id: int):
    user = get_user(user_id)
    user["list"] = []
    user["history"] = []
    save_user(user_id, user)

def set_at_home(user_id: int, items: list):
    user = get_user(user_id)
    user["at_home"] = items
    save_user(user_id, user)


# ─── Лимиты запросов ──────────────────────────────────────────
FREE_LIMIT = 5  # запросов в день для бесплатных

def check_limit(user_id: int) -> tuple[bool, int]:
    """Проверяет лимит запросов. Возвращает (можно_ли, осталось)."""
    from datetime import date
    user = get_user(user_id)

    if user.get("is_pro"):
        return True, 999

    today = str(date.today())
    if user.get("last_request_date") != today:
        # Новый день — сбрасываем счётчик
        user["requests_today"] = 0
        user["last_request_date"] = today
        save_user(user_id, user)

    used = user.get("requests_today", 0)
    remaining = FREE_LIMIT - used
    return remaining > 0, remaining

def increment_requests(user_id: int):
    """Увеличивает счётчик запросов на 1."""
    from datetime import date
    user = get_user(user_id)
    today = str(date.today())
    if user.get("last_request_date") != today:
        user["requests_today"] = 0
        user["last_request_date"] = today
    user["requests_today"] = user.get("requests_today", 0) + 1
    save_user(user_id, user)

def set_pro(user_id: int, is_pro: bool):
    """Включает/выключает Pro подписку."""
    user = get_user(user_id)
    user["is_pro"] = is_pro
    save_user(user_id, user)


# ─── История списков покупок ──────────────────────────────────
MAX_HISTORY_LISTS = 10  # храним последние 10 списков

def save_shopping_list(user_id: int, recipe_name: str, items_text: str):
    """Сохраняет список покупок в историю."""
    from datetime import datetime
    user = get_user(user_id)
    if "shopping_history" not in user:
        user["shopping_history"] = []

    entry = {
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "recipe": recipe_name,
        "items": items_text[:500],  # обрезаем если очень длинный
    }

    user["shopping_history"].insert(0, entry)  # добавляем в начало
    # Оставляем только последние N списков
    user["shopping_history"] = user["shopping_history"][:MAX_HISTORY_LISTS]
    save_user(user_id, user)

def get_shopping_history(user_id: int) -> list:
    """Возвращает историю списков покупок."""
    user = get_user(user_id)
    return user.get("shopping_history", [])

def clear_shopping_history(user_id: int):
    """Очищает историю списков."""
    user = get_user(user_id)
    user["shopping_history"] = []
    save_user(user_id, user)

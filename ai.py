import os
import re
from openai import OpenAI
from dotenv import load_dotenv
import recipes as recipe_db

load_dotenv()

client = OpenAI(
    api_key=os.getenv("VSEGPT_API_KEY"),
    base_url="https://api.vsegpt.ru/v1"
)

SYSTEM_PROMPT = """Ты умный помощник по кулинарии и покупкам.

ВАЖНЫЕ ПРАВИЛА ФОРМАТИРОВАНИЯ:
- НЕ используй ### заголовки
- НЕ используй ** жирный текст
- НЕ используй * курсив
- Пиши обычным текстом с эмодзи

Когда пользователь просит составить список — отвечай СТРОГО в таком формате:

✅ Список на X человек:

🥬 Овощи и фрукты:
• продукт — количество

🥩 Мясо и рыба:
• продукт — количество

🧀 Молочные продукты и яйца:
• продукт — количество

🥫 Бакалея:
• продукт — количество

🧴 Соусы и приправы:
• продукт — количество

🔥 Калорийность на 1 порцию:
• Калории: ~XXX ккал
• Белки: ~XXг | Жиры: ~XXг | Углеводы: ~XXг

Если пользователь не сказал что есть дома — спроси об этом коротко."""

def chat(user_id: int, message: str, history: list, at_home: list) -> tuple[str, list]:
    at_home_str = ""
    if at_home:
        at_home_str = f"\n\nУ пользователя дома уже есть: {', '.join(at_home)}. Не включай это в список."

    portions = _extract_portions(message)
    recipe_context = _find_recipes_in_message(message, portions)

    system = SYSTEM_PROMPT + at_home_str
    if recipe_context:
        system += f"\n\nТочные данные из базы рецептов:\n{recipe_context}"

    messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=messages,
        max_tokens=1400,
        temperature=0.5
    )

    reply = response.choices[0].message.content

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        history = history[-20:]

    return reply, history

def get_substitutions(shopping_list: str) -> str:
    prompt = f"""Вот список покупок:
{shopping_list}

Предложи 3-5 дешёвых замен которые сэкономят деньги но не испортят блюда.
Формат:
💰 Замены для экономии:
• [дорогой продукт] → [дешёвая замена] (экономия ~X руб)

В конце напиши примерную общую экономию."""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.5
    )
    return response.choices[0].message.content

def parse_items_from_reply(reply: str) -> list:
    prompt = f"""Из этого текста извлеки только названия продуктов (без количества).
Верни список через запятую, без лишних слов.

Текст:
{reply}"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0
    )
    items_str = response.choices[0].message.content.strip()
    return [i.strip() for i in items_str.split(",") if i.strip()]

def get_recipe_menu() -> str:
    lines = ["📖 <b>Рецепты в моей базе:</b>\n"]
    for cat, emoji in recipe_db.CATEGORIES.items():
        names = recipe_db.get_recipe_list(cat)
        if names:
            lines.append(f"{emoji} <b>{cat.capitalize()}</b>")
            lines.append(", ".join(names))
            lines.append("")
    lines.append("Напиши название блюда и количество человек!")
    return "\n".join(lines)

def suggest_dishes(ingredients: str) -> str:
    """Предлагает 5 блюд из продуктов которые есть дома + калории каждого."""

    prompt = f"""У пользователя дома есть: {ingredients}

Предложи ровно 5 блюд которые можно приготовить из этих продуктов.
Можно использовать базовые продукты которые есть у всех: соль, перец, масло, вода.

Для каждого блюда напиши строго в таком формате:

[эмодзи] <b>Название блюда</b>
🥕 Продукты: список продуктов из наличия
⏱ Время: XX минут
🔥 Калории: ~XXX ккал | Б: XXг | Ж: XXг | У: XXг
👨‍🍳 Как готовить: одно предложение

---

После всех 5 блюд добавь:
💡 <b>Чего не хватает:</b> напиши 2-3 продукта которые расширят меню"""

    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.7
    )
    return response.choices[0].message.content

def _extract_portions(text: str) -> int:
    patterns = [
        r"на\s+(\d+)\s*(человек|чел|персон|порци)",
        r"(\d+)\s*(человек|чел|персон|порци)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return 2

def _find_recipes_in_message(message: str, portions: int) -> str:
    found = []
    msg_lower = message.lower()
    for name in recipe_db.RECIPES:
        if name in msg_lower or any(word in msg_lower for word in name.split() if len(word) > 4):
            recipe = recipe_db.find_recipe(name)
            if recipe:
                found.append(recipe_db.format_recipe_for_prompt(recipe, portions))
    return "\n\n".join(found)

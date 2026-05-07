import os
import json
import sqlite3
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")

DB_PATH = "fitness.db"

WORKOUT_PLAN = {
    0: {  # Monday
        "name": "Грудь 💪",
        "exercises": [
            {"id": "bench_press", "name": "Жим гантелей лёжа", "sets": 4, "reps": "12–15", "weight": 18},
            {"id": "fly", "name": "Разводка на скамье", "sets": 4, "reps": "12–15", "weight": 18},
            {"id": "incline_press", "name": "Жим под углом 30°", "sets": 3, "reps": "12", "weight": 18},
            {"id": "pushup", "name": "Отжимания с паузой (3-1-1)", "sets": 3, "reps": "max", "weight": 0},
            {"id": "jump_rope", "name": "Скакалка (разминка)", "sets": 1, "reps": "10 мин", "weight": 0},
        ]
    },
    1: {  # Tuesday
        "name": "Спина + бицепс 🔙",
        "exercises": [
            {"id": "row_single", "name": "Тяга гантели в наклоне", "sets": 4, "reps": "15 каждой", "weight": 18},
            {"id": "row_both", "name": "Тяга двух гантелей", "sets": 4, "reps": "12", "weight": 18},
            {"id": "curl", "name": "Подъём на бицепс", "sets": 4, "reps": "15", "weight": 18},
            {"id": "hammer", "name": "Молотки", "sets": 3, "reps": "15", "weight": 18},
            {"id": "jump_rope", "name": "Скакалка (разминка)", "sets": 1, "reps": "8 мин", "weight": 0},
        ]
    },
    2: {  # Wednesday — rest
        "name": "Отдых 🧘",
        "exercises": [
            {"id": "stretch", "name": "Растяжка грудь/спина", "sets": 1, "reps": "15 мин", "weight": 0},
            {"id": "walk", "name": "Лёгкая прогулка", "sets": 1, "reps": "30 мин", "weight": 0},
        ]
    },
    3: {  # Thursday
        "name": "Плечи + трицепс 🔥",
        "exercises": [
            {"id": "ohp", "name": "Жим гантелей стоя", "sets": 4, "reps": "15", "weight": 18},
            {"id": "lateral", "name": "Подъём через стороны", "sets": 4, "reps": "15", "weight": 18},
            {"id": "skull", "name": "Французский жим лёжа", "sets": 4, "reps": "15", "weight": 18},
            {"id": "tri_push", "name": "Отжимания на трицепс", "sets": 3, "reps": "max", "weight": 0},
            {"id": "jump_rope", "name": "Скакалка (разминка)", "sets": 1, "reps": "8 мин", "weight": 0},
        ]
    },
    4: {  # Friday
        "name": "Кардио 🏃",
        "exercises": [
            {"id": "rope_intervals", "name": "Скакалка интервалы 40/20", "sets": 12, "reps": "40с", "weight": 0},
            {"id": "rope_double", "name": "Двойные прыжки (попытки)", "sets": 1, "reps": "конец", "weight": 0},
            {"id": "cooldown", "name": "Заминка + растяжка", "sets": 1, "reps": "10 мин", "weight": 0},
        ]
    },
}

WAITING_LOG = "WAITING_LOG"
WAITING_WEIGHT = "WAITING_WEIGHT"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            exercise_id TEXT,
            exercise_name TEXT,
            sets INTEGER,
            reps TEXT,
            weight REAL,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            current_exercise_id TEXT,
            current_exercise_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_today_plan():
    day = date.today().weekday()
    if day >= 5:
        return None
    return WORKOUT_PLAN.get(day)

def get_week_stats(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT exercise_name, SUM(sets), AVG(weight), MAX(weight), COUNT(*)
        FROM logs
        WHERE user_id=? AND date >= date('now', '-7 days')
        GROUP BY exercise_name
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_exercise_history(user_id, exercise_id, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT date, sets, reps, weight FROM logs
        WHERE user_id=? AND exercise_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, exercise_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def save_log(user_id, exercise_id, exercise_name, sets, reps, weight):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (user_id, date, exercise_id, exercise_name, sets, reps, weight, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, str(date.today()), exercise_id, exercise_name, sets, reps, weight, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def set_user_state(user_id, exercise_id, exercise_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO user_state (user_id, current_exercise_id, current_exercise_name)
        VALUES (?, ?, ?)
    """, (user_id, exercise_id, exercise_name))
    conn.commit()
    conn.close()

def get_user_state(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT current_exercise_id, current_exercise_name FROM user_state WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📋 Тренировка сегодня", callback_data="today")],
        [InlineKeyboardButton("📊 Мой прогресс", callback_data="stats")],
        [InlineKeyboardButton("📅 Вся программа", callback_data="program")],
    ]
    await update.message.reply_text(
        "Привет! Я твой фитнес-бот 💪\n\n"
        "Каждый день я показываю тренировку, ты жмёшь *Начать упражнение* и записываешь результат.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "today":
        plan = get_today_plan()
        if not plan:
            await query.edit_message_text("Сегодня выходной 🎉 Отдыхай, восстановление — часть тренинга!")
            return

        text = f"*{plan['name']}*\n\n"
        keyboard = []
        for ex in plan["exercises"]:
            hist = get_exercise_history(user_id, ex["id"], 1)
            hint = ""
            if hist:
                d, s, r, w = hist[0]
                hint = f" (пред: {s}×{r}" + (f"×{int(w)}кг" if w else "") + ")"
            text += f"• {ex['name']} — {ex['sets']}×{ex['reps']}" + (f" / {ex['weight']}кг" if ex['weight'] else "") + hint + "\n"
            keyboard.append([InlineKeyboardButton(
                f"▶ {ex['name']}", callback_data=f"start_ex:{ex['id']}:{ex['name']}"
            )])

        keyboard.append([InlineKeyboardButton("📊 Прогресс", callback_data="stats")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("start_ex:"):
        parts = data.split(":", 2)
        ex_id = parts[1]
        ex_name = parts[2]
        set_user_state(user_id, ex_id, ex_name)

        hist = get_exercise_history(user_id, ex_id, 3)
        hist_text = ""
        if hist:
            hist_text = "\n\n📈 *Последние результаты:*\n"
            for d, s, r, w in hist:
                hist_text += f"  {d}: {s} подх × {r}" + (f" × {int(w)}кг" if w else "") + "\n"

        await query.edit_message_text(
            f"*{ex_name}*\n\nЗапиши результат в формате:\n"
            f"`подходы рпеторения вес`\n\n"
            f"Примеры:\n"
            f"`4 15 18` — 4 подхода по 15 раз, 18 кг\n"
            f"`3 max 0` — 3 подхода до отказа, без веса\n"
            f"`1 10мин 0` — 1 подход, 10 минут"
            + hist_text,
            parse_mode="Markdown"
        )

    elif data == "stats":
        rows = get_week_stats(user_id)
        if not rows:
            await query.edit_message_text("Пока нет данных. Начни первую тренировку! 💪")
            return

        text = "📊 *Прогресс за 7 дней:*\n\n"
        for name, total_sets, avg_w, max_w, count in rows:
            text += f"*{name}*\n"
            text += f"  Подходов: {int(total_sets)} | Ср. вес: {round(avg_w, 1) if avg_w else '—'}кг | Макс: {round(max_w, 1) if max_w else '—'}кг\n\n"

        keyboard = [[InlineKeyboardButton("◀ Назад", callback_data="today")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "program":
        text = "📅 *Программа на неделю:*\n\n"
        days = ["Пн", "Вт", "Ср", "Чт", "Пт"]
        for i, d in enumerate(days):
            plan = WORKOUT_PLAN[i]
            text += f"*{d} — {plan['name']}*\n"
            for ex in plan["exercises"]:
                text += f"  • {ex['name']} {ex['sets']}×{ex['reps']}\n"
            text += "\n"

        keyboard = [[InlineKeyboardButton("◀ Назад", callback_data="today")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    state = get_user_state(user_id)
    if not state:
        await update.message.reply_text("Сначала выбери упражнение через /start → Тренировка сегодня")
        return

    ex_id, ex_name = state
    parts = text.split()

    if len(parts) < 2:
        await update.message.reply_text("Формат: `подходы повторения вес`\nПример: `4 15 18`", parse_mode="Markdown")
        return

    try:
        sets = int(parts[0])
        reps = parts[1]
        weight = float(parts[2]) if len(parts) > 2 else 0.0
    except ValueError:
        await update.message.reply_text("Формат: `подходы повторения вес`\nПример: `4 15 18`", parse_mode="Markdown")
        return

    save_log(user_id, ex_id, ex_name, sets, reps, weight)

    volume = sets * (float(reps) if reps.replace('.','').isdigit() else 0) * weight
    volume_text = f"\nОбъём: *{int(volume)} кг*" if volume > 0 else ""

    hist = get_exercise_history(user_id, ex_id, 2)
    progress_text = ""
    if len(hist) >= 2:
        prev_w = hist[1][3]
        if weight > prev_w:
            progress_text = f"\n🔥 Прогресс! +{round(weight - prev_w, 1)} кг к весу!"
        elif weight == prev_w and sets >= hist[1][1]:
            progress_text = "\n✅ Держишь уровень!"

    keyboard = [[InlineKeyboardButton("◀ К тренировке", callback_data="today")]]
    await update.message.reply_text(
        f"✅ *{ex_name}* записано!\n"
        f"{sets} подх × {reps}" + (f" × {weight}кг" if weight else "") + volume_text + progress_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_log))
    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

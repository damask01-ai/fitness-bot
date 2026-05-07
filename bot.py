import os
import sqlite3
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TOKEN_HERE")
DB_PATH = "fitness.db"

WORKOUT_PLAN = {
    0: {
        "name": "Грудь 💪",
        "exercises": [
            {"id": "jump_rope", "name": "Скакалка (разминка)", "sets": 1, "reps": "10 мин", "weight": 0,
             "gif": "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
             "tip": "Прыгай на носках, локти прижаты к телу, вращение запястьями."},
            {"id": "bench_press", "name": "Жим гантелей лёжа", "sets": 4, "reps": "12-15", "weight": 18,
             "gif": "https://i.imgur.com/1yPxqOI.gif",
             "tip": "Лёжа на скамье. Опускай 3 сек, пауза внизу, взрыв вверх. Лопатки сведены."},
            {"id": "fly", "name": "Разводка на скамье", "sets": 4, "reps": "12-15", "weight": 18,
             "gif": "https://i.imgur.com/xYxAl5o.gif",
             "tip": "Руки слегка согнуты в локтях. Опускай широко, чувствуй растяжку груди."},
            {"id": "incline_press", "name": "Жим под углом 30", "sets": 3, "reps": "12", "weight": 18,
             "gif": "https://i.imgur.com/1yPxqOI.gif",
             "tip": "Скамья под углом 30 градусов. Акцент на верхнюю грудь. Не разводи локти слишком широко."},
            {"id": "pushup", "name": "Отжимания с паузой 3-1-1", "sets": 3, "reps": "max", "weight": 0,
             "gif": "https://i.imgur.com/kH1PXVT.gif",
             "tip": "3 сек вниз, пауза 1 сек, взрыв вверх. Тело прямое как доска."},
        ]
    },
    1: {
        "name": "Спина + бицепс",
        "exercises": [
            {"id": "jump_rope", "name": "Скакалка (разминка)", "sets": 1, "reps": "8 мин", "weight": 0,
             "gif": "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
             "tip": "Прыгай на носках, локти прижаты к телу, вращение запястьями."},
            {"id": "row_single", "name": "Тяга гантели в наклоне", "sets": 4, "reps": "15 каждой", "weight": 18,
             "gif": "https://i.imgur.com/LmFxBWS.gif",
             "tip": "Колено и рука опираются на скамью. Тяни локоть вверх и назад, не разворачивай корпус."},
            {"id": "row_both", "name": "Тяга двух гантелей", "sets": 4, "reps": "12", "weight": 18,
             "gif": "https://i.imgur.com/LmFxBWS.gif",
             "tip": "Наклон 45 градусов, спина прямая. Тяни обе гантели к поясу одновременно."},
            {"id": "curl", "name": "Подъём на бицепс", "sets": 4, "reps": "15", "weight": 18,
             "gif": "https://i.imgur.com/wuqxBCR.gif",
             "tip": "Локти прижаты к корпусу, не качайся. Полная амплитуда - вниз до конца."},
            {"id": "hammer", "name": "Молотки", "sets": 3, "reps": "15", "weight": 18,
             "gif": "https://i.imgur.com/wuqxBCR.gif",
             "tip": "Нейтральный хват (ладони смотрят друг на друга). Качает плечевую мышцу под бицепсом."},
        ]
    },
    2: {
        "name": "Отдых",
        "exercises": [
            {"id": "stretch", "name": "Растяжка грудь и спина", "sets": 1, "reps": "15 мин", "weight": 0,
             "gif": "https://media.giphy.com/media/3o7TKuylFkTuBELGGk/giphy.gif",
             "tip": "Удерживай каждую позицию 30-60 сек. Дыши глубоко, не задерживай дыхание."},
            {"id": "walk", "name": "Легкая прогулка", "sets": 1, "reps": "30 мин", "weight": 0,
             "gif": "https://media.giphy.com/media/3o7TKuylFkTuBELGGk/giphy.gif",
             "tip": "Темп спокойный. Активное восстановление улучшает кровоток в мышцах."},
        ]
    },
    3: {
        "name": "Плечи + трицепс",
        "exercises": [
            {"id": "jump_rope", "name": "Скакалка (разминка)", "sets": 1, "reps": "8 мин", "weight": 0,
             "gif": "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
             "tip": "Прыгай на носках, локти прижаты к телу, вращение запястьями."},
            {"id": "ohp", "name": "Жим гантелей стоя", "sets": 4, "reps": "15", "weight": 18,
             "gif": "https://i.imgur.com/1yPxqOI.gif",
             "tip": "Стоя, ноги на ширине плеч. Жми строго вверх, не отклоняйся назад. Корпус напряжён."},
            {"id": "lateral", "name": "Подъём через стороны", "sets": 4, "reps": "15", "weight": 18,
             "gif": "https://i.imgur.com/xYxAl5o.gif",
             "tip": "Руки чуть согнуты. Поднимай до уровня плеч, не выше. Мизинец чуть выше большого пальца."},
            {"id": "skull", "name": "Французский жим лёжа", "sets": 4, "reps": "15", "weight": 18,
             "gif": "https://i.imgur.com/1yPxqOI.gif",
             "tip": "Лёжа. Опускай гантели к вискам, локти смотрят в потолок, не разводи их в стороны."},
            {"id": "tri_push", "name": "Отжимания на трицепс", "sets": 3, "reps": "max", "weight": 0,
             "gif": "https://i.imgur.com/kH1PXVT.gif",
             "tip": "Узкая постановка рук. Локти идут назад вдоль тела, не в стороны."},
        ]
    },
    4: {
        "name": "Кардио",
        "exercises": [
            {"id": "rope_intervals", "name": "Скакалка интервалы 40/20", "sets": 12, "reps": "40 сек", "weight": 0,
             "gif": "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
             "tip": "40 сек быстро, 20 сек пауза. 12 раундов. В быстрые секунды - максимальный темп!"},
            {"id": "rope_double", "name": "Двойные прыжки", "sets": 1, "reps": "попытки", "weight": 0,
             "gif": "https://media.giphy.com/media/l0HlBO7eyXzSZkJri/giphy.gif",
             "tip": "Прыгни выше обычного и два оборота скакалки за один прыжок. Начни с 5 попыток."},
            {"id": "cooldown", "name": "Заминка и растяжка", "sets": 1, "reps": "10 мин", "weight": 0,
             "gif": "https://media.giphy.com/media/3o7TKuylFkTuBELGGk/giphy.gif",
             "tip": "Плавные движения, глубокое дыхание. Растяни икры, бёдра, плечи."},
        ]
    },
}

def find_exercise(ex_id):
    for day in WORKOUT_PLAN.values():
        for ex in day["exercises"]:
            if ex["id"] == ex_id:
                return ex
    return None

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
        SELECT exercise_name, SUM(sets), AVG(weight), MAX(weight)
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
        [InlineKeyboardButton("Тренировка сегодня", callback_data="today")],
        [InlineKeyboardButton("Мой прогресс", callback_data="stats")],
        [InlineKeyboardButton("Вся программа", callback_data="program")],
    ]
    await update.message.reply_text(
        "Привет! Я твой фитнес-бот\n\n"
        "Каждый день показываю тренировку, ты жмёшь на упражнение и записываешь результат.",
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
            await query.edit_message_text("Сегодня выходной! Отдыхай, восстановление - часть тренинга.")
            return

        text = f"*{plan['name']}*\n\n"
        keyboard = []
        for ex in plan["exercises"]:
            hist = get_exercise_history(user_id, ex["id"], 1)
            hint = ""
            if hist:
                d, s, r, w = hist[0]
                hint = f" (пред: {s}x{r}" + (f" x{int(w)}кг" if w else "") + ")"
            text += f"• {ex['name']} — {ex['sets']}x{ex['reps']}" + (f" / {ex['weight']}кг" if ex['weight'] else "") + hint + "\n"
            keyboard.append([InlineKeyboardButton(
                f"▶ {ex['name']}", callback_data=f"start_ex:{ex['id']}:{ex['name']}"
            )])

        keyboard.append([InlineKeyboardButton("Мой прогресс", callback_data="stats")])
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("start_ex:"):
        parts = data.split(":", 2)
        ex_id = parts[1]
        ex_name = parts[2]
        set_user_state(user_id, ex_id, ex_name)

        ex_data = find_exercise(ex_id)

        hist = get_exercise_history(user_id, ex_id, 3)
        hist_text = ""
        if hist:
            hist_text = "\n\nПоследние результаты:\n"
            for d, s, r, w in hist:
                hist_text += f"  {d}: {s} подх x {r}" + (f" x {int(w)}кг" if w else "") + "\n"

        tip_text = ""
        if ex_data and ex_data.get("tip"):
            tip_text = f"\n\nТехника: {ex_data['tip']}"

        caption = (
            f"{ex_name}"
            + tip_text
            + f"\n\nЗапиши результат:\nподходы повторения вес\n\n"
            f"4 15 18 — 4x15 по 18 кг\n"
            f"3 max 0 — до отказа"
            + hist_text
        )

        if ex_data and ex_data.get("gif"):
            try:
                await query.message.reply_animation(
                    animation=ex_data["gif"],
                    caption=caption
                )
                return
            except Exception:
                pass

        await query.edit_message_text(caption)

    elif data == "stats":
        rows = get_week_stats(user_id)
        if not rows:
            await query.edit_message_text("Пока нет данных. Начни первую тренировку!")
            return

        text = "Прогресс за 7 дней:\n\n"
        for name, total_sets, avg_w, max_w in rows:
            text += f"{name}\n"
            text += f"  Подходов: {int(total_sets)} | Ср. вес: {round(avg_w, 1) if avg_w else '-'}кг | Макс: {round(max_w, 1) if max_w else '-'}кг\n\n"

        keyboard = [[InlineKeyboardButton("Назад", callback_data="today")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "program":
        text = "Программа на неделю:\n\n"
        days = ["Пн", "Вт", "Ср", "Чт", "Пт"]
        for i, d in enumerate(days):
            plan = WORKOUT_PLAN[i]
            text += f"{d} — {plan['name']}\n"
            for ex in plan["exercises"]:
                text += f"  • {ex['name']} {ex['sets']}x{ex['reps']}\n"
            text += "\n"

        keyboard = [[InlineKeyboardButton("Назад", callback_data="today")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    state = get_user_state(user_id)
    if not state:
        await update.message.reply_text("Сначала выбери упражнение через /start")
        return

    ex_id, ex_name = state
    parts = text.split()

    if len(parts) < 2:
        await update.message.reply_text("Формат: подходы повторения вес\nПример: 4 15 18")
        return

    try:
        sets = int(parts[0])
        reps = parts[1]
        weight = float(parts[2]) if len(parts) > 2 else 0.0
    except ValueError:
        await update.message.reply_text("Формат: подходы повторения вес\nПример: 4 15 18")
        return

    save_log(user_id, ex_id, ex_name, sets, reps, weight)

    volume = sets * (float(reps) if reps.replace('.','').isdigit() else 0) * weight
    volume_text = f"\nОбъём: {int(volume)} кг" if volume > 0 else ""

    hist = get_exercise_history(user_id, ex_id, 2)
    progress_text = ""
    if len(hist) >= 2:
        prev_w = hist[1][3]
        if weight > prev_w:
            progress_text = f"\nПрогресс! +{round(weight - prev_w, 1)} кг к весу!"
        elif weight == prev_w and sets >= hist[1][1]:
            progress_text = "\nДержишь уровень!"

    keyboard = [[InlineKeyboardButton("К тренировке", callback_data="today")]]
    await update.message.reply_text(
        f"{ex_name} записано!\n"
        f"{sets} подх x {reps}" + (f" x {weight}кг" if weight else "") + volume_text + progress_text,
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

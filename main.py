import os
import logging
import asyncio
import asyncpg
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Optional

# Импорты для FSM
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import WebAppInfo, CallbackQuery
import asyncio
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
# -------------------- 1. НАСТРОЙКА ЛОГИРОВАНИЯ --------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------- 2. НАСТРОЙКА И КОНСТАНТЫ --------------------
load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://mini-app-mauve-alpha.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    app.state.db = await asyncpg.create_pool(POSTGRES_DSN)
    print("✅ Database connected")

@app.get("/api/files")
async def get_files(request: Request):
    async with app.state.db.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, file_name, file_id FROM materials ORDER BY created_at DESC LIMIT 50"
        )

    files = []
    for row in rows:
        file_id = row["file_id"]
        name = row["file_name"] or "Без названия"
        try:
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}")
            data = r.json()
            if "result" not in data:
                continue
            file_path = data["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            files.append({"name": name, "url": download_url})
        except Exception as e:
            print(f"Ошибка получения file_path: {e}")

    return files



BOT_TOKEN = os.getenv("BOT_TOKEN")

# АДМИНИСТРАТОРЫ
ADMIN_IDS = [6720999592, 6520890849]
POSTGRES_DSN = "postgresql://ramiz:unppr78026@amvera-ramizortiqov-cnpg-medekzamendb-rw:5432/bot_database"
# КАНАЛ ДЛЯ ПРОВЕРКИ ПОДПИСКИ
CHANNEL_ID = -1002034189536
CHANNEL_URL = "https://t.me/fr_ray7"
FEEDBACK_USERNAME_URL = "https://t.me/parviz_medik"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в .env")

# Инициализация бота с хранилищем
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Константы для групп и курсов
GROUPS = {"ru": "🇷🇺 Русский", "tj": "🇹🇯 Таджикский"}
COURSES = [1, 2, 3, 4, 5, 6]
MAX_COURSE_FOR_SUMMARY = 3 # Константа для ограничения "Итога"

# Предметы для Экзамена
ALL_SUBJECTS_MAP = {
    # 1-й КУРС
    "chem1": "🧪 Химия",
    "bio1": "🧬 Биология",
    "anat1": "💀 Анатомия",
    "phys1": "⚛️ Физика",
    
    # 2-й КУРС
    "anat2": "💀 Анатомия (2)",
    "gisto2": "🔬 Гистология",
    "phys2": "🏃 Физиология",
    "biohim2": "🧪 Биохимия",

    # 3-й КУРС
    "microb3": "🦠 Микроб",
    "patfiz3": "🤢 Патфиз",
    "topanat3": "🧠 Топанатомия",
    "farmak3": "💊 Фармак",
    "hirurgia3": "🔪 Хирургия",
    "generalhygiene3": "🧼 Общая гигиена",
    "dentistry3": "🦷 Стоматология",
    "propv3": "👴 Пропедевтика взр",
    "propd3": "👶 Пропедевтика детск",
    
    # 4-й КУРC
    "dermatovenereology4": "🔬 Дерматовенерология",
    "pediatrics4": "👶 Педиатрия", 
    "topanatomy4": "🗺️ Топографическая анатомия",
    "generalhygiene4": "🧼 Общая гигиена",
    "radiology4": "📡 Рентгенология",
    "internalmed4": "🫀 Внутренние болезни",
    "occupationalpath4": "🏭 Профессиональная патология",
    "neurology4": "🧠 Неврология",
    "obstetrics4": "🤰 Акушерство",
    "surgicaldiseases4": "🔪 Хирургические болезни", 
    "socialhygiene4": "🏥 Социальная гигиена",
    "endocrinology4": "🦋 Эндокринология",
    "ent4": "👂 Оториноларингология",
    "militarytest4": "🎖️ Военный тест",
    
    # 5-й КУРC
    "familymed5": "👨‍👩‍👧‍👦 Семейная медицина",
    "vascularsurg5": "🩸 Сосудистая хирургия", 
    "internal5": "🫀 Внутренние болезни",
    "traumatology5": "🦴 Травматология",
    "epidemiology5": "📊 Эпидемиология",
    "gynecology5": "🌸 Гинекология",
    "socialhygiene5": "🏥 Социальная гигиена",
    "phthisiology5": "🫁 Фтизиатрия",
    "psychiatry5": "🧠 Психиатрия",
    "urology5": "💧 Урология", 
    "politology5": "🏛️ Политология",
    "pediatricsurg5": "👶 Детская хирургия",
    "ophthalmology5": "👁️ Офтальмология",
    "anesthesiology5": "💤 Анестезиология",
    "pediatrics5": "👶 Педиатрия",

    # 6-й КУРC
    "combtrauma6": "🩺 Сочетанные травмы",
    "transplant6": "🧬 Трансплантология",
    "obstetrics6": "🤰 Акушерство",
    "internal6": "🫀 Внутренние болезни",
    "econtheory6": "📊 Экономическая теория",
    "childinfect6": "🌡️ Детские инфекционные болезни",
    "pediatrics6": "👶 Педиатрия",
    "surgery6": "🔪 Хирургия",
    "stateexam6": "📝 Государственный экзамен",
    "neurosurgery6": "🧠 Нейрохирургия",
    "familymed6": "👨‍👩‍👧‍👦 Семейная медицина",
    "infectious6": "🦠 Инфекционные болезни",
    "militarymed6": "🎖️ Военно-полевая терапия",
    "clinicalpharm6": "💊 Клиническая фармакология",
    "oncology6": "🎗️ Онкология",
    "exercisether6": "🏃‍♂️ Лечебная физкультура",
    "forensic6": "🔍 Судебная медицина"
 
    
}
MATERIALS_SUBJECTS_MAP = {
    "matchem1": "🧪 Химия",
    "matbio1": "🧬 Биология",
    "matanat1": "💀 Анатомия",
    "matphys1": "⚛️ Физика",
    
    # 2-й КУРС
    "matanat2": "💀 Анатомия (2)",
    "matgisto2": "🔬 Гистология",
    "matphys2": "🏃 Физиология",
    "matbiohim2": "🧪 Биохимия",

    # 3-й КУРС
    "matmicrob3": "🦠 Микроб",
    "matpatfiz3": "🤢 Патфиз",
    "mattopanat3": "🧠 Топанатомия",
    "matfarmak3": "💊 Фармак",
    "mathirurgia3": "🔪 Хирургия",
    "matdentistry3": "🦷 Стоматология",\
    "matgeneralhygiene3": "🧼 Общая гигиена",
    "matpropv3": "👴 Пропедевтика взр",
    "matpropd3": "👶 Пропедевтика детск",
    
    # 4-й КУРC
    "matdermatovenereology4": "🔬 Дерматовенерология",
    "matpediatrics4": "👶 Педиатрия", 
    "mattopanatomy4": "🗺️ Топографическая анатомия",
    "matgeneralhygiene4": "🧼 Общая гигиена",
    "matradiology4": "📡 Рентгенология",
    "matinternalmed4": "🫀 Внутренние болезни",
    "matoccupationalpath4": "🏭 Профессиональная патология",
    "matneurology4": "🧠 Неврология",
    "matobstetrics4": "🤰 Акушерство",
    "matsurgicaldiseases4": "🔪 Хирургические болезни", 
    "matsocialhygiene4": "🏥 Социальная гигиена",
    "matendocrinology4": "🦋 Эндокринология",
    "matent4": "👂 Оториноларингология",
    "matmilitarytest14": "🎖️ Военный тест 1 семестр",
    "matmilitarytest24": "🎖️ Военный тест 2 семестр",
    
    # 5-й КУРC
    "matfamilymed5": "👨‍👩‍👧‍👦 Семейная медицина",
    "matvascularsurg5": "🩸 Сосудистая хирургия", 
    "matinternal5": "🫀 Внутренние болезни",
    "mattraumatology5": "🦴 Травматология",
    "matepidemiology5": "📊 Эпидемиология",
    "matgynecology5": "🌸 Гинекология",
    "matsocialhygiene5": "🏥 Социальная гигиена",
    "matphthisiology5": "🫁 Фтизиатрия",
    "matpsychiatry5": "🧠 Психиатрия",
    "maturology5": "💧 Урология", 
    "matpolitology5": "🏛️ Политология",
    "matpediatricsurg5": "👶 Детская хирургия",
    "matophthalmology5": "👁️ Офтальмология",
    "matanesthesiology5": "💤 Анестезиология",
    "matpediatrics5": "👶 Педиатрия",

    # 6-й КУРC
    "matcombtrauma6": "🩺 Сочетанные травмы",
    "mattransplant6": "🧬 Трансплантология",
    "matobstetrics6": "🤰 Акушерство",
    "matinternal6": "🫀 Внутренние болезни",
    "matecontheory6": "📊 Экономическая теория",
    "matchildinfect6": "🌡️ Детские инфекционные болезни",
    "matpediatrics6": "👶 Педиатрия",
    "matsurgery6": "🔪 Хирургия",
    "matstateexam6": "📝 Государственный экзамен",
    "matneurosurgery6": "🧠 Нейрохирургия",
    "matfamilymed6": "👨‍👩‍👧‍👦 Семейная медицина",
    "matinfectious6": "🦠 Инфекционные болезни",
    "matmilitarymed6": "🎖️ Военно-полевая терапия",
    "matclinicalpharm6": "💊 Клиническая фармакология",
    "matoncology6": "🎗️ Онкология",
    "matexercisether6": "🏃‍♂️ Лечебная физкультура",
    "matforensic6": "🔍 Судебная медицина"
}
# Теги, которые будут отображаться в меню предметов для каждого курса
COURSE_SUBJECTS = {
    1: ["chem1", "bio1", "anat1", "phys1"],
    2: ["anat2", "gisto2", "phys2", "biohim2"],
    3: ["microb3", "patfiz3", "topanat3", "farmak3", "hirurgia3", "dentistry3","generalhygiene3", "propv3", "propd3"],
    4: ["dermatovenereology4", "pediatrics4", "topanatomy4", "generalhygiene4", "radiology4", "internalmed4", "occupationalpath4", "neurology4", "obstetrics4", "surgicaldiseases4", "socialhygiene4", "endocrinology4", "ent4", "militarytest14", "militarytest24"],
    5: ["familymed5", "vascularsurg5", "internal5", "traumatology5", "epidemiology5", "gynecology5", "socialhygiene5", "phthisiology5", "psychiatry5", "urology5", "politology5", "pediatricsurg5", "ophthalmology5", "anesthesiology5", "pediatrics5"],
    6: ["combtrauma6", "transplant6", "obstetrics6", "internal6", "econtheory6", "childinfect6", "pediatrics6", "surgery6", "stateexam6", "neurosurgery6", "familymed6", "infectious6", "militarymed6", "clinicalpharm6", "oncology6", "exercisether6", "forensic6"],
}

MATERIALS_COURSE_SUBJECTS = {
    1: ["matchem1", "matbio1", "matanat1", "matphys1"],
    2: ["matanat2", "matgisto2", "matphys2", "matbiohim2"],
    3: ["matmicrob3", "matpatfiz3", "mattopanat3", "matfarmak3", "mathirurgia3","matdentistry3", "matgeneralhygiene3", "matpropv3", "matpropd3"],
    4: ["matdermatovenereology4", "matpediatrics4", "mattopanatomy4", "matgeneralhygiene4", "matradiology4", "matinternalmed4", "matoccupationalpath4", "matneurology4", "matobstetrics4", "matsurgicaldiseases4", "matsocialhygiene4", "matendocrinology4", "matent4", "matmilitarytest14", "matmilitarytest24"],
    5: ["matfamilymed5", "matvascularsurg5", "matinternal5", "mattraumatology5", "matepidemiology5", "matgynecology5", "matsocialhygiene5", "matphthisiology5", "matpsychiatry5", "maturology5", "matpolitology5", "matpediatricsurg5", "matophthalmology5", "matanesthesiology5", "matpediatrics5"],
    6: ["matcombtrauma6", "mattransplant6", "matobstetrics6", "matinternal6", "matecontheory6", "matchildinfect6", "matpediatrics6", "matsurgery6", "matstateexam6", "matneurosurgery6", "matfamilymed6", "matinfectious6", "matmilitarymed6", "matclinicalpharm6", "matoncology6", "matexercisether6", "matforensic6"],
}

MATERIAL_TYPES = {
    "lecture": "📖 Лекции+темплан",
    "practice": "🔬 Практика",
    "video": "🎥 Видео"
}

# --- СПИСОК ВСЕХ ТЕГОВ ДЛЯ АДМИНА ---
ALL_ADMIN_TAGS = []
for course in range(1, MAX_COURSE_FOR_SUMMARY + 1):
    for i in range(1, 5):
        tag = f"summary{course}.{i}"
        ALL_ADMIN_TAGS.append(tag)

# Добавляем теги для экзаменов (предметы)
for tag in ALL_SUBJECTS_MAP.keys():
    if tag not in ALL_ADMIN_TAGS:
        ALL_ADMIN_TAGS.append(tag)

# Добавляем теги для материалов (тип_предмет)
for material_type in MATERIAL_TYPES.keys():
    for subject_tag in ALL_SUBJECTS_MAP.keys():
        combined_tag = f"{material_type}_{subject_tag}"
        if combined_tag not in ALL_ADMIN_TAGS:
            ALL_ADMIN_TAGS.append(combined_tag)

# -------------------- 3. БАЗА ДАННЫХ (PostgreSQL) --------------------

class PostgresDB:
    """Класс для работы с PostgreSQL через asyncpg."""
    def __init__(self):
        self.pool = None

    async def init_pool(self):
        """Инициализирует пул подключений к PostgreSQL."""
        try:
            self.pool = await asyncpg.create_pool(POSTGRES_DSN)
            logger.info("PostgreSQL pool initialized successfully.")
            await self._init_db_schema()
        except Exception as e:
            logger.error(f"FATAL: Не удалось подключиться к PostgreSQL. Ошибка: {e}")
            raise

    async def _init_db_schema(self):
        """Создает таблицы, если они не существуют."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    course INTEGER,
                    group_lang TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS materials (
                    id SERIAL PRIMARY KEY,
                    tag TEXT NOT NULL,
                    type TEXT NOT NULL,
                    file_id TEXT,
                    file_name TEXT,
                    caption TEXT,
                    course INTEGER,
                    group_lang TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_materials_tag ON materials (tag);
                CREATE INDEX IF NOT EXISTS idx_materials_course_group ON materials (course, group_lang);
            ''')
            logger.info("PostgreSQL schema initialized/checked.")

    async def get_user(self, user_id: int):
        """Получает пользователя."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)

    async def save_user(self, user_id: int, username: str, full_name: str, course: int, group_lang: str):
        """Сохраняет или обновляет пользователя."""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, full_name, course, group_lang)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username, full_name = EXCLUDED.full_name,
                course = EXCLUDED.course, group_lang = EXCLUDED.group_lang
            ''', user_id, username, full_name, course, group_lang)

    async def get_materials_by_tag(self, tag: str):
        """Получает материалы по тегу."""
        async with self.pool.acquire() as conn:
            return await conn.fetch('SELECT * FROM materials WHERE tag = $1 ORDER BY created_at', tag)

    async def save_material(self, tag: str, type_: str, file_id: str = None, file_name: str = None,
                             caption: str = None, course: int = None, group_lang: str = None):
        """Сохраняет материал."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO materials (tag, type, file_id, file_name, caption, course, group_lang)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            ''', tag, type_, file_id, file_name, caption, course, group_lang)

    async def delete_material(self, material_id: int):
        """Удаляет материал по ID."""
        async with self.pool.acquire() as conn:
            result = await conn.execute('DELETE FROM materials WHERE id = $1', material_id)
            return int(result.split()[-1])
            
    async def get_all_materials(self):
        """Получает все материалы для админ-статистики."""
        async with self.pool.acquire() as conn:
            return await conn.fetch('SELECT * FROM materials ORDER BY tag, course, group_lang')
    #PUBLIC
    async def get_users_for_broadcast(self, course: int, group_lang: str):
        """Получает список user_id, соответствующих курсу и группе."""
        # Если курс равен 0, то игнорируем фильтр по курсу
        course_query = "course = $1" if course != 0 else "TRUE"
        
        # Если group_lang равен 'all', то игнорируем фильтр по группе
        group_query = "group_lang = $2" if group_lang != 'all' else "TRUE"
        
        query = f"SELECT user_id FROM users WHERE {course_query} AND {group_query}"
        
        args = []
        if course != 0:
            args.append(course)
        if group_lang != 'all':
            args.append(group_lang)
            
        async with self.pool.acquire() as conn:
            # fetchval не подходит, нам нужен список
            result = await conn.fetch(query, *args)
            return [row['user_id'] for row in result]
            
db = PostgresDB()

# -------------------- 4. FSM СОСТОЯНИЯ --------------------
class RegistrationStates(StatesGroup):
    waiting_for_course = State()
    waiting_for_group = State()
    waiting_for_confirmation = State()

class AdminStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_index_to_delete = State()
    waiting_for_exam_course = State()
    waiting_for_admin_group = State()
    waiting_for_summary_course = State()

    waiting_for_broadcast_filter = State()
    waiting_for_broadcast_course = State()
    waiting_for_broadcast_content = State()
    
    waiting_for_materials_course = State()
    waiting_for_materials_subject = State()
    
class FeedbackStates(StatesGroup):
    waiting_for_feedback_message = State()

class AdminReplyStates(StatesGroup):
    waiting_for_reply_message = State()# <--- Тут будет приниматься ЛЮБОЙ контент
    
class MaterialsStates(StatesGroup):
    """Состояния для обычных пользователей в разделе материалов"""
    waiting_for_material_type = State()
    waiting_for_subject = State()
# -------------------- 5. СЕРВИСНЫЕ ФУНКЦИИ --------------------

def get_subscription_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔔 Подписка", url=CHANNEL_URL)
    builder.button(text="✅ Проверить", callback_data="check_subscription")
    builder.adjust(2)
    return builder.as_markup()

def get_no_access_message() -> str:
    return f"🚫 **Доступ ограничен.** Для использования бота, пожалуйста, **подпишитесь** на наш канал."

async def check_subscription(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
        
    try:
        member = await bot.get_chat_member(chat_id=str(CHANNEL_ID), user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка при проверке подписки для user_id {user_id}: {e}")
        return False

def clean_tags(text: str, tag: str) -> str:
    if not text:
        return ""
    cleaned_text = text.replace(f"#{tag}", "").replace(f"#{tag.upper()}", "")
    cleaned_text = ' '.join(cleaned_text.split())
    return cleaned_text

# -------------------- 6. КЛАВИАТУРЫ --------------------
def get_reply_main_menu_keyboard(user_course: int = None, user_id: int = None):
    builder = ReplyKeyboardBuilder()
    
    is_admin = user_id in ADMIN_IDS if user_id else False
    
    if user_course:
        builder.button(text="📚 Экзамен")
        builder.button(text="📂 Материалы")
        
        if user_course <= MAX_COURSE_FOR_SUMMARY or is_admin:
            builder.button(text="📋 Итог")
    
    builder.button(text="🚪 Личный кабинет")
    builder.button(text="✉️ Обратная связь")
    
    if (user_course and user_course <= MAX_COURSE_FOR_SUMMARY) or is_admin:
        builder.adjust(3, 2)
    elif user_course:
        builder.adjust(2, 2, 1)
    else:
        builder.adjust(2, 1)
        
    return builder.as_markup(resize_keyboard=True)

def get_course_selection_keyboard():
    builder = ReplyKeyboardBuilder()
    for course in COURSES:
        builder.button(text=f"{course}-курс")
    builder.adjust(3, 3)
    return builder.as_markup(resize_keyboard=True)

def get_group_selection_keyboard():
    builder = ReplyKeyboardBuilder()
    for key, value in GROUPS.items():
        builder.button(text=value)
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# --- КЛАВИАТУРА ДЛЯ ПОДТВЕРЖДЕНИЯ РЕГИСТРАЦИИ ---
def get_confirmation_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="✅ Подтвердить выбор")
    builder.button(text="🔙 Назад к выбору курса")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)
# -----------------------------------------------

# --- КЛАВИАТУРА ДЛЯ ВЫБОРА КУРСА ЭКЗАМЕНА ---
def get_reply_exam_course_keyboard(user_course: int):
    builder = ReplyKeyboardBuilder()
    
    for course in range(1, user_course + 1):
        builder.button(text=f"{course}-й курс")
    
    builder.button(text="🔙 Главное меню")
    builder.adjust(3, 3, 1)
    return builder.as_markup(resize_keyboard=True)

# --- НОВАЯ КЛАВИАТУРА ДЛЯ ПРЕДМЕТОВ ЭКЗАМЕНА ---
def get_reply_exam_subject_keyboard(course_num: int, user_id: int):
    builder = ReplyKeyboardBuilder()
    
    is_admin = user_id in ADMIN_IDS
    
    subjects = COURSE_SUBJECTS.get(course_num, [])
    
    for tag in subjects:
        name = ALL_SUBJECTS_MAP.get(tag, tag)
        builder.button(text=name)
    
    # if is_admin:
    #     builder.button(text=f"🔙 К выбору курса")
    #     builder.button(text=f"🔙 Главное меню")
    #     if len(subjects) > 4:
    #         builder.adjust(3, 3, 3)
    #     else:
    #          builder.adjust(2, 2, 2)
    # else:
    #     builder.button(text=f"🔙 Главное меню")
        
    #     if len(subjects) <= 4:
    #         builder.adjust(2, 2, 1)
    #     else:
    #         builder.adjust(3, 3, 1)
    if is_admin:
        builder.button(text=f"🔙 К выбору курса")
        builder.button(text=f"🔙 Главное меню")
    else:
        builder.button(text=f"🔙 Главное меню")
    
    # ИЗМЕНЕНИЕ: Все предметы по 2 в ряд, затем кнопки навигации
    num_subjects = len(subjects)
    
    if is_admin:
        # Предметы по 2, потом 2 кнопки навигации
        builder.adjust(*([2] * ((num_subjects + 1) // 2)), 2)
    else:
        # Предметы по 2, потом 1 кнопка навигации
        builder.adjust(*([2] * ((num_subjects + 1) // 2)), 1)
        
        
    return builder.as_markup(resize_keyboard=True)

def get_reply_materials_menu_keyboard():
    builder = ReplyKeyboardBuilder()
    for material_name in MATERIAL_TYPES.values():
        builder.button(text=material_name)
    builder.button(text="🔙 Главное меню")
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)

def get_reply_summary_course_keyboard(user_course: int):
    builder = ReplyKeyboardBuilder()
    
    max_visible_course = min(MAX_COURSE_FOR_SUMMARY, user_course)
    
    if user_course in ADMIN_IDS:
           max_visible_course = MAX_COURSE_FOR_SUMMARY
    
    for course in range(1, max_visible_course + 1):
        builder.button(text=f"Итог - {course} курс")
    
    builder.button(text="🔙 Главное меню")
    builder.adjust(3, 1)
    return builder.as_markup(resize_keyboard=True)

def get_reply_final_summary_keyboard(course_num: int):
    builder = ReplyKeyboardBuilder()
    for i in range(1, 5):
        builder.button(text=f"Итог {course_num}.{i}")
    
    builder.button(text="🔙 Главное меню")
    builder.adjust(4, 1)
    return builder.as_markup(resize_keyboard=True)

# --- КЛАВИАТУРА ДЛЯ ВЫБОРА КУРСА МАТЕРИАЛОВ ---
def get_reply_materials_course_keyboard(user_course: int):
    builder = ReplyKeyboardBuilder()
    
    for course in range(1, user_course + 1):
        builder.button(text=f"{course}-й курс")
    
    builder.button(text="🔙 К типам материалов")
    builder.button(text="🔙 Главное меню")
    builder.adjust(3, 3, 2)
    return builder.as_markup(resize_keyboard=True)

# --- КЛАВИАТУРА ДЛЯ ПРЕДМЕТОВ МАТЕРИАЛОВ ---
def get_reply_materials_subject_keyboard(course_num: int, material_type: str, user_id: int):
    builder = ReplyKeyboardBuilder()
    
    is_admin = user_id in ADMIN_IDS
    
    subjects = MATERIALS_COURSE_SUBJECTS.get(course_num, [])
    
    for tag in subjects:
        name = MATERIALS_SUBJECTS_MAP.get(tag, tag)
        builder.button(text=name)
        
    builder.button(text="🔙 К типам материалов")
    
    if is_admin:
        builder.button(text=f"🔙 К выбору курса (Материалы)")
        builder.button(text=f"🔙 Главное меню")
    else:
        builder.button(text=f"🔙 Главное меню")
    
    # Предметы по 2 в ряд
    num_subjects = len(subjects)
    
    if is_admin:
        builder.adjust(*([2] * ((num_subjects + 1) // 2)), 2)
    else:
        builder.adjust(*([2] * ((num_subjects + 1) // 2)), 2)
        
    return builder.as_markup(resize_keyboard=True)

def get_admin_menu(tag: str) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"➕ Загрузить в #{tag}", callback_data=f"upload__{tag}")
    builder.button(text=f"🗑️ Удалить из #{tag}", callback_data=f"delete_indexed__{tag}")
    builder.adjust(1)
    return builder.as_markup()
    
def get_admin_all_tags_menu() -> types.InlineKeyboardMarkup:
    """Генерирует инлайн-клавиатуру со всеми возможными тегами для выбора админ-действий."""
    builder = InlineKeyboardBuilder()
    
    sorted_tags = sorted(ALL_ADMIN_TAGS)
    
    for tag in sorted_tags:
        builder.button(text=f"#{tag}", callback_data=f"select_admin_tag__{tag}")
        
    builder.adjust(4)
    return builder.as_markup()

# -------------------- 7. ОТПРАВКА КОНТЕНТА --------------------
async def send_content_by_tag(chat_id: int, tag: str, course_filter_value: int = None, user_group: str = None):
    """
    Отправляет контент по тегу.
    course_filter_value используется как строгий фильтр, если пользователь не админ.
    """
    logger.info(f"Sending content for tag #{tag} to chat_id {chat_id}, course_filter {course_filter_value}, group {user_group}")
    materials = await db.get_materials_by_tag(tag)
    

    is_admin = chat_id in ADMIN_IDS
    BOT_SIGNATURE = "\n@MedEkzamenBot"

    if not materials:
        await bot.send_message(chat_id, f"❌ Материалы не найдены.", parse_mode="HTML")
        return

    filtered_materials = []
    for material in materials:
        mat_id = material['id']
        mat_tag = material['tag']
        mat_type = material['type']
        file_id = material['file_id']
        file_name = material['file_name']
        caption = material['caption']
        mat_course = material['course']
        mat_group = material['group_lang']
        created_at = material['created_at']
        
        course_match = True
        
        if not is_admin:
            if mat_course is not None and mat_course != course_filter_value:
                course_match = False
        else:
            pass

        group_match = (mat_group is None or mat_group == user_group)

        if course_match and group_match:
            filtered_materials.append(material)

    if not filtered_materials:
        await bot.send_message(chat_id, f"❌ Нет доступных материалов по тегу **#{tag}** для вашего курса и группы.", parse_mode="Markdown")
        return

    # ИЗМЕНЕНО: Используем HTML для всех ответов, чтобы избежать ошибок парсинга
    await bot.send_message(chat_id, f"📦 <b>Материалы по запросу ({len(filtered_materials)} шт.):</b>", parse_mode="HTML")

    for material in filtered_materials:
        mat_type = material['type']
        file_id = material['file_id']
        file_name = material['file_name']
        caption = material['caption']
        mat_course = material['course']
        mat_group = material['group_lang']

        caption = clean_tags(caption or "", tag) if caption else ""
        
        final_caption = ""
        # УДАЛЕНО: if file_name and mat_type != "text": final_caption += f"📄 <b>{file_name}</b>\n\n"
            
        if caption:
            final_caption += caption
        # УДАЛЕНО: Логика добавления filter_info (фильтры)
        if mat_type != "text":
            final_caption += BOT_SIGNATURE
        try:
            if mat_type == "text":
                await bot.send_message(chat_id, final_caption, parse_mode="HTML")
            elif mat_type == "photo" and file_id:
                await bot.send_photo(chat_id, file_id, caption=final_caption, parse_mode="HTML")
            elif mat_type == "video" and file_id:
                await bot.send_video(chat_id, file_id, caption=final_caption, parse_mode="HTML")
            elif mat_type == "document" and file_id:
                await bot.send_document(chat_id, file_id, caption=final_caption, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка отправки контента {mat_type} для тега #{tag}: {e}")
            await bot.send_message(chat_id, "⚠️ Произошла внутренняя ошибка при отправке файла.")

    await bot.send_message(chat_id, "✅ Все доступные материалы отправлены.")

# -------------------- 8. ОБРАБОТЧИКИ РЕГИСТРАЦИИ --------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"User {user_id} started the bot")
    
    if not await check_subscription(user_id):
        await message.answer(get_no_access_message(), reply_markup=get_subscription_keyboard(), parse_mode="Markdown")
        return

    # Проверяем, зарегистрирован ли пользователь
    user_data = await db.get_user(user_id)
    
    # --- Административный доступ ---
    if user_id in ADMIN_IDS:
        await state.clear()
        
        max_course = max(COURSES)
        
        if not user_data:
            await db.save_user(
                user_id=user_id,
                username=message.from_user.username or 'NoUsername',
                full_name=message.from_user.full_name,
                course=max_course,
                group_lang="ru"
            )
            user_course = max_course
        else:
            user_course = user_data['course']
            
        await message.answer(
            f"👑 <b>Админ-меню.</b>",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id),
            parse_mode="HTML"
        )
        return
    # -----------------------------

    if user_data:
        user_course = user_data['course']
        await message.answer(
            f"✅ С возвращением! Вы учитесь на {user_course}-м курсе.\nВыберите раздел:",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id)
        )
    else:
        # Начинаем процесс регистрации
        await message.answer(
            "🎓 <b>Добро пожаловать!</b>\n\n"
            "Для персонализации материалов, пожалуйста, укажите ваш курс:",
            reply_markup=get_course_selection_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(RegistrationStates.waiting_for_course)

@dp.message(RegistrationStates.waiting_for_course)
async def process_course_selection(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, выберите курс используя кнопки ниже:")
        return

    try:
        course = int(message.text.split("-")[0])
        if course not in COURSES:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, выберите корректный курс используя кнопки:")
        return

    # Сохраняем курс и переходим к выбору группы
    await state.update_data(course=course)
    
    await message.answer(
        "📝 Теперь выберите вашу группу:",
        reply_markup=get_group_selection_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_for_group)

@dp.message(RegistrationStates.waiting_for_group)
async def process_group_selection(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, выберите группу используя кнопки ниже:")
        return

    group_lang = None
    for key, value in GROUPS.items():
        if message.text == value:
            group_lang = key
            break

    if not group_lang:
        await message.answer("Пожалуйста, выберите группу используя кнопки ниже:")
        return

    data = await state.get_data()
    course = data.get('course')
    
    # Сохраняем группу и переходим к подтверждению
    await state.update_data(group_lang=group_lang)
    
    await message.answer(
        f"⚠️ <b>Прежде чем сделать выбор — важное условие!</b>\n\n"
        f"Вы выбрали:\n"
        f"• Курс: <b>{course}-й</b>\n"
        f"• Группа: <b>{GROUPS[group_lang]}</b>\n\n"
        f"Ваше решение будет <b>окончательным</b>. После подтверждения курс <b>нельзя будет изменить</b>.\n\n"
        f"Пожалуйста, подойдите к выбору осознанно.",
        reply_markup=get_confirmation_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_confirmation)

@dp.message(RegistrationStates.waiting_for_confirmation)
async def process_confirmation(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == "✅ Подтвердить выбор":
        data = await state.get_data()
        course = data.get('course')
        group_lang = data.get('group_lang')
        
        # Финальное сохранение пользователя в базу
        await db.save_user(
            user_id=user_id,
            username=message.from_user.username or 'NoUsername',
            full_name=message.from_user.full_name,
            course=course,
            group_lang=group_lang
        )
        
        await message.answer(
            f"✅ <b>Регистрация завершена!</b>\n\n"
            f"Теперь вам доступны материалы для вашего курса.",
            reply_markup=get_reply_main_menu_keyboard(course, user_id),
            parse_mode="HTML"
        )
        await state.clear()
        
    elif message.text == "🔙 Назад к выбору курса":
        await state.clear()
        await message.answer(
            "Начнем сначала. Пожалуйста, укажите ваш курс:",
            reply_markup=get_course_selection_keyboard()
        )
        await state.set_state(RegistrationStates.waiting_for_course)
        
    else:
        await message.answer("Пожалуйста, используйте кнопки для подтверждения или отмены.")

# -------------------- 9. ОБРАБОТЧИКИ МЕНЮ --------------------
@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if await check_subscription(user_id):
        user_data = await db.get_user(user_id)
        user_course = user_data['course'] if user_data else None
        
        # 1. Удаляем инлайн-клавиатуру из предыдущего сообщения
        await callback.message.edit_reply_markup(reply_markup=None)
        
        # 2. Оповещаем пользователя (опционально)
        await callback.answer("✅ Подписка подтверждена!", show_alert=False)
        
        # 3. Вызываем cmd_start для инициализации регистрации/меню
        await cmd_start(callback.message, state)
        
    else:
        await callback.answer("❌ Подписка не найдена. Попробуйте снова.", show_alert=True)

# --- УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ДЛЯ КНОПКИ "🔙 Главное меню" ---
@dp.message(F.text == "🔙 Главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    user_course = user_data['course'] if user_data else None

    await state.clear()
    
    await message.answer(
        "Вы вернулись в главное меню.",
        reply_markup=get_reply_main_menu_keyboard(user_course, user_id)
    )
    
class ExamStates(StatesGroup):
    waiting_for_subject = State()

@dp.message(F.text == "📚 Экзамен")
async def exam_menu(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        await message.answer("Пожалуйста, завершите регистрацию через /start")
        return
    
    user_course = user_data['course']
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    if not is_admin:
        await state.update_data(exam_course=user_course)
        
        await message.answer(
            f"Теперь выберите предмет <b>{user_course}-го курса</b>:",
            reply_markup=get_reply_exam_subject_keyboard(user_course, user_id),
            parse_mode="HTML"
        )
        await state.set_state(ExamStates.waiting_for_subject)
        return
    
    await state.update_data(target_section="exam")
    await message.answer(
        "👑 <b>Админ-меню Экзамен:</b> Выберите язык материалов:",
        reply_markup=get_group_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_admin_group)

@dp.message(AdminStates.waiting_for_exam_course)
async def process_exam_course_selection(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        await state.clear()
        return await message.answer("Ошибка пользователя. Пожалуйста, начните с /start")

    user_course_limit = user_data['course']
    user_id = message.from_user.id
    
    try:
        course_num = int(message.text.split("-")[0].replace('й', ''))
        
        if user_id not in ADMIN_IDS and course_num > user_course_limit:
             await message.answer(f"❌ У вас есть доступ только к материалам {user_course_limit}-го курса и ниже.")
             return

        await state.update_data(exam_course=course_num)
        
        await message.answer(
            f"✅ Выбран <b>{course_num}-й курс</b>. Теперь выберите предмет:",
            reply_markup=get_reply_exam_subject_keyboard(course_num, user_id),
            parse_mode="HTML"
        )
        await state.set_state(ExamStates.waiting_for_subject)

    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите курс, используя кнопки.")

@dp.message(ExamStates.waiting_for_subject, F.text.in_(ALL_SUBJECTS_MAP.values()))
async def exam_subject_handler(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return await message.answer("Пожалуйста, завершите регистрацию через /start")

    user_course_limit = user_data['course']
    user_group = user_data['group_lang']
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    data = await state.get_data()
    exam_course = data.get('exam_course')
    
    # 1. Проверка на отсутствие курса
    if not exam_course:
        if not is_admin:
             return await message.answer("⚠️ Ошибка: курс не был выбран. Начните с '📚 Экзамен'.", reply_markup=get_reply_main_menu_keyboard(user_course_limit, user_id))
        
        await state.set_state(AdminStates.waiting_for_exam_course)
        return await message.answer(
            "⚠️ Пожалуйста, сначала выберите курс.",
            reply_markup=get_reply_exam_course_keyboard(user_course_limit)
        )
    
    # 2. Определение тега
    selected_subject_name = message.text
    subject_tag = None
    
    for tag, name in ALL_SUBJECTS_MAP.items():
        if name == selected_subject_name:
            if tag in COURSE_SUBJECTS.get(exam_course, []):
                 subject_tag = tag
                 break
    
    if not subject_tag:
        return await message.answer(f"Ошибка: Неизвестный предмет или предмет не соответствует {exam_course}-му курсу.")

    final_tag = subject_tag
    
    # 3. Фильтрация контента
    course_to_filter_by = exam_course if is_admin else user_course_limit
    group_to_filter_by = data.get('admin_group_filter', user_group)
    
    await send_content_by_tag(message.chat.id, final_tag, course_to_filter_by, group_to_filter_by)
    
    # 4. Админ-панель
    if user_id in ADMIN_IDS:
        await message.answer(
            f"<b>АДМИН-ПАНЕЛЬ:</b> Загрузка для <b>#{final_tag}</b>",
            reply_markup=get_admin_menu(final_tag),
            parse_mode="HTML"
        )

    # 5. Возврат в меню предметов (сохраняем exam_course)
    await state.update_data(exam_course=exam_course)
    
    await message.answer(
        f"Курс <b>{exam_course}-й</b> - Материалы отправлены. Выберите следующий предмет:",
        reply_markup=get_reply_exam_subject_keyboard(exam_course, user_id),
        parse_mode="HTML"
    )
    await state.set_state(ExamStates.waiting_for_subject)

@dp.message(F.text == "🔙 К выбору курса")
async def back_to_exam_courses(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await back_to_main_menu(message, state)
        
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return await message.answer("Пожалуйста, завершите регистрацию через /start")
    
    user_course = user_data['course']
    await state.update_data(exam_course=None)
    await state.set_state(AdminStates.waiting_for_exam_course)
    await message.answer(
        "Выберите курс, по которому вы хотите сдать экзамен:",
        reply_markup=get_reply_exam_course_keyboard(user_course)
    )

@dp.message(F.text == "📋 Итог")
async def summary_menu(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        await message.answer("Пожалуйста, завершите регистрацию через /start")
        return
    
    user_course = user_data['course']
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS

    if not is_admin and user_course <= MAX_COURSE_FOR_SUMMARY:
        
        await message.answer(
            f"✅ Выбран <b>{user_course}-й курс</b>. Теперь выберите раздел итогов (1-4):",
            reply_markup=get_reply_final_summary_keyboard(user_course),
            parse_mode="HTML"
        )
        return
    
    await state.update_data(target_section="summary")
    await message.answer(
        "👑 <b>Админ-меню Итог:</b> Выберите язык материалов:",
        reply_markup=get_group_selection_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_admin_group)


@dp.message(AdminStates.waiting_for_summary_course)
async def process_admin_summary_course(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        await state.clear()
        return await message.answer("Ошибка пользователя. Пожалуйста, начните с /start")
    
    user_course_limit = user_data['course']
    user_id = message.from_user.id

    try:
        course_num_str = message.text.split('-')[1].strip().split(' ')[0]
        course_num = int(course_num_str)
        
        if course_num > MAX_COURSE_FOR_SUMMARY:
             return await message.answer(f"❌ Доступны только курсы 1-{MAX_COURSE_FOR_SUMMARY} для раздела Итог.")

        await message.answer(
            f"✅ Выбран <b>{course_num}-й курс</b>. Теперь выберите раздел итогов (1-4):",
            reply_markup=get_reply_final_summary_keyboard(course_num),
            parse_mode="HTML"
        )
        await state.set_state(None)

    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите курс, используя кнопки.")


@dp.message(F.text.startswith("Итог -") & F.text.endswith("курс"))
async def process_summary_course_selection(message: types.Message):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return await message.answer("Пожалуйста, завершите регистрацию через /start")
    
    user_course_limit = user_data['course']
    user_group = user_data['group_lang']
    user_id = message.from_user.id

    try:
        course_num_str = message.text.split('-')[1].strip().split(' ')[0]
        course_num = int(course_num_str)
        
        if user_id not in ADMIN_IDS and (course_num > user_course_limit or course_num > MAX_COURSE_FOR_SUMMARY):
            await message.answer("❌ У вас нет доступа к этому курсу итоговых материалов.")
            return
            
        await message.answer(
            f"✅ Выбран <b>{course_num}-й курс</b>. Теперь выберите раздел итогов (1-4):",
            reply_markup=get_reply_final_summary_keyboard(course_num),
            parse_mode="HTML"
        )
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите курс, используя кнопки.")

@dp.message(F.text.startswith("Итог") & F.text.contains("."))
async def final_summary_handler(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return await message.answer("Пожалуйста, завершите регистрацию через /start")

    user_course_limit = user_data['course']
    user_group = user_data['group_lang']
    user_id = message.from_user.id
    
    data = await state.get_data()

    try:
        parts = message.text.split(' ')[1].split('.')
        course = int(parts[0])
        section = int(parts[1])
        
        if course > MAX_COURSE_FOR_SUMMARY:
            return await message.answer("❌ Этот раздел итогов не существует или неактивен.")
            
        final_tag = f"summary{course}.{section}"
    except (ValueError, IndexError):
        return await message.answer("Ошибка: Неверный формат выбора итогового раздела. Пожалуйста, используйте кнопки.")

    group_to_filter_by = data.get('admin_group_filter', user_group)

    await send_content_by_tag(message.chat.id, final_tag, user_course_limit, group_to_filter_by)
    
    if user_id in ADMIN_IDS:
        await message.answer(
            f"<b>АДМИН-ПАНЕЛЬ:</b> Загрузка для <b>#{final_tag}</b>",
            reply_markup=get_admin_menu(final_tag),
            parse_mode="HTML"
        )

    await message.answer(
        f"Материалы отправлены. Выберите следующий раздел:",
        reply_markup=get_reply_final_summary_keyboard(course),
        parse_mode="HTML"
    )

@dp.message(F.text == "🚪 Личный кабинет")
async def personal_account(message: types.Message):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        await message.answer("Пожалуйста, завершите регистрацию через /start")
        return
        
    user_id = user_data['user_id']
    username = user_data['username']
    full_name = user_data['full_name']
    course = user_data['course']
    group_lang = user_data['group_lang']
    registered_at = user_data['registered_at']
    
    account_info = (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"• <b>Имя:</b> {full_name}\n"
        f"• <b>Курс:</b> {course}-й\n"
        f"• <b>Группа:</b> {GROUPS.get(group_lang, group_lang)}\n"
        f"• <b>Зарегистрирован:</b> {str(registered_at)[:10]}\n\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Открыть study.tj", web_app=WebAppInfo(url="https://study.tj/"))
    
    await message.answer(account_info, reply_markup=builder.as_markup(), parse_mode="HTML")


# --- ОБРАБОТЧИКИ РАЗДЕЛА МАТЕРИАЛЫ ---
@dp.message(F.text == "📂 Материалы")
async def materials_menu(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return await message.answer("Пожалуйста, завершите регистрацию через /start")
    
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    if is_admin:
        await state.update_data(target_section="materials")
        await message.answer(
            "👑 <b>Админ-меню Материалы:</b> Выберите язык материалов:",
            reply_markup=get_group_selection_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.waiting_for_admin_group)
        return
    
    # Для обычного пользователя - выбор типа материала
    await message.answer(
        "Выберите тип материалов:",
        reply_markup=get_reply_materials_menu_keyboard()
    )
    await state.set_state(MaterialsStates.waiting_for_material_type)


@dp.message(MaterialsStates.waiting_for_material_type, F.text.in_(MATERIAL_TYPES.values()))
async def handle_material_type_selection(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    user_course = user_data['course']
    user_id = user_data['user_id']
    
    material_type_key = next((key for key, value in MATERIAL_TYPES.items() if value == message.text), None)
    if not material_type_key:
        return

    await state.update_data(material_type=material_type_key, materials_course=user_course)
    
    await message.answer(
        f"✅ Выбрано: <b>{message.text}</b>.\n"
        f"Теперь выберите предмет для <b>{user_course}</b>-го курса:",
        reply_markup=get_reply_materials_subject_keyboard(user_course, material_type, user_id),
        parse_mode="HTML"
    )
    await state.set_state(MaterialsStates.waiting_for_subject)

@dp.message(MaterialsStates.waiting_for_subject, F.text.in_(MATERIALS_SUBJECTS_MAP.values()))
async def handle_materials_subject_selection(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    user_id = user_data['user_id']
    user_group = user_data['group_lang']
    is_admin = user_id in ADMIN_IDS
    data = await state.get_data()

    material_type = data.get('material_type')
    materials_course = data.get('materials_course')
    
    if not material_type or not materials_course:
        await state.clear()
        return await back_to_main_menu(message, state)

    subject_tag = next((tag for tag, name in MATERIALS_SUBJECTS_MAP.items() if name == message.text), None)
    if not subject_tag:
        return

    final_tag = f"{material_type}_{subject_tag}"
    group_to_filter_by = data.get('admin_group_filter', user_group)

    await send_content_by_tag(message.chat.id, final_tag, materials_course, group_to_filter_by)

    if is_admin:
        await message.answer(
            f"<b>АДМИН-ПАНЕЛЬ:</b> Загрузка для <b>#{final_tag}</b>",
            reply_markup=get_admin_menu(final_tag),
            parse_mode="HTML"
        )

    type_name = MATERIAL_TYPES.get(material_type, "Материалы")
    await message.answer(
        f"{type_name} - Курс <b>{materials_course}-й</b> - Материалы отправлены.\n"
        f"Выберите следующий предмет или вернитесь назад.",
        reply_markup=get_reply_materials_subject_keyboard(materials_course, material_type, user_id), # <--- ИСПРАВЛЕНИЕ
        parse_mode="HTML"
    )
    await state.set_state(MaterialsStates.waiting_for_subject)

@dp.message(F.text == "🔙 К типам материалов")
async def back_to_material_types(message: types.Message, state: FSMContext):
    await state.clear()
    await materials_menu(message, state)
    
@dp.message(F.text == "🔙 К выбору курса (Материалы)")
async def back_to_materials_course_admin(message: types.Message, state: FSMContext):
     if message.from_user.id in ADMIN_IDS:
        user_data = await db.get_user(message.from_user.id)
        # Определяем максимальный курс для админа
        user_course_limit = user_data['course'] if user_data else max(COURSES)
        
        # Очищаем ранее выбранный курс
        await state.update_data(materials_course=None)
        
        # Получаем тип материала из состояния (он должен там остаться)
        data = await state.get_data()
        material_type = data.get('material_type', 'N/A')
        type_name = MATERIAL_TYPES.get(material_type, material_type)

        # Устанавливаем состояние ожидания выбора КУРСА
        await state.set_state(AdminStates.waiting_for_materials_subject)
        
        # Отправляем сообщение и клавиатуру для выбора КУРСА
        await message.answer(
            f"✅ Выбран тип: <b>{type_name}</b>.\n\nТеперь выберите курс:",
            reply_markup=get_reply_materials_course_keyboard(user_course_limit),
            parse_mode="HTML"
        )
     else:
        await back_to_main_menu(message, state)

@dp.message(AdminStates.waiting_for_materials_course, F.text.in_(MATERIAL_TYPES.values()))
async def admin_select_material_type(message: types.Message, state: FSMContext):
    user_data = await db.get_user(message.from_user.id)
    user_course_limit = user_data['course']
    
    material_type_key = next((key for key, value in MATERIAL_TYPES.items() if value == message.text), None)
    if not material_type_key: return

    await state.update_data(material_type=material_type_key)
    await message.answer(
        f"✅ Выбран тип: <b>{message.text}</b>.\n\nТеперь выберите курс:",
        reply_markup=get_reply_materials_course_keyboard(user_course_limit),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_materials_subject)

@dp.message(AdminStates.waiting_for_materials_subject, F.text.regexp(r'\d+-й курс'))
async def admin_select_course_for_materials(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    material_type = data.get('material_type')
    
    if not material_type:
        await state.clear()
        user_data = await db.get_user(user_id)
        user_course = user_data['course'] if user_data else None
        await message.answer(
            "⚠️ Произошла ошибка состояния (тип материала не найден). Пожалуйста, начните сначала.",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id)
        )
        return
    try:
        course_num = int(message.text.split("-")[0])
        await state.update_data(materials_course=course_num)
        
        await message.answer(
            f"✅ Выбран <b>{course_num}-й курс</b>. Теперь выберите предмет:",
           reply_markup=get_reply_materials_subject_keyboard(course_num, material_type, user_id),
            parse_mode="HTML"
        )
        await state.set_state(MaterialsStates.waiting_for_subject)
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите курс, используя кнопки.")


@dp.message(AdminStates.waiting_for_materials_course)
async def process_admin_group_selection(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_section = data.get('target_section')
    
    group_lang = next((key for key, value in GROUPS.items() if value == message.text), None)
            
    if not group_lang:
        return await message.answer("Пожалуйста, выберите группу используя кнопки ниже.")

    await state.update_data(admin_group_filter=group_lang)
    
    user_data = await db.get_user(message.from_user.id)
    user_course_limit = user_data['course']
    
    if target_section == "exam":
        # Этот блок не трогаем
        await message.answer(
            f"✅ Выбран язык: {GROUPS[group_lang]}. Выберите курс:",
            reply_markup=get_reply_exam_course_keyboard(user_course_limit)
        )
        await state.set_state(AdminStates.waiting_for_exam_course)
        
    elif target_section == "summary":
        # Этот блок не трогаем
        await message.answer(
            f"✅ Выбран язык: {GROUPS[group_lang]}. Выберите курс для итога:",
            reply_markup=get_reply_summary_course_keyboard(user_course_limit)
        )
        await state.set_state(AdminStates.waiting_for_summary_course)
        
    elif target_section == "materials":
        # <<< ИСПРАВЛЕНИЕ ЗДЕСЬ >>>
        await message.answer(
            f"✅ Выбран язык: {GROUPS[group_lang]}. Теперь выберите тип материала:",
            reply_markup=get_reply_materials_menu_keyboard()
        )
        # Устанавливаем состояние ожидания ТИПА МАТЕРИАЛА
        await state.set_state(AdminStates.waiting_for_materials_course)
        
    else:
        await state.clear()
        user_id = message.from_user.id
        return await message.answer(
            "Ошибка секции. Возврат в главное меню.",
            reply_markup=get_reply_main_menu_keyboard(user_course_limit, user_id)
        )

# --- УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ДЛЯ ПРЕДМЕТОВ МАТЕРИАЛОВ ---
async def handle_materials_subject(message: types.Message, state: FSMContext):
    """Обработка выбора предмета для материалов (и для админа, и для пользователя)"""
    user_data = await db.get_user(message.from_user.id)
    if not user_data:
        return await message.answer("Пожалуйста, завершите регистрацию через /start")

    user_course_limit = user_data['course']
    user_group = user_data['group_lang']
    user_id = message.from_user.id
    is_admin = user_id in ADMIN_IDS
    
    data = await state.get_data()
    material_type = data.get('material_type')
    materials_course = data.get('materials_course')
    
    # Проверка на наличие типа материала и курса
    if not material_type or not materials_course:
        if not is_admin:
            return await message.answer(
                "⚠️ Ошибка: тип материала или курс не выбран. Начните с '📂 Материалы'.",
                reply_markup=get_reply_main_menu_keyboard(user_course_limit, user_id)
            )
        else:
            await state.clear()
            return await message.answer(
                "⚠️ Ошибка состояния. Начните с '📂 Материалы'.",
                reply_markup=get_reply_main_menu_keyboard(user_course_limit, user_id)
            )
    
    # Определение тега предмета
    selected_subject_name = message.text
    subject_tag = None
    
    for tag, name in MATERIALS_SUBJECTS_MAP.items():
        if name == selected_subject_name:
            if tag in MATERIALS_COURSE_SUBJECTS.get(materials_course, []):
                subject_tag = tag
                break
    
    if not subject_tag:
        return await message.answer(
            f"Ошибка: Неизвестный предмет или предмет не соответствует {materials_course}-му курсу."
        )
    
    # Формируем комбинированный тег: lecture_chem1, practice_bio1, video_anat2
    final_tag = f"{material_type}_{subject_tag}"
    
    # Фильтрация контента
    course_to_filter_by = materials_course if is_admin else user_course_limit
    group_to_filter_by = data.get('admin_group_filter', user_group)
    
    await send_content_by_tag(message.chat.id, final_tag, course_to_filter_by, group_to_filter_by)
    
    # Админ-панель
    if is_admin:
        await message.answer(
            f"<b>АДМИН-ПАНЕЛЬ:</b> Загрузка для <b>#{final_tag}</b>",
            reply_markup=get_admin_menu(final_tag),
            parse_mode="HTML"
        )
    
    # Возврат в меню предметов
    type_name = MATERIAL_TYPES.get(material_type, material_type)
    await message.answer(
        f"{type_name} - Курс <b>{materials_course}-й</b> - Материалы отправлены.\n"
        f"Выберите следующий предмет:",
        reply_markup=get_reply_materials_subject_keyboard(materials_course, material_type, user_id),
        parse_mode="HTML"
    )


# Регистрируем обработчик для всех предметов в контексте материалов
@dp.message(F.text.in_(MATERIALS_COURSE_SUBJECTS.values()))
async def subject_handler_router(message: types.Message, state: FSMContext):
    """Роутер: определяет, это экзамен или материалы"""
    data = await state.get_data()
    
    # Если есть material_type - это материалы
    if data.get('material_type'):
        await handle_materials_subject(message, state)
    # Иначе - это экзамен
    else:
        await exam_subject_handler(message, state)
# --- FSM ОБРАБОТЧИК ВЫБОРА ЯЗЫКА ДЛЯ АДМИНА ---

@dp.message(AdminStates.waiting_for_admin_group)
async def process_admin_group_selection(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_section = data.get('target_section')
    
    group_lang = None
    for key, value in GROUPS.items():
        if message.text == value:
            group_lang = key
            break
            
    if not group_lang:
        return await message.answer("Пожалуйста, выберите группу используя кнопки ниже.")

    await state.update_data(admin_group_filter=group_lang)
    
    user_data = await db.get_user(message.from_user.id)
    user_course_limit = user_data['course']
    user_id = message.from_user.id
    
    if target_section == "exam":
        # Переход к выбору курса экзамена (шаг для админа)
        await message.answer(
            f"✅ Выбран язык: {GROUPS[group_lang]}. Выберите курс:",
            reply_markup=get_reply_exam_course_keyboard(user_course_limit)
        )
        await state.set_state(AdminStates.waiting_for_exam_course)
        
    elif target_section == "summary":
        # Переход к выбору курса итога (шаг для админа)
        await message.answer(
            f"✅ Выбран язык: {GROUPS[group_lang]}. Выберите курс для итога:",
            reply_markup=get_reply_summary_course_keyboard(user_course_limit)
        )
        await state.set_state(AdminStates.waiting_for_summary_course)
        
    elif target_section == "materials":
        # Переход к выбору типа материалов (шаг для админа)
        await message.answer(
            f"✅ Выбран язык: {GROUPS[group_lang]}. Выберите тип материала:",
            reply_markup=get_reply_materials_menu_keyboard()
        )
        await state.set_state(AdminStates.waiting_for_materials_course)
        
    else:
        await state.clear()
        return await message.answer(
            "Ошибка секции. Возврат в главное меню.",
            reply_markup=get_reply_main_menu_keyboard(user_course_limit, user_id)
        )
        
# --- НОВАЯ АДМИН-КОМАНДА ДЛЯ РАССЫЛКИ (BROADCAST) ---

@dp.message(Command("broadcast"))
async def cmd_start_broadcast(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Доступ запрещен.")
    
    # Добавляем опцию "Всем группам" для полного охвата
    builder = ReplyKeyboardBuilder()
    for key, value in GROUPS.items():
        builder.button(text=value)
    builder.button(text="ВСЕМ ГРУППАМ")
    builder.adjust(3)
    
    await message.answer(
        "👑 <b>РАССЫЛКА:</b> Выберите целевую группу:",
        reply_markup=builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast_filter)


@dp.message(AdminStates.waiting_for_broadcast_filter)
async def process_broadcast_group_filter(message: types.Message, state: FSMContext):
    group_lang = message.text
    
    if group_lang == "ВСЕМ ГРУППАМ":
        group_filter_key = 'all'
    else:
        group_filter_key = next((key for key, value in GROUPS.items() if value == group_lang), None)
        
    if not group_filter_key and group_lang != "ВСЕМ ГРУППАМ":
        return await message.answer("Пожалуйста, выберите группу из предложенных кнопок.")

    await state.update_data(broadcast_group=group_filter_key)
    
    # Теперь спрашиваем курс
    builder = ReplyKeyboardBuilder()
    for course in COURSES:
        builder.button(text=f"Курс {course}")
    builder.button(text="ВСЕМ КУРСАМ")
    builder.adjust(3)
    
    await message.answer(
        f"✅ Группа выбрана ({group_lang}). Теперь выберите курс:",
        reply_markup=builder.as_markup(resize_keyboard=True),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_broadcast_course)


@dp.message(AdminStates.waiting_for_broadcast_course)
async def process_broadcast_course_filter(message: types.Message, state: FSMContext):
    course_text = message.text
    course_filter_num = 0 # 0 будет означать "ВСЕМ КУРСАМ"

    if course_text == "ВСЕМ КУРСАМ":
        pass
    elif course_text.startswith("Курс "):
        try:
            course_filter_num = int(course_text.split(" ")[1])
            if course_filter_num not in COURSES:
                raise ValueError
        except (ValueError, IndexError):
            return await message.answer("Неверный формат курса. Пожалуйста, используйте кнопки.")
    else:
        return await message.answer("Пожалуйста, выберите курс из предложенных кнопок.")

    await state.update_data(broadcast_course=course_filter_num)

    # Запрашиваем контент (ИЗМЕНЕНИЕ: Убрали ожидание только текста и удалили клавиатуру)
    await message.answer(
        "📝 **Введите контент (текст, фото, файл и т.д.) для рассылки.**\n\n"
        "<i>(Вы можете использовать HTML-разметку для текста)</i>",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    # Переводим в состояние ожидания ЛЮБОГО контента
    await state.set_state(AdminStates.waiting_for_broadcast_content)


@dp.message(AdminStates.waiting_for_broadcast_content, F.text | F.photo | F.document | F.video | F.audio | F.voice | F.animation)
async def process_broadcast_content(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    # ИЗМЕНЕНИЕ: Логика определения типа контента
    content_type = 'text'
    file_id = None
    caption = message.caption or message.text
    
    if message.photo:
        content_type = 'photo'
        file_id = message.photo[-1].file_id
    elif message.document:
        content_type = 'document'
        file_id = message.document.file_id
        caption = message.caption or message.document.file_name # Для документов лучше сохранять имя файла, если нет подписи
    elif message.video:
        content_type = 'video'
        file_id = message.video.file_id
    elif message.audio:
        content_type = 'audio'
        file_id = message.audio.file_id
    elif message.voice:
        content_type = 'voice'
        file_id = message.voice.file_id
    elif message.animation:
        content_type = 'animation'
        file_id = message.animation.file_id
    elif not message.text:
        # Если нет ни текста, ни медиа
        return await message.answer("⚠️ Неподдерживаемый тип контента для рассылки.")


    data = await state.get_data()
    course = data.get('broadcast_course')
    group_lang = data.get('broadcast_group')
    
    # 1. Получаем список user_id из базы данных
    user_ids = await db.get_users_for_broadcast(course, group_lang)
    
    if not user_ids:
        await state.clear()
        user_data = await db.get_user(user_id)
        user_course = user_data['course']
        return await message.answer(
            f"❌ Не найдено ни одного активного пользователя, соответствующего фильтрам (Курс: {course if course else 'Все'}, Группа: {GROUPS.get(group_lang, 'Все')}).",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id),
            parse_mode="HTML"
        )
    
    # 2. Отправляем рассылку
    success_count = 0
    total_count = len(user_ids)
    
    await message.answer(f"⏳ **Начинаю рассылку** ({total_count} получателей, тип: {content_type}). Ожидайте...", parse_mode="HTML")
    
    for target_id in user_ids:
        try:
            if content_type == 'text':
                await bot.send_message(
                    chat_id=target_id,
                    text=caption,
                    parse_mode="HTML"
                )
            # Использование соответствующих методов для медиа
            elif content_type == 'photo':
                await bot.send_photo(target_id, file_id, caption=caption, parse_mode="HTML")
            elif content_type == 'document':
                await bot.send_document(target_id, file_id, caption=caption, parse_mode="HTML")
            elif content_type == 'video':
                await bot.send_video(target_id, file_id, caption=caption, parse_mode="HTML")
            elif content_type == 'audio':
                await bot.send_audio(target_id, file_id, caption=caption, parse_mode="HTML")
            elif content_type == 'voice':
                await bot.send_voice(target_id, file_id, caption=caption, parse_mode="HTML")
            elif content_type == 'animation':
                await bot.send_animation(target_id, file_id, caption=caption, parse_mode="HTML")

            success_count += 1
            # Небольшая задержка, чтобы избежать лимитов
            await asyncio.sleep(0.05) 
            
        except Exception as e:
            # Логируем ошибку, но продолжаем рассылку
            logger.error(f"Не удалось отправить сообщение пользователю {target_id} ({content_type}): {e}")
            
    # 3. Уведомляем админа о результате
    await state.clear()
    user_data = await db.get_user(user_id)
    user_course = user_data['course']
    
    await message.answer(
        f"✅ **Рассылка завершена!**\n"
        f"Тип контента: **{content_type.capitalize()}**\n"
        f"Успешно отправлено: **{success_count}** из {total_count} сообщений.\n"
        f"Фильтры: Курс {course if course else 'Все'}, Группа {GROUPS.get(group_lang, 'Все')}.",
        reply_markup=get_reply_main_menu_keyboard(user_course, user_id),
        parse_mode="HTML"
    )


# -------------------- 10. АДМИН-ПАНЕЛЬ (FSM) --------------------
@dp.callback_query(F.data.startswith('upload__'))
async def start_upload_fsm(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен.")
        return
    target_tag = callback.data.split('__')[1]
    
    data = await state.get_data()
    group_filter = data.get('admin_group_filter', None)
    
    await state.update_data(
        target_tag=target_tag,
        course_filter=None,
        group_filter=group_filter
    )
    await state.set_state(AdminStates.waiting_for_content)
    
    filter_info = f"только для группы {GROUPS.get(group_filter, 'N/A')}" if group_filter else "для ВСЕХ групп"
    
    await callback.message.answer(
        f"✅ Режим загрузки активирован для раздела <b>#{target_tag}</b> ({filter_info}).\n"
        f"Отправьте файл, фото или текст.\n"
        f"Для отмены введите /start или /cancel.",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(AdminStates.waiting_for_content)
async def process_content_upload(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text and (message.text.lower() == '/start' or message.text.lower() == '/cancel'):
        await state.clear()
        user_data = await db.get_user(user_id)
        user_course = user_data['course'] if user_data else None
        return await message.answer("Загрузка отменена. Возврат в главное меню.", reply_markup=get_reply_main_menu_keyboard(user_course, user_id))

    data = await state.get_data()
    target_tag = data.get('target_tag')
    course_filter = data.get('course_filter')
    group_filter = data.get('group_filter')
    
    if not target_tag:
        await state.clear()
        return await message.answer("Ошибка: не удалось определить целевой раздел. Попробуйте снова.")
        
    entry = {
        "type": "text",
        "file_id": None,
        "caption": message.caption or message.text,
        "file_name": None,
        "course": course_filter,
        "group_lang": group_filter
    }
    
    if message.document:
        entry["type"] = "document"
        entry["file_id"] = message.document.file_id
        entry["file_name"] = message.document.file_name
    elif message.photo:
        entry["type"] = "photo"
        entry["file_id"] = message.photo[-1].file_id
        entry["file_name"] = "Изображение"
    elif message.video:
        entry["type"] = "video"
        entry["file_id"] = message.video.file_id
        entry["file_name"] = message.video.file_name or "Видеозапись"
    elif not message.text:
        await message.answer("⚠️ Неподдерживаемый тип контента (нужен файл, фото, видео или текст).")
        return

    material_id = await db.save_material(
        tag=target_tag,
        type_=entry["type"],
        file_id=entry["file_id"],
        file_name=entry["file_name"],
        caption=entry["caption"],
        course=entry["course"],
        group_lang=entry["group_lang"]
    )

    filter_text = f" (для группы {GROUPS.get(group_filter, 'N/A')})" if group_filter else " (доступно всем)"

    await message.answer(
        f"✅ Материал успешно сохранён в раздел <b>#{target_tag}</b>{filter_text}!\n"
        f"ID: {material_id}\n"
        f"Тип: {entry['type']}\n"
        f"Имя файла: <b>{entry.get('file_name', 'Текст')}</b>",
        parse_mode="HTML"
    )
    
    await state.clear()
    user_data = await db.get_user(user_id)
    user_course = user_data['course'] if user_data else None
    await message.answer("Загрузка завершена. Выберите следующий раздел.", reply_markup=get_reply_main_menu_keyboard(user_course, user_id))

@dp.callback_query(F.data.startswith('delete_indexed__'))
async def start_indexed_delete(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен.")
        return
    tag = callback.data.split('__')[1]
    
    materials = await db.get_materials_by_tag(tag)
    
    if not materials:
        return await callback.message.answer(f"❌ В разделе <b>#{tag}</b> нет материалов для удаления.", parse_mode="HTML")

    await state.update_data(target_tag=tag, materials=materials)
    await state.set_state(AdminStates.waiting_for_index_to_delete)
    
    response_text = f"🗑️ <b>УДАЛЕНИЕ:</b> Раздел <b>#{tag}</b>\n\n"
    for material in materials:
        mat_id = material['id']
        mat_type = material['type']
        file_name = material['file_name']
        caption = material['caption']
        mat_course = material['course']
        mat_group = material['group_lang']
        
        display_name = file_name if mat_type != "text" and file_name else (caption[:50] + "..." if caption and len(caption) > 50 else caption or "Текст")
        
        filter_info = []
        if mat_course:
            filter_info.append(f"к{mat_course}")
        if mat_group:
            filter_info.append(f"г{mat_group}")
        filters = f" [{', '.join(filter_info)}]" if filter_info else " [всем]"
        
        response_text += f"<b>ID {mat_id}:</b> <code>{mat_type.upper()}</code> {display_name}{filters}\n"
    
    response_text += "\n\n🔢 <b>Для удаления:</b> Введите <b>ID материала(ов)</b> через пробел (например, <code>5 12 8</code>), <b>ALL</b> для удаления всех материалов, или /start/ /cancel для отмены."

    await callback.message.answer(response_text, parse_mode="HTML")
    await callback.answer()

@dp.message(AdminStates.waiting_for_index_to_delete)
async def process_indexed_deletion(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.text and (message.text.lower() == '/start' or message.text.lower() == '/cancel'):
        await state.clear()
        user_data = await db.get_user(user_id)
        user_course = user_data['course'] if user_data else None
        return await message.answer("Удаление отменено. Возврат в главное меню.", reply_markup=get_reply_main_menu_keyboard(user_course, user_id))

    data = await state.get_data()
    tag = data.get('target_tag')
    materials = data.get('materials')

    if not message.text:
        return await message.answer("⚠️ Введите один или несколько ID через пробел (например, <code>5 12 8</code>) или слово ALL.", parse_mode="HTML")

    input_text = message.text.strip().upper()
    
    if input_text == "ALL":
        deleted_count = 0
        for material in materials:
            mat_id = material['id']
            if await db.delete_material(mat_id) > 0:
                deleted_count += 1
                
        await message.answer(f"✅ <b>ВСЕ</b> материалы ({deleted_count} шт.) из раздела <b>#{tag}</b> были успешно <b>УДАЛЕНЫ</b>.", parse_mode="HTML")
        await state.clear()
        user_data = await db.get_user(user_id)
        user_course = user_data['course'] if user_data else None
        return await message.answer("Удаление завершено.", reply_markup=get_reply_main_menu_keyboard(user_course, user_id))

    try:
        ids_str = input_text.replace(',', ' ').split()
        ids_to_delete = [int(i) for i in ids_str]
        
        if not ids_to_delete:
            return await message.answer("⚠️ Введите один или несколько ID через пробел (например, <code>5 12 8</code>) или слово ALL.", parse_mode="HTML")

    except ValueError:
        return await message.answer("⚠️ Неверный формат ввода. Введите числа (ID) через пробел (например, <code>5 12 8</code>) или слово ALL.", parse_mode="HTML")
        
    deleted_count = 0
    existing_ids = [mat['id'] for mat in materials]
    
    for material_id in ids_to_delete:
        if material_id in existing_ids:
            if await db.delete_material(material_id) > 0:
                deleted_count += 1
        else:
            await message.answer(f"❌ Материал с ID {material_id} не найден в разделе <b>#{tag}</b>. Пропуск.", parse_mode="HTML")

    if deleted_count > 0:
        await message.answer(
            f"✅ <b>{deleted_count}</b> материал(а) был(и) успешно <b>УДАЛЕН(Ы)</b> из раздела <b>#{tag}</b>.",
            parse_mode="HTML"
        )
    else:
        await message.answer("⚠️ Ни один материал не был удален. Проверьте введенные ID.", parse_mode="HTML")

    await state.clear()
    user_data = await db.get_user(user_id)
    user_course = user_data['course'] if user_data else None
    await message.answer("Удаление завершено.", reply_markup=get_reply_main_menu_keyboard(user_course, user_id))

@dp.message(Command("admin_stats"))
async def cmd_admin_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Доступ запрещен.")
    
    async with db.pool.acquire() as conn:
        
        total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
        users_by_course = await conn.fetch('SELECT course, COUNT(*) FROM users GROUP BY course')
        users_by_group = await conn.fetch('SELECT group_lang, COUNT(*) FROM users GROUP BY group_lang')
        
        total_materials = await conn.fetchval('SELECT COUNT(*) FROM materials')
        materials_by_tag = await conn.fetch('SELECT tag, COUNT(*) FROM materials GROUP BY tag')
        
        filtered_materials = await conn.fetch('''
            SELECT tag, course, group_lang, COUNT(*)
            FROM materials
            WHERE course IS NOT NULL OR group_lang IS NOT NULL
            GROUP BY tag, course, group_lang
        ''')
    
    stats_text = "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
    
    stats_text += f"👥 <b>Пользователи:</b> {total_users}\n"
    for row in users_by_course:
        stats_text += f"  • {row['course']}-й курс: {row['count']}\n"
    
    stats_text += "\n🌍 <b>По группам:</b>\n"
    for row in users_by_group:
        stats_text += f"  • {GROUPS.get(row['group_lang'], row['group_lang'])}: {row['count']}\n"
    
    if filtered_materials:
        stats_text += "\n🎯 <b>Материалы с фильтрами:</b>\n"
        for row in filtered_materials:
            filter_info = []
            if row['course']:
                filter_info.append(f"к{row['course']}")
            if row['group_lang']:
                filter_info.append(f"г{row['group_lang']}")
            stats_text += f"  • #{row['tag']} [{', '.join(filter_info)}]: {row['count']}\n"
    
    await message.answer(stats_text, parse_mode="HTML")

# Команда для просмотра материалов админом
@dp.message(Command("admin_materials"))
async def cmd_admin_materials(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Доступ запрещен.")
    
    materials_stats = await db.get_all_materials()

    if not materials_stats:
        return await message.answer("📭 В базе нет материалов.")
    
    stats_grouped: Dict[str, Dict[str, int]] = {}
    for mat in materials_stats:
        tag = mat['tag']
        mat_type = mat['type']
        
        filter_str = ""
        if mat['course']:
            filter_str += f"к{mat['course']}"
        if mat['group_lang']:
            filter_str += f"г{mat['group_lang']}"
        
        key = f"{mat_type} [{filter_str or 'всем'}]"
        
        if tag not in stats_grouped:
            stats_grouped[tag] = {}
            
        stats_grouped[tag][key] = stats_grouped[tag].get(key, 0) + 1


    materials_text = "📁 <b>МАТЕРИАЛЫ В БАЗЕ</b>\n\n"
    for tag in sorted(stats_grouped.keys()):
        materials_text += f"\n<b>#{tag.upper()}:</b>\n"
        for key, count in stats_grouped[tag].items():
            materials_text += f"  • {key}: {count} шт.\n"
    
    await message.answer(materials_text, parse_mode="HTML")
    
@dp.message(Command("admin_menu"))
async def cmd_admin_menu(message: types.Message):
    """Показывает администратору меню со всеми доступными разделами (тегами)."""
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Доступ запрещен.")
    
    await message.answer(
        "🛠️ <b>АДМИН-ПАНЕЛЬ:</b> Выберите раздел (тег) для загрузки или удаления материалов.",
        reply_markup=get_admin_all_tags_menu(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith('select_admin_tag__'))
async def show_admin_menu_for_tag(callback: types.CallbackQuery):
    """Обрабатывает выбор тега из меню всех разделов и показывает кнопки админ-действий."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен.")
        return
        
    tag = callback.data.split('__')[1]
    
    await callback.message.edit_text(
        f"<b>АДМИН-ПАНЕЛЬ:</b> Действия для раздела <b>#{tag}</b>",
        reply_markup=get_admin_menu(tag),
        parse_mode="HTML"
    )
    await callback.answer()
@dp.message(F.text == "✉️ Обратная связь")
async def feedback_handler(message: types.Message, state: FSMContext):
    """Начало процесса отправки обратной связи."""
    await message.answer(
        "📝 <b>Обратная связь</b>\n\n"
        "Отправьте ваше сообщение, вопрос, предложение или жалобу.\n"
        "Вы можете отправить:\n"
        "• Текст\n"
        "• Фото\n"
        "• Документ\n"
        "• Видео\n\n"
        "Для отмены используйте /start или /cancel",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    await state.set_state(FeedbackStates.waiting_for_feedback_message)


@dp.message(FeedbackStates.waiting_for_feedback_message, F.text | F.photo | F.document | F.video | F.audio | F.voice)
async def process_feedback_message(message: types.Message, state: FSMContext):
    """Обработка сообщения обратной связи и пересылка админам."""
    user_id = message.from_user.id
    
    # Проверка на отмену
    if message.text and (message.text.lower() == '/start' or message.text.lower() == '/cancel'):
        await state.clear()
        user_data = await db.get_user(user_id)
        user_course = user_data['course'] if user_data else None
        return await message.answer(
            "Отправка сообщения отменена.",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id)
        )
    
    # Получаем информацию о пользователе
    user_data = await db.get_user(user_id)
    username = message.from_user.username or "Нет username"
    full_name = message.from_user.full_name
    course = user_data['course'] if user_data else "Не указан"
    group = GROUPS.get(user_data['group_lang'], "Не указана") if user_data else "Не указана"
    
    # Формируем информацию о пользователе
    user_info = (
        f"📩 <b>НОВОЕ СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ</b>\n\n"
        f"👤 <b>Имя:</b> {full_name}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"📱 <b>Username:</b> @{username}\n"
        f"📚 <b>Курс:</b> {course}\n"
        f"🌍 <b>Группа:</b> {group}\n"
        f"{'─' * 30}\n"
    )
    
    # Отправляем сообщение всем админам
    success_count = 0
    for admin_id in ADMIN_IDS:
        try:
            # Отправляем информацию о пользователе
            await bot.send_message(admin_id, user_info, parse_mode="HTML")
            
            # Пересылаем само сообщение
            await message.forward(admin_id)
            
            # Добавляем кнопку для быстрого ответа
            builder = InlineKeyboardBuilder()
            builder.button(text="✉️ Ответить пользователю", callback_data=f"reply_to_user__{user_id}")
            await bot.send_message(
                admin_id,
                f"{'─' * 30}",
                reply_markup=builder.as_markup()
            )
            
            success_count += 1
        except Exception as e:
            logger.error(f"Не удалось отправить feedback админу {admin_id}: {e}")
    
    # Уведомляем пользователя
    await state.clear()
    user_course = user_data['course'] if user_data else None
    
    if success_count > 0:
        await message.answer(
            "✅ <b>Ваше сообщение отправлено!</b>\n\n"
            "Администратор получил ваше обращение и свяжется с вами в ближайшее время.",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Произошла ошибка при отправке сообщения. Попробуйте позже.",
            reply_markup=get_reply_main_menu_keyboard(user_course, user_id),
            parse_mode="HTML"
        )


# -------------------- 13. ОТВЕТ АДМИНА НА ОБРАТНУЮ СВЯЗЬ --------------------

@dp.callback_query(F.data.startswith('reply_to_user__'))
async def start_admin_reply(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса ответа админа пользователю."""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Доступ запрещен.")
        return
    
    target_user_id = int(callback.data.split('__')[1])
    
    # Проверяем, существует ли пользователь
    target_user = await db.get_user(target_user_id)
    if not target_user:
        await callback.answer("❌ Пользователь не найден в базе.", show_alert=True)
        return
    
    await state.update_data(reply_target_user_id=target_user_id)
    await state.set_state(AdminReplyStates.waiting_for_reply_message)
    
    await callback.message.answer(
        f"✉️ <b>Ответ пользователю</b>\n\n"
        f"👤 {target_user['full_name']}\n"
        f"🆔 <code>{target_user_id}</code>\n\n"
        f"Отправьте ваш ответ (текст, фото, документ и т.д.)\n\n"
        f"Для отмены используйте /start или /cancel",
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(AdminReplyStates.waiting_for_reply_message, F.text | F.photo | F.document | F.video | F.audio | F.voice)
async def process_admin_reply(message: types.Message, state: FSMContext):
    """Обработка и отправка ответа админа пользователю."""
    admin_id = message.from_user.id
    
    # Проверка на отмену
    if message.text and (message.text.lower() == '/start' or message.text.lower() == '/cancel'):
        await state.clear()
        user_data = await db.get_user(admin_id)
        user_course = user_data['course'] if user_data else None
        return await message.answer(
            "Отправка ответа отменена.",
            reply_markup=get_reply_main_menu_keyboard(user_course, admin_id)
        )
    
    data = await state.get_data()
    target_user_id = data.get('reply_target_user_id')
    
    if not target_user_id:
        await state.clear()
        return await message.answer("❌ Ошибка: не удалось определить получателя.")
    
    # Отправляем ответ пользователю
    try:
        # Отправляем заголовок
        await bot.send_message(
            target_user_id,
            "📬 <b>Ответ от администратора:</b>",
            parse_mode="HTML"
        )
        
        # Копируем сообщение админа пользователю
        await message.copy_to(target_user_id)
        
        await message.answer(
            "✅ <b>Ваш ответ успешно отправлен пользователю!</b>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Не удалось отправить ответ пользователю {target_user_id}: {e}")
        await message.answer(
            f"❌ <b>Ошибка отправки:</b>\n<code>{e}</code>\n\n"
            f"Возможно, пользователь заблокировал бота.",
            parse_mode="HTML"
        )
    
    await state.clear()
    user_data = await db.get_user(admin_id)
    user_course = user_data['course'] if user_data else None
    await message.answer(
        "Готово.",
        reply_markup=get_reply_main_menu_keyboard(user_course, admin_id)
    )

# -------------------- 11. ЗАПУСК --------------------
async def main():
    try:
        await db.init_pool()
    except Exception as e:
        logger.error(f"Не удалось подключиться к PostgreSQL: {e}")
        raise

    logger.info("Бот запущен с системой регистрации и PostgreSQL...")
    await dp.start_polling(bot)
    
async def start_all():
    # запускаем бота как задачу
    bot_task = asyncio.create_task(main())  # твой Telegram-бот
    # запускаем FastAPI сервер
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    # ждем оба процесса
    await asyncio.gather(bot_task, server_task)


if __name__ == "__main__":
    asyncio.run(start_all())
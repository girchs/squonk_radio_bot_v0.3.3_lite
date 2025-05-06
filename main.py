import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1

API_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "songs.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.reply("👋 Welcome to Squonk Radio V0.3.3 Lite!\nUse /setup in private chat or /play in group.")

@dp.message_handler(commands=['setup'])
async def cmd_setup(message: types.Message):
    await message.reply("📨 Send me `GroupID: <your_group_id>` first, then upload .mp3 files.")

@dp.message_handler(lambda m: m.text and m.text.startswith("GroupID:"))
async def handle_group_id(message: types.Message):
    group_id = message.text.replace("GroupID:", "").strip()
    data = load_data()
    data[group_id] = []
    save_data(data)
    await message.reply(f"✅ Group ID `{group_id}` saved. Now send me .mp3 files!")

@dp.message_handler(content_types=types.ContentType.DOCUMENT)
async def handle_mp3_upload(message: types.Message):
    user_data = load_data()
    group_ids = list(user_data.keys())
    if not group_ids:
        await message.reply("❗ Please first send `GroupID: <your_group_id>`")
        return

    group_id = group_ids[-1]
    file = await bot.get_file(message.document.file_id)
    file_path = file.file_path
    file_name = message.document.file_name
    await message.document.download(destination_file=file_name)

    try:
        audio = MP3(file_name)
        tags = ID3(file_name)
        title = tags.get('TIT2', TIT2(encoding=3, text='Unknown')).text[0]
        artist = tags.get('TPE1', TPE1(encoding=3, text='Unknown')).text[0]
    except:
        title = "Unknown"
        artist = "Unknown"

    user_data[group_id].append({"file_id": message.document.file_id, "title": title, "artist": artist})
    save_data(user_data)
    await message.reply(f"✅ Saved `{title}` by `{artist}` for group {group_id}")

@dp.message_handler(commands=['play'])
async def cmd_play(message: types.Message):
    group_id = str(message.chat.id)
    data = load_data()
    if group_id not in data or not data[group_id]:
        await message.reply("❌ No songs found for this group.")
        return

    song = data[group_id][0]
    keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("▶️ Next", callback_data="next")
    )
    await bot.send_audio(message.chat.id, song["file_id"], caption=f"🎵 {song['title']} - {song['artist']}", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "next")
async def next_song(callback_query: types.CallbackQuery):
    group_id = str(callback_query.message.chat.id)
    data = load_data()
    if group_id in data and data[group_id]:
        data[group_id].append(data[group_id].pop(0))
        save_data(data)
    await cmd_play(callback_query.message)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

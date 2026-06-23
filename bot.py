# bot.py
import asyncio
import re
import hashlib
import os
import sys
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

# ===== 🔐 YOUR DETAILS =====
API_ID = int(os.environ.get("API_ID", 37836508))
API_HASH = os.environ.get("API_HASH", "5b539a894960ce38914c7205d5ed5418")
STRING_SESSION = os.environ.get("STRING_SESSION", "1BVtsOLsBu21GjA1fzHOFNlKnJGtYV-5pQmsec1ZofZIMwL8ZbQlQmqoAoJFCVBoteCwrsAMKe64ChhDAV2nB-M3mhcLN-S1KOzX6x5woz0VXZkNHp8KBYW9NvMZKPsFBBGn-ezChCyf7DiY9iDtfsnLT-4StOqplQw15yTUFTMUb4Kx2jN6RgIKFIwzkLsksBLKzlSir_q17bvdlqxSkJG9f6RTggRCFoJZnIOGuCHuQ7R6kaAXYvHVghhBgRkBYqiSAtj8694fzZAMfzzPyg94psHk1aPGQH8BjVHTr7Gw7nES5lWoVj2Mhg-UIpFW7OQS28YEiEYt0CLC0vpJ8qm_N6Yp9M1E=")

# 📢 CHANNELS (Use environment variables)
SOURCE_CHANNEL = int(os.environ.get("SOURCE_CHANNEL", -1003984452893))
TARGET_CHANNEL = int(os.environ.get("TARGET_CHANNEL", -1003640490073))

# ⏱️ TIMINGS
DELETE_DELAY = int(os.environ.get("DELETE_DELAY", 30))
GAP_DELAY = int(os.environ.get("GAP_DELAY", 30))

# 🚫 BLOCKED BINS
BLOCK_BINS = {
    "440066","453201","497171","431195","411146","525849","453924",
    "492913","454638","465865","461785","437401","404924","455600",
    "483583","445444","450065","428550","402911","421494","486483",
    "511796","520976","516921","554042","400843","522401","417363",
    "530436","441014","545147","540132","535081","5392047","543484"
}

# ===== SETUP =====
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# Load already posted CCs
posted = set()
dup_file = "posted_cc.txt"
if os.path.exists(dup_file):
    with open(dup_file, "r") as f:
        posted = set(line.strip() for line in f)

# CC Regex
cc_regex = re.compile(
    r"\b((4\d{12}(?:\d{3})?)|(5[1-5]\d{14}))\s*\|\s*\d{1,2}\s*\|\s*\d{2,4}\s*\|\s*\d{3,4}\b"
)

msg_counter = 0
lock = asyncio.Lock()

@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    global msg_counter
    
    if not event.text:
        return
    
    print(f"\n📥 New message received!")
    
    for match in cc_regex.finditer(event.text):
        full_cc = match.group(0).replace(" ", "")
        card_number = full_cc.split('|')[0].strip()
        prefix6 = card_number[:6]
        
        if prefix6 in BLOCK_BINS:
            print(f"⛔ Skipped blocked BIN: {prefix6}")
            continue
        
        card_hash = hashlib.md5(card_number.encode()).hexdigest()
        if card_hash in posted:
            print(f"♻️ Duplicate CC, skipping...")
            continue
        
        async with lock:
            posted.add(card_hash)
            with open(dup_file, "a") as f:
                f.write(card_hash + "\n")
            
            try:
                msg = await client.send_message(TARGET_CHANNEL, f"/chk {full_cc}")
                msg_counter += 1
                print(f"✅ SENT: {full_cc[:10]}*** | Total: {msg_counter}")
                
                await asyncio.sleep(DELETE_DELAY)
                try:
                    await msg.delete()
                    print(f"🗑️ Deleted message")
                except:
                    pass
                
                await asyncio.sleep(GAP_DELAY)
                
            except FloodWaitError as e:
                print(f"⏳ Flood wait: {e.seconds} seconds")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Error: {e}")

async def main():
    await client.start()
    me = await client.get_me()
    print(f"🤖 Bot Started as: {me.first_name} (@{me.username})")
    print(f"📡 Monitoring source channel: {SOURCE_CHANNEL}")
    print(f"🎯 Forwarding to target channel: {TARGET_CHANNEL}")
    print("🚀 Bot is running... Press Ctrl+C to stop\n")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

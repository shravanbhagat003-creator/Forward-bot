# bot_fixed_final.py
import asyncio
import re
import hashlib
import os
import sys
import json
import random
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, RPCError
from telethon.network import ConnectionTcpAbridged

# ===== 🔐 YOUR DETAILS =====
API_ID = 34783446
API_HASH = "c1da051b38797498a32805f762c36bd3"
STRING_SESSION = "1BVtsOHwBu7dY3DEKKEYn08XxluMt9U-7qS5MI77ucxZK1y_HF9oMVdRsqoFwmc_g6FUSdoPmCmaUsw9Qte7K6DBFe4BkAyxXSgCQG0uc-9Wjf-QqBWhRbeSIywYCkLOscRyHWFVQBfXonfgGFqgfqLCigRgogdT-wrYVtl2t4GURGRf5LBOCUii35hCef3CuP5pc3TyzQRWqSH7IAC0Zpdqr-zTT3Gr7j8LrujGlhPn6rB884AK0VeZPIjFJC9EezjjZNTjetTWXN5sw7KYAJzqurK0cPZOX4dbgJzj8BeYy5zhmScCBWQCBwVsWHNPpXH0uh0rUjwhjjkjCT8bRsehhR-L1O6M="

# 📢 CHANNELS
SOURCE_CHANNEL = -1004438106656
TARGET_CHANNEL = -1003783045906

# ⏱️ TIMINGS
DELETE_DELAY = 25
GAP_DELAY = 25

# 🚫 BLOCKED BINS
BLOCK_BINS = {
    "440066","453201","497171","431195","411146","525849","453924",
    "492913","454638","465865","461785","437401","404924","455600",
    "483583","445444","450065","428550","402911","421494","486483",
    "511796","520976","516921","554042","400843","522401","417363",
    "530436","441014","545147","540132","535081","5392047","543484"
}

# ===== SESSION MANAGEMENT =====
# Unique session file har baar alag
SESSION_ID = random.randint(1000, 9999)
SESSION_FILE = f"session_{SESSION_ID}.json"
DEVICE_NAME = f"iPhone_{random.randint(10000, 99999)}"

def save_session(session_string):
    """Save session with unique ID"""
    data = {
        "session": session_string,
        "device": DEVICE_NAME,
        "timestamp": datetime.now().isoformat()
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)
    print(f"💾 Session saved: {SESSION_FILE}")

def load_session():
    """Load session from file"""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                return data.get("session")
        except:
            pass
    return None

# ===== CREATE CLIENT WITH UNIQUE DEVICE =====
# Try saved session first
saved = load_session()
if saved:
    print(f"🔄 Using saved session from: {SESSION_FILE}")
    STRING_SESSION = saved
else:
    save_session(STRING_SESSION)

# Client with UNIQUE device ID
client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    connection=ConnectionTcpAbridged,
    connection_retries=3,
    retry_delay=1,
    auto_reconnect=False,  # Manual control
    flood_sleep_threshold=60,
    device_model=DEVICE_NAME,
    system_version=f"iOS_{random.randint(15, 18)}.{random.randint(0, 9)}"
)

print(f"📱 Device: {DEVICE_NAME}")
print(f"📁 Session: {SESSION_FILE}")

# Load posted CCs
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
is_connected = False

@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    global msg_counter
    
    if not event.text:
        return
    
    print(f"\n📥 Message at {datetime.now().strftime('%H:%M:%S')}")
    
    for match in cc_regex.finditer(event.text):
        full_cc = match.group(0).replace(" ", "")
        card_number = full_cc.split('|')[0].strip()
        prefix6 = card_number[:6]
        
        if prefix6 in BLOCK_BINS:
            print(f"⛔ Blocked BIN: {prefix6}")
            continue
        
        card_hash = hashlib.md5(card_number.encode()).hexdigest()
        if card_hash in posted:
            print(f"♻️ Duplicate")
            continue
        
        async with lock:
            posted.add(card_hash)
            with open(dup_file, "a") as f:
                f.write(card_hash + "\n")
            
            try:
                msg = await client.send_message(TARGET_CHANNEL, f"/br {full_cc}")
                msg_counter += 1
                print(f"✅ SENT: {full_cc[:10]}*** | Total: {msg_counter}")
                
                await asyncio.sleep(DELETE_DELAY)
                try:
                    await msg.delete()
                    print(f"🗑️ Deleted")
                except:
                    pass
                
                await asyncio.sleep(GAP_DELAY)
                
            except FloodWaitError as e:
                print(f"⏳ Flood: {e.seconds}s")
                await asyncio.sleep(e.seconds + 5)
            except RPCError as e:
                print(f"⚠️ RPC: {e}")
            except Exception as e:
                print(f"❌ Error: {e}")

async def start_bot():
    """Start with error handling"""
    try:
        print("🔄 Connecting...")
        await client.start()
        
        me = await client.get_me()
        print(f"✅ Connected: {me.first_name} (@{me.username})")
        
        # Save fresh session
        save_session(client.session.save())
        
        return True
        
    except Exception as e:
        print(f"❌ Start failed: {e}")
        
        # Delete corrupted session
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            print(f"🗑️ Deleted: {SESSION_FILE}")
        
        print("\n🔄 Generate NEW session:")
        print("python generate_session.py")
        return False

async def main():
    print("\n" + "="*50)
    print("🤖 CC FORWARDER BOT")
    print("="*50)
    print(f"📱 Device: {DEVICE_NAME}")
    print(f"📁 Session: {SESSION_FILE}")
    print("="*50 + "\n")
    
    if not await start_bot():
        sys.exit(1)
    
    print(f"📡 Source: {SOURCE_CHANNEL}")
    print(f"🎯 Target: {TARGET_CHANNEL}")
    print("🚀 Running... Press Ctrl+C\n")
    
    try:
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Disconnected: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
    except Exception as e:
        print(f"❌ Fatal: {e}")
        sys.exit(1)

# bot_updated.py
import asyncio
import re
import hashlib
import os
import sys
import json
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
DELETE_DELAY = 20
GAP_DELAY = 20

# 🚫 BLOCKED BINS
BLOCK_BINS = {
    "440066","453201","497171","431195","411146","525849","453924",
    "492913","454638","465865","461785","437401","404924","455600",
    "483583","445444","450065","428550","402911","421494","486483",
    "511796","520976","516921","554042","400843","522401","417363",
    "530436","441014","545147","540132","535081","5392047","543484"
}

# ===== SESSION MANAGEMENT =====
SESSION_FILE = "session_data.json"

def save_session(session_string):
    """Save session to file"""
    data = {
        "session": session_string,
        "timestamp": datetime.now().isoformat()
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)
    print("💾 Session saved to file")

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

# ===== SETUP WITH FIXES =====
# Try to load saved session first
saved_session = load_session()
if saved_session and saved_session != STRING_SESSION:
    print("🔄 Using saved session from file")
    STRING_SESSION = saved_session
else:
    # Save current session
    save_session(STRING_SESSION)

# Create client with better settings
client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    connection=ConnectionTcpAbridged,
    connection_retries=10,
    retry_delay=2,
    auto_reconnect=True,
    flood_sleep_threshold=60,
    device_model="iPhone 15 Pro",
    system_version="iOS 17.2"
)

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
reconnect_attempts = 0
max_reconnect = 5

@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    global msg_counter
    
    if not event.text:
        return
    
    print(f"\n📥 New message received at {datetime.now().strftime('%H:%M:%S')}")
    
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
            
            # Retry logic for sending
            for attempt in range(3):
                try:
                    msg = await client.send_message(TARGET_CHANNEL, f"/br {full_cc}")
                    msg_counter += 1
                    print(f"✅ SENT: {full_cc[:10]}*** | Total: {msg_counter}")
                    
                    await asyncio.sleep(DELETE_DELAY)
                    try:
                        await msg.delete()
                        print(f"🗑️ Deleted message")
                    except:
                        pass
                    
                    await asyncio.sleep(GAP_DELAY)
                    break  # Success, exit retry loop
                    
                except FloodWaitError as e:
                    print(f"⏳ Flood wait: {e.seconds} seconds")
                    await asyncio.sleep(e.seconds + 5)
                except RPCError as e:
                    print(f"⚠️ RPC Error (attempt {attempt+1}/3): {e}")
                    if attempt < 2:
                        await asyncio.sleep(5 * (attempt + 1))
                    else:
                        print(f"❌ Failed after 3 attempts")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    if attempt < 2:
                        await asyncio.sleep(3)
                    else:
                        print(f"❌ Failed after 3 attempts")

async def reconnect():
    """Reconnect logic"""
    global reconnect_attempts
    
    while reconnect_attempts < max_reconnect:
        try:
            print(f"🔄 Reconnection attempt {reconnect_attempts + 1}/{max_reconnect}")
            await client.disconnect()
            await asyncio.sleep(5)
            await client.connect()
            
            # Test connection
            await client.get_me()
            print("✅ Reconnected successfully!")
            reconnect_attempts = 0
            return True
            
        except Exception as e:
            reconnect_attempts += 1
            print(f"❌ Reconnect failed: {e}")
            await asyncio.sleep(10 * reconnect_attempts)
    
    return False

async def main():
    global reconnect_attempts
    
    while True:
        try:
            print("🚀 Starting bot...")
            await client.start()
            
            # Save session after successful start
            save_session(client.session.save())
            
            me = await client.get_me()
            print(f"🤖 Bot Started as: {me.first_name} (@{me.username})")
            print(f"📡 Monitoring: {SOURCE_CHANNEL}")
            print(f"🎯 Forwarding to: {TARGET_CHANNEL}")
            print(f"💾 Session saved to: {SESSION_FILE}")
            print("🚀 Bot is running... Press Ctrl+C to stop\n")
            
            await client.run_until_disconnected()
            
        except ConnectionError as e:
            print(f"⚠️ Connection lost: {e}")
            if await reconnect():
                continue
            else:
                print("❌ Max reconnection attempts reached")
                break
                
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            
            # Check if it's session error
            if "authorization key" in str(e).lower() or "invalid" in str(e).lower():
                print("🔄 Session invalid, generating new session...")
                # Delete old session file
                if os.path.exists(SESSION_FILE):
                    os.remove(SESSION_FILE)
                print("📝 Please generate new session using generate_session.py")
                sys.exit(1)
            
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
        # Save session on exit
        try:
            save_session(client.session.save())
        except:
            pass
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

import asyncio
import re
import hashlib
import os
import sys
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, RPCError

# ===== LOGGING SETUP =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ===== 🔐 YOUR DETAILS =====
API_ID = int(os.environ.get("API_ID", 34783446))
API_HASH = os.environ.get("API_HASH", "c1da051b38797498a32805f762c36bd3")

# 👇 Get from environment variable for security
STRING_SESSION = os.environ.get("STRING_SESSION", "1BVtsOMQBu6skYI-cZ1b_Pyl3gwKURtxtEkbntFUwZhMsxHQkfgwnCwb4O2qywWeJSFaJoNqJHcLJuMsWgcZljeg8C4TweHoVY-mGfi85vNnoiJmf8kB99_95ulwTB9yh8G5AW_9wCyTChtLTJxUeoaO2JAnJWwMVYFMFUDIUqVlEo-AXBLNPKWyYB3DLPYiRWgbDBP5V9Jpwgz9iIoQD-UlSqSSzvJa0VEFgPqEGN8iIhTtIN53kqVL9riqfHuY3aBgATpyYty3jdpM8q5BsL-YmCmlXk22Vxy4VHn3ZIZ_7UpDf20EPZ-HFHGtUXrK1PhD-9w9uzdm7J7K4Eo77paDn4DYUUKA=")

# 📢 CHANNELS - Use environment variables
SOURCE_CHANNEL = int(os.environ.get("SOURCE_CHANNEL", -1004438106656))
TARGET_CHANNEL = int(os.environ.get("TARGET_CHANNEL", -1003783045906))

# ⏱️ TIMINGS - Can be set via env
DELETE_DELAY = int(os.environ.get("DELETE_DELAY", 10))
GAP_DELAY = int(os.environ.get("GAP_DELAY", 10))

# 🚫 BLOCKED BINS
BLOCK_BINS = {
    "440066","453201","497171","431195","411146","525849","453924",
    "492913","454638","465865","461785","437401","404924","455600",
    "483583","445444","450065","428550","402911","421494","486483",
    "511796","520976","516921","554042","400843","522401","417363",
    "530436","441014","545147","540132","535081","5392047","543484",
    "559728","457226","466582","485358","592333","528181","431322",
    "550568","465487","462436","417878","404247","516815","468040",
    "532541","457224","539305","430451","521152","489364","554702",
    "549041","483074","457227","543891","444111","466582","489358",
    "408383","419327","412998","554027","412329","440768","401711"
}

# ===== SETUP =====
client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# Load already posted CCs
posted = set()
dup_file = "posted_cc.txt"

# Create data directory if it doesn't exist
if not os.path.exists("data"):
    os.makedirs("data")
dup_file = os.path.join("data", "posted_cc.txt")

if os.path.exists(dup_file):
    with open(dup_file, "r") as f:
        posted = set(line.strip() for line in f)
    logger.info(f"Loaded {len(posted)} existing CCs")

# Fixed CC Regex - better pattern
cc_regex = re.compile(
    r'(\d{16})\s*\|\s*(\d{1,2})\s*\|\s*(\d{2,4})\s*\|\s*(\d{3,4})',
    re.IGNORECASE
)

# Alternative simpler regex if above doesn't work
simple_cc_regex = re.compile(
    r'(\d{15,16})\s*[|/]\s*(\d{1,2})\s*[|/]\s*(\d{2,4})\s*[|/]\s*(\d{3,4})',
    re.IGNORECASE
)

msg_counter = 0
lock = asyncio.Lock()

@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    global msg_counter
    
    if not event.text:
        return
    
    logger.info(f"📥 New message received!")
    
    # Try both regex patterns
    matches = cc_regex.findall(event.text)
    if not matches:
        matches = simple_cc_regex.findall(event.text)
    
    if not matches:
        logger.debug("⚠️ No CC found in message")
        return
    
    for match in matches:
        try:
            # Handle different match formats
            if len(match) >= 4:
                card_number = match[0].strip()
                month = match[1].strip()
                year = match[2].strip()
                cvv = match[3].strip()
                
                # Format CC
                full_cc = f"{card_number}|{month}|{year}|{cvv}"
                prefix6 = card_number[:6]
                
                logger.info(f"🔍 Found CC: {card_number[:6]}*** | Exp: {month}/{year}")
                
                # Check if BIN is blocked
                if prefix6 in BLOCK_BINS:
                    logger.info(f"⛔ Skipped blocked BIN: {prefix6}")
                    continue
                
                # Check for duplicate
                card_hash = hashlib.md5(card_number.encode()).hexdigest()
                if card_hash in posted:
                    logger.info(f"♻️ Duplicate CC, skipping...")
                    continue
                
                async with lock:
                    posted.add(card_hash)
                    with open(dup_file, "a") as f:
                        f.write(card_hash + "\n")
                    
                    # Send to target channel with retry logic
                    for attempt in range(3):
                        try:
                            msg = await client.send_message(TARGET_CHANNEL, f"/br {full_cc}")
                            msg_counter += 1
                            logger.info(f"✅ SENT: {full_cc[:10]}*** | Total: {msg_counter}")
                            
                            # Delete message after delay
                            await asyncio.sleep(DELETE_DELAY)
                            try:
                                await msg.delete()
                                logger.info(f"🗑️ Deleted message")
                            except Exception as e:
                                logger.warning(f"⚠️ Could not delete: {e}")
                            
                            await asyncio.sleep(GAP_DELAY)
                            break  # Success, exit retry loop
                            
                        except FloodWaitError as e:
                            logger.warning(f"⏳ Flood wait: {e.seconds} seconds")
                            await asyncio.sleep(e.seconds + 5)
                        except RPCError as e:
                            logger.error(f"⚠️ RPC Error (attempt {attempt+1}/3): {e}")
                            if attempt < 2:
                                await asyncio.sleep(5 * (attempt + 1))
                        except Exception as e:
                            logger.error(f"❌ Error sending: {e}")
                            if attempt < 2:
                                await asyncio.sleep(3)
                        
            else:
                logger.warning(f"⚠️ Invalid match format: {match}")
                
        except Exception as e:
            logger.error(f"❌ Error processing CC: {e}")
            continue

async def main():
    try:
        logger.info("🚀 Starting bot...")
        await client.start()
        
        # Verify connection
        me = await client.get_me()
        logger.info(f"🤖 Bot Started as: {me.first_name} (@{me.username})")
        logger.info(f"📡 Monitoring source channel: {SOURCE_CHANNEL}")
        logger.info(f"🎯 Forwarding to target channel: {TARGET_CHANNEL}")
        logger.info("🚀 Bot is running... Press Ctrl+C to stop")
        
        # Test if we can access channels
        try:
            await client.get_entity(SOURCE_CHANNEL)
            logger.info("✅ Source channel accessible")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Source channel might not be accessible: {e}")
        
        try:
            await client.get_entity(TARGET_CHANNEL)
            logger.info("✅ Target channel accessible")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Target channel might not be accessible: {e}")
        
        await client.run_until_disconnected()
        
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    try:
        # Run the client
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

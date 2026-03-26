from flask import Flask, request
import json, os, requests, time, random, string, asyncio, threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)

# ========= CONFIG =========
BOT_TOKEN = "8637581331:AAGn9lI6do6CfAsqMYCL2HgH8Xfd9RQ1BS8"
ADMIN_ID = 7634132457

API_BASE = "https://ff-bind-rohit-l.vercel.app"
API_KEY = "12345"

app = Flask(__name__)
bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ========= FILE =========
DATA_FILE = "data.json"

def load():
    if not os.path.exists(DATA_FILE):
        return {
            "keys": {},
            "users": {},
            "emails": {},
            "banned": [],
            "usernames": {}
        }
    return json.load(open(DATA_FILE))

def save():
    json.dump(data, open(DATA_FILE, "w"), indent=2)

data = load()

# ========= UTIL =========
def pro(msg):
    return f"\n🔥 PRO PANEL\n\n{msg}"

def gen_key(hours):
    key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    exp = int(time.time()) + (hours * 3600)
    data["keys"][key] = exp
    save()
    return key

def is_banned(uid):
    return int(uid) in set(data.get("banned", []))

def check_user(uid):
    if uid == ADMIN_ID:
        return True

    exp = data["users"].get(str(uid))

    if not exp:
        return False

    if time.time() > exp:
        return False

    return True

def remaining(exp):
    left = int(exp - time.time())

    if left <= 0:
        return "Expired"

    h = left // 3600
    m = (left % 3600) // 60
    s = left % 60

    return f"{h}h {m}m {s}s"

def call_api(endpoint, token):
    try:
        url = f"{API_BASE}/{endpoint}?token={token}&key={API_KEY}"
        return requests.get(url, timeout=10).json()
    except Exception as e:
        return {"error": str(e)}

# ========= ADMIN LOG =========
async def log(update, context):
    user = update.effective_user
    await context.bot.send_message(
        ADMIN_ID,
        f"👤 USER\nID: {user.id}\nUser: @{user.username}\nMsg: {update.message.text}"
    )

# ========= COMMANDS =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_banned(uid):
        return await update.message.reply_text("🚫 You are banned")

    if check_user(uid):
        return await panel(update, context)

    await update.message.reply_text("🔑 Enter Key:")

async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    hours = int(context.args[0])
    key = gen_key(hours)
    await update.message.reply_text(pro(f"🔑 Key: {key}\n⏳ {hours}h"))

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    if is_banned(uid):
        return await update.message.reply_text("🚫 You are banned")

    if not check_user(uid):
        return await update.message.reply_text("❌ No Access")

    if uid == ADMIN_ID:
        kb = [
            ["🔑 Generate Key", "⛔ Ban User"],
            ["✅ Unban User", "📊 User Info"]
        ]
    else:
        kb = [
            ["🔍 Check Bind", "🔗 Check Links"],
            ["❌ Cancel Bind", "⚡ Revoke Token"],
            ["📩 Bind Email"]
        ]

    await update.message.reply_text(
        pro("Select Option"),
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True)
    )

# ========= HANDLER =========
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    # save username
    data["usernames"][str(uid)] = update.effective_user.username
    save()

    await log(update, context)

    if is_banned(uid):
        return await update.message.reply_text("🚫 You are banned")

    # ===== ADMIN =====
    if uid == ADMIN_ID:

        if text == "🔑 Generate Key":
            context.user_data["action"] = "genkey"
            return await update.message.reply_text("Enter hours:")

        if context.user_data.get("action") == "genkey":
            key = gen_key(int(text))
            context.user_data["action"] = None
            return await update.message.reply_text(pro(f"Key: {key}"))

        if text == "⛔ Ban User":
            context.user_data["action"] = "ban"
            return await update.message.reply_text("Enter ID or @username:")

        if context.user_data.get("action") == "ban":
            target = text

            if target.isdigit():
                data["banned"].append(int(target))
            else:
                for uid_, uname in data["usernames"].items():
                    if uname and uname.lower() == target.replace("@","").lower():
                        data["banned"].append(int(uid_))

            data["banned"] = list(set(data["banned"]))
            save()
            context.user_data["action"] = None
            return await update.message.reply_text("🚫 Banned")

        if text == "✅ Unban User":
            context.user_data["action"] = "unban"
            return await update.message.reply_text("Enter ID or @username:")

        if context.user_data.get("action") == "unban":
            target = text

            if target.isdigit():
                uid2 = int(target)
                if uid2 in data["banned"]:
                    data["banned"].remove(uid2)
            else:
                for uid_, uname in data["usernames"].items():
                    if uname and uname.lower() == target.replace("@","").lower():
                        if int(uid_) in data["banned"]:
                            data["banned"].remove(int(uid_))

            save()
            context.user_data["action"] = None
            return await update.message.reply_text("✅ Unbanned")

    # ===== KEY SYSTEM =====
    if text in data["keys"]:
        exp = data["keys"].pop(text)
        data["users"][str(uid)] = exp
        save()
        return await update.message.reply_text(
            pro(f"✅ Key Activated\n⏳ {remaining(exp)}")
        )

    if not check_user(uid):
        return await update.message.reply_text("🔑 Invalid Key")

    # ===== USER =====
    if text == "🔍 Check Bind":
        context.user_data["action"] = "bind"
        return await update.message.reply_text("Send Token:")

    elif text == "🔗 Check Links":
        context.user_data["action"] = "links"
        return await update.message.reply_text("Send Token:")

    action = context.user_data.get("action")

    if action in ["bind", "links"]:
        res = call_api(action, text)
        context.user_data["action"] = None
        return await update.message.reply_text(pro(str(res)))

# ========= REGISTER =========
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("genkey", genkey))
bot_app.add_handler(CommandHandler("panel", panel))
bot_app.add_handler(MessageHandler(filters.TEXT, handle))

# ========= WEBHOOK =========
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        print("Webhook hit")

        data_update = request.get_json(force=True)
        update = Update.de_json(data_update, bot_app.bot)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.process_update(update))
        loop.close()

        return "ok"
    except Exception as e:
        print("Webhook Error:", e)
        return "error"

@app.route("/", methods=["GET"])
def home():
    return "Bot Running", 200

# ========= RUN =========
async def main():
    await bot_app.initialize()
    await bot_app.start()

def run_bot():
    asyncio.run(main())

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

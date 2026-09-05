import sqlite3
import telebot
from telebot import types

BOT_TOKEN = "7657021317:AAH0yKQqbrQw2OMnxJCokSP9jYXtTi_BKyw"
ADMIN_ID = 7161571409

REQUIRED_CHANNELS = [
    {"name": "Proof Channel", "username": "@botlikeproof"},
    {"name": "Earning Channel 1", "username": "@eraningwithask"},
    {"name": "Earning Channel 2", "username": "@eraningwithask9"}
]

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = bot.get_me().username

def init_db():
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, coins INTEGER DEFAULT 30, referred_by INTEGER DEFAULT 0, is_verified INTEGER DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, channel_username TEXT, needed_joins INTEGER, current_joins INTEGER DEFAULT 0, status TEXT DEFAULT 'ACTIVE')")
    c.execute("CREATE TABLE IF NOT EXISTS history (user_id INTEGER, campaign_id INTEGER, UNIQUE(user_id, campaign_id))")
    c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('join_reward', 15)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('refer_reward', 20)")
    c.execute("INSERT OR IGNORE INTO settings VALUES ('cost_per_member', 15)")
    conn.commit()
    conn.close()

init_db()

def get_setting(key, default=15):
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def update_setting(key, value):
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))
    conn.commit()
    conn.close()

def get_coins(user_id):
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def check_all_required_channels(user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch["username"], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def force_join_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in REQUIRED_CHANNELS:
        clean = ch["username"].replace("@", "")
        markup.add(types.InlineKeyboardButton(f"📢 Join {ch['name']}", url=f"https://t.me/{clean}"))
    markup.add(types.InlineKeyboardButton("✨ Verify & Unlock Bot", callback_data="check_force_join"))
    return markup

def main_menu(user_id):
    coins = get_coins(user_id)
    join_reward = get_setting("join_reward", 15)
    refer_reward = get_setting("refer_reward", 20)
    cost = get_setting("cost_per_member", 15)

    text = (
        "╔════════════════════════╗\n"
        "   ⚡ <b>PROMO BOOST NETWORK</b> ⚡\n"
        "╚════════════════════════╝\n"
        f"💎 <b>Wallet Balance:</b> <code>{coins} Coins</code>\n"
        "────────────────────────\n"
        f"🎁 <b>Per Join:</b> <code>+{join_reward} Coins</code>\n"
        f"👥 <b>Per Refer:</b> <code>+{refer_reward} Coins</code>\n"
        f"🚀 <b>Promo Cost:</b> <code>{cost} Coins / Sub</code>\n"
        "────────────────────────\n"
        "<i>Apne channels promote karein aur organic members payein!</i>"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎯 Earn Coins", callback_data="earn_0"),
        types.InlineKeyboardButton("📢 Promote Channel", callback_data="add_campaign"),
        types.InlineKeyboardButton("👥 Refer & Earn", callback_data="refer_earn"),
        types.InlineKeyboardButton("📊 My Dashboard", callback_data="my_stats"),
        types.InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_menu")
    )
    if int(user_id) == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚡ Master Admin Console ⚡", callback_data="admin_master"))
    return text, markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    name = message.from_user.first_name
    referrer = 0
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            p_ref = int(parts[1].replace("ref_", ""))
            if p_ref != uid:
                referrer = p_ref
        except ValueError:
            pass

    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT user_id, is_verified FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO users (user_id, name, coins, referred_by, is_verified) VALUES (?, ?, 30, ?, 0)", (uid, name, referrer))
        conn.commit()
    conn.close()

    if not check_all_required_channels(uid):
        text = (
            "🔒 <b>ACCESS RESTRICTED!</b>\n\n"
            "Bot ke sabhi features use karne ke liye pehle niche diye gaye <b>Mandatory Channels</b> join karein:\n"
        )
        bot.send_message(message.chat.id, text, reply_markup=force_join_markup())
        return

    text, markup = main_menu(uid)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check_force_join")
def verify_force_join_handler(call):
    uid = call.from_user.id
    if check_all_required_channels(uid):
        conn = sqlite3.connect("promotion.db")
        c = conn.cursor()
        c.execute("SELECT is_verified, referred_by FROM users WHERE user_id = ?", (uid,))
        user_data = c.fetchone()
        if user_data and user_data[0] == 0:
            c.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (uid,))
            ref_by = user_data[1]
            if ref_by != 0:
                reward = get_setting("refer_reward", 20)
                c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (reward, ref_by))
                try:
                    bot.send_message(ref_by, f"🎉 <b>Referral Verified!</b>\nAapke dost ne join kiya: <b>+{reward} Coins</b> jud gaye!")
                except Exception:
                    pass
            conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ Verification Successful!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        text, markup = main_menu(uid)
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, "❌ Saare channels join nahi hue! Pehle join karein.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "refresh_menu")
def refresh_callback(call):
    if not check_all_required_channels(call.from_user.id):
        bot.send_message(call.message.chat.id, "⚠️ Pehle channels join karein:", reply_markup=force_join_markup())
        return
    text, markup = main_menu(call.from_user.id)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "refer_earn")
def refer_earn_callback(call):
    uid = call.from_user.id
    reward = get_setting("refer_reward", 20)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
    text = (
        "╔════════════════════════╗\n"
        "   👥 <b>REFER & EARN SYSTEM</b>\n"
        "╚════════════════════════╝\n"
        f"🎁 <b>Per Verified Referral:</b> <code>+{reward} Coins</code>\n"
        "────────────────────────\n"
        "🔗 <b>Aapka Private Invite Link:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "<i>Apne link ko doston ke sath share karein aur unlimited coins earn karein!</i>"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("earn_"))
def earn_channel_task(call):
    offset = int(call.data.split("_")[1])
    uid = call.from_user.id
    join_reward = get_setting("join_reward", 15)

    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    query = "SELECT id, channel_username FROM campaigns WHERE status = 'ACTIVE' AND owner_id != ? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id = ?) LIMIT 1 OFFSET ?"
    c.execute(query, (uid, uid, offset))
    task = c.fetchone()

    c.execute("SELECT COUNT(*) FROM campaigns WHERE status = 'ACTIVE' AND owner_id != ? AND id NOT IN (SELECT campaign_id FROM history WHERE user_id = ?)", (uid, uid))
    total_available = c.fetchone()[0]
    conn.close()

    if not task or offset >= total_available:
        empty_text = (
            "╔════════════════════════╗\n"
            "   ✨ <b>ALL TASKS COMPLETED</b> ✨\n"
            "╚════════════════════════╝\n"
            "Filhal sabhi available channels complete ho chuke hain.\n"
            "Naye campaigns aate hi yahan live ho jayenge!"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="refresh_menu"))
        bot.edit_message_text(empty_text, call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    camp_id, ch_user = task
    clean_handle = ch_user.replace("@", "")
    task_card = (
        f"🎯 <b>TASK QUEUE: [{offset + 1}/{total_available}]</b>\n"
        "────────────────────────\n"
        f"📢 <b>Channel:</b> <code>@{clean_handle}</code>\n"
        f"💰 <b>Reward:</b> <code>+{join_reward} Coins</code>\n"
        "────────────────────────\n"
        "1. Open karke Channel join karein.\n"
        "2. Wapas aakar Verify par tap karein."
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 Open Channel", url=f"https://t.me/{clean_handle}"),
        types.InlineKeyboardButton("✅ Verify Join", callback_data=f"verify_{camp_id}_{clean_handle}_{offset}")
    )
    markup.add(
        types.InlineKeyboardButton("➡️ Next Channel", callback_data=f"earn_{offset + 1}"),
        types.InlineKeyboardButton("🔙 Back", callback_data="refresh_menu")
    )
    bot.edit_message_text(task_card, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("verify_"))
def verify_task_join(call):
    _, camp_id, clean_handle, offset = call.data.split("_")
    camp_id, offset = int(camp_id), int(offset)
    uid = call.from_user.id
    join_reward = get_setting("join_reward", 15)

    try:
        member = bot.get_chat_member(f"@{clean_handle}", uid)
        if member.status in ['member', 'administrator', 'creator']:
            conn = sqlite3.connect("promotion.db")
            c = conn.cursor()
            c.execute("SELECT 1 FROM history WHERE user_id = ? AND campaign_id = ?", (uid, camp_id))
            if c.fetchone():
                bot.answer_callback_query(call.id, "Reward pehle hi claim ho chuka hai!", show_alert=True)
                conn.close()
                return

            c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (join_reward, uid))
            c.execute("INSERT INTO history (user_id, campaign_id) VALUES (?, ?)", (uid, camp_id))
            c.execute("UPDATE campaigns SET current_joins = current_joins + 1 WHERE id = ?", (camp_id,))
            c.execute("SELECT owner_id, channel_username, needed_joins, current_joins FROM campaigns WHERE id = ?", (camp_id,))
            camp_info = c.fetchone()
            if camp_info:
                owner_id, ch_name, need, curr = camp_info
                if curr >= need:
                    c.execute("UPDATE campaigns SET status = 'COMPLETED' WHERE id = ?", (camp_id,))
                    try:
                        bot.send_message(
                            owner_id, 
                            f"🎉 <b>PROMOTION TARGET REACHED!</b>\n\n"
                            f"📢 Channel: <b>{ch_name}</b>\n"
                            f"👥 Joined: <b>{curr}/{need} Members</b>\n"
                            "Aapka campaign successfully finish ho chuka hai!"
                        )
                    except Exception:
                        pass
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, f"🎉 Verified! +{join_reward} Coins added!", show_alert=True)
            call.data = f"earn_{offset}"
            earn_channel_task(call)
        else:
            bot.answer_callback_query(call.id, "❌ Channel join nahi mila! Pehle join karein.", show_alert=True)
    except Exception:
        bot.answer_callback_query(call.id, "⚠️ Verification error. Channel settings check karein.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "add_campaign")
def add_campaign_start(call):
    uid = call.from_user.id
    cost = get_setting("cost_per_member", 15)
    if get_coins(uid) < cost:
        bot.answer_callback_query(call.id, f"Kam se kam {cost} coins chahiye!", show_alert=True)
        return
    text = (
        "⚙️ <b>PROMOTION SETUP:</b>\n"
        "────────────────────────\n"
        f"1. Bot <code>@{BOT_USERNAME}</code> ko channel me <b>ADMIN</b> banayein.\n"
        "2. Public Username format me bhejein (Example: <code>@MyChannel</code>):"
    )
    msg = bot.send_message(call.message.chat.id, text)
    bot.register_next_step_handler(msg, verify_channel_and_admin)

def verify_channel_and_admin(message):
    ch_user = message.text.strip()
    if not ch_user.startswith("@"):
        bot.send_message(message.chat.id, "❌ Format galat hai! '@' se start karein.")
        return
    try:
        bot_member = bot.get_chat_member(ch_user, bot.get_me().id)
        if bot_member.status != "administrator":
            bot.send_message(message.chat.id, "❌ Bot channel me Admin nahi hai! Pehle Admin banayein.")
            return
    except Exception:
        bot.send_message(message.chat.id, "❌ Bot channel read nahi kar pa raha hai. Public username check karein.")
        return

    cost = get_setting("cost_per_member", 15)
    msg = bot.send_message(message.chat.id, f"✅ <b>Channel Verified!</b>\nKitne subscribers chahiye? (1 = <code>{cost} Coins</code>):")
    bot.register_next_step_handler(msg, process_campaign_count, ch_user)

def process_campaign_count(message, ch_user):
    try:
        count = int(message.text.strip())
        if count <= 0:
            raise ValueError
        cost = get_setting("cost_per_member", 15)
        total_cost = count * cost
        uid = message.from_user.id
        if get_coins(uid) < total_cost:
            bot.send_message(message.chat.id, f"❌ Insufficient Coins! Chahiye: <code>{total_cost} Coins</code>.")
            return
        conn = sqlite3.connect("promotion.db")
        c = conn.cursor()
        c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (total_cost, uid))
        c.execute("INSERT INTO campaigns (owner_id, channel_username, needed_joins) VALUES (?, ?, ?)", (uid, ch_user, count))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"🚀 <b>Campaign Live!</b>\nTarget: <code>{count} Members</code>. Pura hone par DM me notification mil jayega.")
        text, markup = main_menu(uid)
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except Exception:
        bot.send_message(message.chat.id, "❌ Valid number enter karein!")

# --- MASTER ADMIN CONSOLE ---
@bot.callback_query_handler(func=lambda c: c.data == "admin_master")
def admin_master_panel(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    j_rew = get_setting("join_reward", 15)
    r_rew = get_setting("refer_reward", 20)
    c_cost = get_setting("cost_per_member", 15)

    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_u = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM campaigns WHERE status = 'ACTIVE'")
    active_c = c.fetchone()[0]
    conn.close()

    text = (
        "╔════════════════════════╗\n"
        "   ⚡ <b>MASTER ADMIN CONSOLE</b> ⚡\n"
        "╚════════════════════════╝\n"
        f"👥 <b>Total Users:</b> <code>{total_u}</code>\n"
        f"📢 <b>Active Campaigns:</b> <code>{active_c}</code>\n"
        "────────────────────────\n"
        f"• Join: <code>{j_rew}</code> | Refer: <code>{r_rew}</code> | Cost: <code>{c_cost}</code>\n"
        "────────────────────────"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎁 Gift Coins to User", callback_data="adm_gift_coins"),
        types.InlineKeyboardButton("📢 Global Broadcast", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("✏️ Set Join Coins", callback_data="adm_chg_join"),
        types.InlineKeyboardButton("✏️ Set Refer Coins", callback_data="adm_chg_refer"),
        types.InlineKeyboardButton("📋 View Campaigns", callback_data="adm_view_channels"),
        types.InlineKeyboardButton("📊 User Activity", callback_data="adm_view_users"),
        types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="refresh_menu")
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

# Admin Feature: Gift/Send Coins to Any User
@bot.callback_query_handler(func=lambda c: c.data == "adm_gift_coins")
def adm_gift_coins_start(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(
        ADMIN_ID,
        "🎁 <b>Send Coins to User:</b>\n\n"
        "Format me bhejein: <code>UserID Coins</code>\n"
        "Example: <code>7161571409 100</code>"
    )
    bot.register_next_step_handler(msg, process_gift_coins)

def process_gift_coins(message):
    try:
        parts = message.text.strip().split()
        target_id, amount = int(parts[0]), int(parts[1])

        conn = sqlite3.connect("promotion.db")
        c = conn.cursor()
        c.execute("SELECT name FROM users WHERE user_id = ?", (target_id,))
        user_row = c.fetchone()

        if not user_row:
            bot.send_message(ADMIN_ID, "❌ User database me nahi mila!")
            conn.close()
            return

        c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()

        # User ko alert bhejna
        try:
            bot.send_message(
                target_id,
                f"🎉 <b>ADMIN BONUS RECEIVED!</b>\n\n"
                f"Admin ne aapke wallet me <b>+{amount} Coins</b> credit kiye hain!"
            )
        except Exception:
            pass

        bot.send_message(ADMIN_ID, f"✅ <b>Successfully Credited!</b>\nUser: <code>{target_id}</code>\nAmount: <code>+{amount} Coins</code>")
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ Format galat tha! Example: <code>123456789 50</code>\nError: {e}")

# Admin Feature: Broadcast Message to All Users
@bot.callback_query_handler(func=lambda c: c.data == "adm_broadcast")
def adm_broadcast_start(call):
    if int(call.from_user.id) != ADMIN_ID:
        return
    msg = bot.send_message(
        ADMIN_ID, 
        "📢 <b>Broadcast Console:</b>\n\n"
        "Sabhi bot users ko jo message bhejna hai, wo type karke bhejein (Text/HTML supported):"
    )
    bot.register_next_step_handler(msg, process_broadcast_send)

def process_broadcast_send(message):
    broadcast_text = message.text
    conn = sqlite3.connect("promotion.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    total_sent = 0
    total_failed = 0
    status_

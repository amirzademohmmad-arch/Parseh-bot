import os, json, time, requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FILE = "parseh_data.json"
states = {}

CUSTOMER_MENU = {
    "keyboard": [
        [{"text": "👗 محصولات"}, {"text": "🆕 جدیدترین مدل‌ها"}],
        [{"text": "📦 ثبت سفارش عمده"}, {"text": "💰 استعلام قیمت"}],
        [{"text": "🚚 پیگیری سفارش"}, {"text": "📞 ارتباط با فروش"}],
    ],
    "resize_keyboard": True
}

ADMIN_MENU = {
    "keyboard": [
        [{"text": "➕ افزودن محصول"}, {"text": "🖼 افزودن عکس محصول"}],
        [{"text": "📦 سفارش‌ها"}, {"text": "👗 محصولات"}],
        [{"text": "🔄 تغییر وضعیت سفارش"}, {"text": "❌ حذف محصول"}],
        [{"text": "📊 گزارش"}, {"text": "📞 ارتباط با فروش"}],
    ],
    "resize_keyboard": True
}

ORDER_STATUSES = ["در انتظار تأیید", "تأیید شده", "در حال آماده‌سازی", "تحویل باربری", "ارسال شده", "لغو شده"]

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "products": [
                {"code": "SP-101", "name": "ست اسپرت زنانه", "fabric": "دورس", "colors": "مشکی، کرم، طوسی", "sizes": "38 تا 46", "min_order": "6 عدد", "price": "تماس بگیرید", "stock": "موجود", "photo_id": ""}
            ],
            "orders": [],
            "customers": {}
        }
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def post(method, payload):
    try:
        return requests.post(f"{API_URL}/{method}", data=payload, timeout=30).json()
    except Exception as e:
        print("Telegram error:", e)
        return {"ok": False}

def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    return post("sendMessage", payload)

def send_photo(chat_id, photo_id, caption):
    return post("sendPhoto", {"chat_id": chat_id, "photo": photo_id, "caption": caption})

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        return requests.get(f"{API_URL}/getUpdates", params=params, timeout=40).json()
    except Exception as e:
        print("Update error:", e)
        return {"ok": False}

def customer_name(user):
    name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
    username = user.get("username", "")
    return f"{name} @{username}".strip()

def save_customer(user):
    data = load_data()
    uid = str(user["id"])
    data["customers"][uid] = {
        "id": user["id"],
        "name": customer_name(user),
        "username": user.get("username", ""),
        "last_seen": now()
    }
    save_data(data)

def product_caption(p):
    return (
        f"👗 {p.get('name','')}\n\n"
        f"کد: {p.get('code','')}\n"
        f"جنس: {p.get('fabric','')}\n"
        f"رنگ‌ها: {p.get('colors','')}\n"
        f"سایز: {p.get('sizes','')}\n"
        f"حداقل سفارش: {p.get('min_order','')}\n"
        f"قیمت عمده: {p.get('price','')}\n"
        f"موجودی: {p.get('stock','')}"
    )

def find_product(code):
    data = load_data()
    return next((p for p in data["products"] if p["code"].upper() == code.upper()), None)

def parse_product(text):
    mapping = {
        "کد": "code", "نام": "name", "جنس": "fabric",
        "رنگ‌ها": "colors", "رنگها": "colors", "سایز": "sizes",
        "حداقل سفارش": "min_order", "قیمت": "price", "موجودی": "stock"
    }
    product = {"photo_id": ""}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k in mapping:
                product[mapping[k]] = v
    return product

def show_products(chat_id, latest=False):
    data = load_data()
    products = data["products"][-5:] if latest else data["products"]
    if not products:
        send_message(chat_id, "فعلاً محصولی ثبت نشده است.")
        return
    for p in products:
        if p.get("photo_id"):
            send_photo(chat_id, p["photo_id"], product_caption(p))
        else:
            send_message(chat_id, product_caption(p))

def handle_start(msg):
    user, chat_id = msg["from"], msg["chat"]["id"]
    save_customer(user)
    if user["id"] == ADMIN_ID:
        send_message(chat_id, "سلام مدیر Parseh 👋\nپنل مدیریت فعال شد.", ADMIN_MENU)
    else:
        send_message(chat_id, "سلام 👋\nبه ربات فروش عمده پوشاک زنانه Parseh خوش آمدید.\n\nاز اینجا می‌توانید محصولات را ببینید، قیمت بگیرید، سفارش ثبت کنید و وضعیت سفارش را پیگیری کنید.", CUSTOMER_MENU)

def handle_admin_command(msg, text):
    uid, chat_id = msg["from"]["id"], msg["chat"]["id"]
    data = load_data()

    if text == "➕ افزودن محصول":
        states[uid] = {"mode": "add_product"}
        send_message(chat_id, "اطلاعات محصول را با این فرمت بفرست:\n\nکد: SP-102\nنام: هودی زنانه\nجنس: دورس\nرنگ‌ها: مشکی، کرم\nسایز: 38 تا 46\nحداقل سفارش: 6 عدد\nقیمت: 450000\nموجودی: موجود")
        return True

    if text == "🖼 افزودن عکس محصول":
        states[uid] = {"mode": "add_photo_code"}
        send_message(chat_id, "کد محصول را بفرست. مثال: SP-101")
        return True

    if text == "📦 سفارش‌ها":
        orders = data["orders"][-20:]
        if not orders:
            send_message(chat_id, "هنوز سفارشی ثبت نشده است.")
            return True
        out = "📦 آخرین سفارش‌ها:\n\n"
        for o in orders:
            out += f"#{o['id']} | {o['status']} | {o['created_at']}\n{o['text'][:150]}\n────────\n"
        send_message(chat_id, out)
        return True

    if text == "🔄 تغییر وضعیت سفارش":
        states[uid] = {"mode": "status_order_id"}
        send_message(chat_id, "شماره سفارش را بفرست. مثال: 1001")
        return True

    if text == "❌ حذف محصول":
        states[uid] = {"mode": "delete_product"}
        send_message(chat_id, "کد محصولی که باید حذف شود را بفرست.")
        return True

    if text == "📊 گزارش":
        send_message(chat_id, f"📊 گزارش Parseh\n\nتعداد محصولات: {len(data['products'])}\nتعداد سفارش‌ها: {len(data['orders'])}\nتعداد مشتریان: {len(data['customers'])}")
        return True

    return False

def handle_photo(msg):
    uid, chat_id = msg["from"]["id"], msg["chat"]["id"]
    state = states.get(uid)
    if uid != ADMIN_ID or not state or state.get("mode") != "add_photo_file":
        return False

    photos = msg.get("photo", [])
    if not photos:
        return False

    file_id = photos[-1]["file_id"]
    code = state["code"]
    data = load_data()
    for p in data["products"]:
        if p["code"].upper() == code.upper():
            p["photo_id"] = file_id
            save_data(data)
            states.pop(uid, None)
            send_message(chat_id, "✅ عکس محصول ثبت شد.", ADMIN_MENU)
            return True

    states.pop(uid, None)
    send_message(chat_id, "محصول پیدا نشد.", ADMIN_MENU)
    return True

def handle_state(msg, text):
    uid, chat_id = msg["from"]["id"], msg["chat"]["id"]
    state = states.get(uid)
    if not state:
        return False

    mode = state["mode"]
    data = load_data()

    if mode == "add_product" and uid == ADMIN_ID:
        p = parse_product(text)
        required = ["code", "name", "fabric", "colors", "sizes", "min_order", "price", "stock"]
        if not all(p.get(k) for k in required):
            send_message(chat_id, "اطلاعات ناقص است. دوباره طبق نمونه بفرست.")
            return True
        if find_product(p["code"]):
            send_message(chat_id, "این کد محصول قبلاً ثبت شده است.", ADMIN_MENU)
            states.pop(uid, None)
            return True
        data["products"].append(p)
        save_data(data)
        states.pop(uid, None)
        send_message(chat_id, "✅ محصول اضافه شد.", ADMIN_MENU)
        return True

    if mode == "add_photo_code" and uid == ADMIN_ID:
        if not find_product(text):
            send_message(chat_id, "محصولی با این کد پیدا نشد.", ADMIN_MENU)
            states.pop(uid, None)
            return True
        states[uid] = {"mode": "add_photo_file", "code": text.upper()}
        send_message(chat_id, "حالا عکس محصول را ارسال کن.")
        return True

    if mode == "delete_product" and uid == ADMIN_ID:
        before = len(data["products"])
        data["products"] = [p for p in data["products"] if p["code"].upper() != text.upper()]
        save_data(data)
        states.pop(uid, None)
        send_message(chat_id, "✅ حذف شد." if len(data["products"]) < before else "محصولی با این کد پیدا نشد.", ADMIN_MENU)
        return True

    if mode == "status_order_id" and uid == ADMIN_ID:
        order_id = text.replace("#", "").strip()
        order = next((o for o in data["orders"] if str(o["id"]) == order_id), None)
        if not order:
            send_message(chat_id, "سفارشی با این شماره پیدا نشد.", ADMIN_MENU)
            states.pop(uid, None)
            return True
        states[uid] = {"mode": "status_value", "order_id": int(order_id)}
        send_message(chat_id, "وضعیت جدید را دقیقاً یکی از این‌ها بفرست:\n\n" + "\n".join(ORDER_STATUSES))
        return True

    if mode == "status_value" and uid == ADMIN_ID:
        if text not in ORDER_STATUSES:
            send_message(chat_id, "وضعیت معتبر نیست. یکی از گزینه‌های لیست را بفرست.")
            return True
        customer_id = None
        for o in data["orders"]:
            if o["id"] == state["order_id"]:
                o["status"] = text
                customer_id = o["user_id"]
        save_data(data)
        states.pop(uid, None)
        send_message(chat_id, "✅ وضعیت سفارش تغییر کرد.", ADMIN_MENU)
        if customer_id:
            send_message(customer_id, f"🚚 وضعیت سفارش #{state['order_id']}:\n{text}")
        return True

    if mode == "price":
        p = find_product(text)
        send_message(chat_id, "💰 استعلام قیمت:\n\n" + product_caption(p) if p else "محصولی با این کد پیدا نشد.")
        states.pop(uid, None)
        return True

    if mode == "order":
        order_id = 1000 + len(data["orders"]) + 1
        order = {"id": order_id, "user_id": uid, "username": msg["from"].get("username", ""), "text": text, "status": "در انتظار تأیید", "created_at": now()}
        data["orders"].append(order)
        save_data(data)
        states.pop(uid, None)
        send_message(chat_id, f"✅ سفارش شما ثبت شد.\nشماره سفارش: #{order_id}\nهمکاران فروش برای تأیید نهایی با شما تماس می‌گیرند.")
        if ADMIN_ID:
            send_message(ADMIN_ID, f"📦 سفارش جدید Parseh\n\nشماره: #{order_id}\nمشتری: {customer_name(msg['from'])}\nآیدی: {uid}\n\n{text}")
        return True

    if mode == "track":
        order_id = text.replace("#", "").strip()
        order = next((o for o in data["orders"] if str(o["id"]) == order_id), None)
        send_message(chat_id, f"🚚 وضعیت سفارش #{order['id']}:\n{order['status']}" if order and (order["user_id"] == uid or uid == ADMIN_ID) else "سفارشی با این شماره پیدا نشد.")
        states.pop(uid, None)
        return True

    return False

def handle_text(msg):
    text = msg.get("text", "").strip()
    if not text:
        return

    user, chat_id = msg["from"], msg["chat"]["id"]
    uid = user["id"]
    save_customer(user)

    if text == "/start":
        handle_start(msg)
        return

    if handle_state(msg, text):
        return

    if uid == ADMIN_ID and handle_admin_command(msg, text):
        return

    if text in ["👗 محصولات", "👗 محصولات Parseh"]:
        show_products(chat_id)
        return

    if text == "🆕 جدیدترین مدل‌ها":
        show_products(chat_id, latest=True)
        return

    if text == "💰 استعلام قیمت":
        states[uid] = {"mode": "price"}
        send_message(chat_id, "کد محصول را بفرست. مثال: SP-101")
        return

    if text == "📦 ثبت سفارش عمده":
        states[uid] = {"mode": "order"}
        send_message(chat_id, "اطلاعات سفارش را در یک پیام بفرست:\n\nنام و نام خانوادگی:\nشماره تماس:\nشهر:\nنام فروشگاه:\nکد محصول:\nرنگ:\nسایز:\nتعداد:\nتوضیحات:")
        return

    if text == "🚚 پیگیری سفارش":
        states[uid] = {"mode": "track"}
        send_message(chat_id, "شماره سفارش را بفرست. مثال: 1001")
        return

    if text == "📞 ارتباط با فروش":
        send_message(chat_id, "پیام خود را ارسال کنید. برای ادمین Parseh فرستاده می‌شود.")
        return

    if uid != ADMIN_ID and ADMIN_ID:
        send_message(ADMIN_ID, f"📩 پیام مشتری\n{customer_name(user)}\nآیدی: {uid}\n\n{text}")
        send_message(chat_id, "پیام شما برای فروش Parseh ارسال شد.")

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing")
        return

    print("Parseh bot is running...")
    offset = None

    while True:
        try:
            updates = get_updates(offset)
            if updates.get("ok"):
                for update in updates.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message")
                    if not msg:
                        continue
                    if "photo" in msg and handle_photo(msg):
                        continue
                    handle_text(msg)
            else:
                print(updates)
                time.sleep(5)
        except Exception as e:
            print("Main loop error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()

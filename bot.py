import os
import json
import time
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DATA_FILE = "parseh_data.json"

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "👗 محصولات Parseh"}, {"text": "🆕 جدیدترین مدل‌ها"}],
        [{"text": "📦 ثبت سفارش عمده"}, {"text": "💰 استعلام قیمت"}],
        [{"text": "🚚 پیگیری سفارش"}, {"text": "📞 ارتباط با فروش"}],
    ],
    "resize_keyboard": True
}

ADMIN_KEYBOARD = {
    "keyboard": [
        [{"text": "➕ افزودن محصول"}, {"text": "📦 مشاهده سفارش‌ها"}],
        [{"text": "👗 محصولات Parseh"}, {"text": "📞 ارتباط با فروش"}],
    ],
    "resize_keyboard": True
}

states = {}

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "products": [
                {
                    "code": "SP-101",
                    "name": "ست اسپرت زنانه",
                    "fabric": "دورس",
                    "colors": "مشکی، کرم، طوسی",
                    "sizes": "38 تا 46",
                    "min_order": "6 عدد",
                    "price": "تماس بگیرید"
                }
            ],
            "orders": []
        }
        save_data(data)
        return data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_message(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    try:
        requests.post(f"{API_URL}/sendMessage", data=payload, timeout=20)
    except Exception as e:
        print("send_message error:", e)

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{API_URL}/getUpdates", params=params, timeout=40)
    return r.json()

def parse_product(text):
    mapping = {
        "کد": "code",
        "نام": "name",
        "جنس": "fabric",
        "رنگ‌ها": "colors",
        "سایز": "sizes",
        "حداقل سفارش": "min_order",
        "قیمت": "price",
    }
    product = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if key in mapping:
                product[mapping[key]] = value
    return product

def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    username = message["from"].get("username", "")
    text = message.get("text", "").strip()

    if not text:
        return

    if text == "/start":
        if user_id == ADMIN_ID:
            send_message(chat_id, "سلام مدیر Parseh 👋\nبه پنل مدیریت ربات خوش آمدید.", ADMIN_KEYBOARD)
        else:
            send_message(
                chat_id,
                "سلام 👋\nبه ربات فروش عمده پوشاک زنانه Parseh خوش آمدید.\n\n"
                "از طریق این ربات می‌توانید مدل‌های جدید را ببینید، قیمت عمده بگیرید و سفارش خود را ثبت کنید.",
                MAIN_KEYBOARD
            )
        return

    if text == "👗 محصولات Parseh":
        data = load_data()
        if not data["products"]:
            send_message(chat_id, "فعلاً محصولی ثبت نشده است.")
            return
        out = "👗 محصولات Parseh:\n\n"
        for p in data["products"]:
            out += (
                f"کد: {p['code']}\n"
                f"نام: {p['name']}\n"
                f"جنس: {p['fabric']}\n"
                f"رنگ‌ها: {p['colors']}\n"
                f"سایز: {p['sizes']}\n"
                f"حداقل سفارش: {p['min_order']}\n"
                f"قیمت عمده: {p['price']}\n"
                "──────────────\n"
            )
        send_message(chat_id, out)
        return

    if text == "🆕 جدیدترین مدل‌ها":
        data = load_data()
        latest = data["products"][-5:]
        if not latest:
            send_message(chat_id, "فعلاً مدل جدیدی ثبت نشده است.")
            return
        out = "🆕 جدیدترین مدل‌های Parseh:\n\n"
        for p in latest:
            out += f"{p['code']} - {p['name']} - {p['price']}\n"
        send_message(chat_id, out)
        return

    if text == "💰 استعلام قیمت":
        states[user_id] = "price"
        send_message(chat_id, "لطفاً کد محصول را ارسال کنید. مثال: SP-101")
        return

    if text == "📦 ثبت سفارش عمده":
        states[user_id] = "order"
        send_message(
            chat_id,
            "لطفاً اطلاعات سفارش را در یک پیام ارسال کنید:\n\n"
            "نام و نام خانوادگی:\n"
            "شماره تماس:\n"
            "شهر:\n"
            "نام فروشگاه:\n"
            "کد محصول:\n"
            "رنگ:\n"
            "سایز:\n"
            "تعداد:\n"
            "توضیحات:"
        )
        return

    if text == "🚚 پیگیری سفارش":
        states[user_id] = "track"
        send_message(chat_id, "شماره سفارش خود را وارد کنید. مثال: 1001")
        return

    if text == "📞 ارتباط با فروش":
        send_message(chat_id, "برای ارتباط با فروش Parseh، پیام خود را همین‌جا ارسال کنید.")
        return

    if text == "➕ افزودن محصول" and user_id == ADMIN_ID:
        states[user_id] = "add_product"
        send_message(
            chat_id,
            "اطلاعات محصول جدید را دقیقاً به این شکل ارسال کنید:\n\n"
            "کد: SP-102\n"
            "نام: هودی زنانه\n"
            "جنس: دورس\n"
            "رنگ‌ها: مشکی، کرم\n"
            "سایز: 38 تا 46\n"
            "حداقل سفارش: 6 عدد\n"
            "قیمت: 450000"
        )
        return

    if text == "📦 مشاهده سفارش‌ها" and user_id == ADMIN_ID:
        data = load_data()
        orders = data["orders"][-10:]
        if not orders:
            send_message(chat_id, "فعلاً سفارشی ثبت نشده است.")
            return
        out = "📦 آخرین سفارش‌ها:\n\n"
        for o in orders:
            out += (
                f"شماره سفارش: {o['id']}\n"
                f"کاربر: {o['user_id']}\n"
                f"وضعیت: {o['status']}\n"
                f"زمان: {o['created_at']}\n"
                f"متن سفارش:\n{o['text']}\n"
                "──────────────\n"
            )
        send_message(chat_id, out)
        return

    mode = states.get(user_id)

    if mode == "price":
        data = load_data()
        code = text.upper()
        product = next((p for p in data["products"] if p["code"].upper() == code), None)
        if product:
            send_message(
                chat_id,
                f"💰 استعلام قیمت:\n\n"
                f"کد: {product['code']}\n"
                f"نام: {product['name']}\n"
                f"قیمت عمده: {product['price']}\n"
                f"حداقل سفارش: {product['min_order']}\n"
                f"رنگ‌ها: {product['colors']}\n"
                f"سایز: {product['sizes']}"
            )
        else:
            send_message(chat_id, "محصولی با این کد پیدا نشد.")
        states.pop(user_id, None)
        return

    if mode == "order":
        data = load_data()
        order_id = 1000 + len(data["orders"]) + 1
        order = {
            "id": order_id,
            "user_id": user_id,
            "username": username,
            "text": text,
            "status": "در انتظار تأیید",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        data["orders"].append(order)
        save_data(data)

        send_message(
            chat_id,
            f"✅ سفارش شما در Parseh ثبت شد.\n\n"
            f"شماره سفارش: #{order_id}\n"
            "همکاران فروش برای تأیید نهایی با شما تماس می‌گیرند."
        )
        if ADMIN_ID:
            send_message(
                ADMIN_ID,
                f"📦 سفارش جدید Parseh\n\n"
                f"شماره سفارش: #{order_id}\n"
                f"کاربر: @{username}\n"
                f"آیدی: {user_id}\n\n{text}"
            )
        states.pop(user_id, None)
        return

    if mode == "track":
        data = load_data()
        code = text.replace("#", "").strip()
        order = next((o for o in data["orders"] if str(o["id"]) == code), None)
        if order and (user_id == order["user_id"] or user_id == ADMIN_ID):
            send_message(chat_id, f"🚚 وضعیت سفارش #{order['id']}:\n{order['status']}")
        else:
            send_message(chat_id, "سفارشی با این شماره پیدا نشد.")
        states.pop(user_id, None)
        return

    if mode == "add_product" and user_id == ADMIN_ID:
        product = parse_product(text)
        required = ["code", "name", "fabric", "colors", "sizes", "min_order", "price"]
        if all(k in product for k in required):
            data = load_data()
            data["products"].append(product)
            save_data(data)
            send_message(chat_id, "✅ محصول جدید با موفقیت اضافه شد.", ADMIN_KEYBOARD)
        else:
            send_message(chat_id, "فرمت اطلاعات ناقص است. دوباره طبق نمونه ارسال کنید.")
        states.pop(user_id, None)
        return

    if ADMIN_ID and user_id != ADMIN_ID:
        send_message(
            ADMIN_ID,
            f"📩 پیام مشتری\nکاربر: @{username}\nآیدی: {user_id}\n\n{text}"
        )
        send_message(chat_id, "پیام شما برای فروش Parseh ارسال شد.")

def main():
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing.")
        return

    print("Parseh bot is running...")
    offset = None

    while True:
        try:
            result = get_updates(offset)
            if result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    if "message" in update:
                        handle_message(update["message"])
            else:
                print(result)
                time.sleep(5)
        except Exception as e:
            print("main loop error:", e)
            time.sleep(5)

if __name__ == "__main__":
    main()
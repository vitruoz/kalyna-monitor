#!/usr/bin/env python3
"""
Kalyna Instagram Monitor Bot
Працює як веб-сервіс (безкоштовний план Render)
"""

import time
import json
import os
import threading
import requests
import instaloader
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = "8759128369:AAGDPnjMrmI86ofAgf9wrBFEC7zDu5In5JY"
TELEGRAM_CHAT_ID = "354854283"
CHECK_INTERVAL = 3600
DATA_FILE = "/tmp/last_posts.json"
PORT = int(os.environ.get("PORT", 8080))

COMPETITORS = {
    "Мережка":    "merezhka.official",
    "Etnodim":    "etnodim",
    "Barvy":      "vyshyvanka_shop.ua",
    "Svarga":     "svarga_ua",
    "Гаптування": "gaptuvalnya",
    "Едельвіка":  "edelvika",
    "Галичанка":  "galychanka_ua",
    "Гойра":      "hoyra.com.ua",
    "Vytyn":      "ukrglamour",
    "Vzhe-Vzhe":  "vzhe.vzhe",
    "Масік":      "vyshyvanka.vmv",
}

last_check = {"time": None, "status": "Ще не запускався"}


def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }, timeout=10)
    except Exception as e:
        print(f"[Telegram] Помилка: {e}")


def load_state():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_latest_post(username):
    L = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
    )
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        post = next(iter(profile.get_posts()), None)
        if post is None:
            return None
        return {
            "shortcode": post.shortcode,
            "timestamp": post.date_utc.isoformat(),
            "caption": (post.caption or "")[:200],
            "url": f"https://www.instagram.com/p/{post.shortcode}/",
            "likes": post.likes,
        }
    except Exception as e:
        print(f"[{username}] Помилка: {e}")
        return None


def check_all():
    state = load_state()
    updated = False

    for brand, username in COMPETITORS.items():
        print(f"Перевіряю @{username}...")
        post = get_latest_post(username)
        if post is None:
            time.sleep(5)
            continue

        last = state.get(username)
        if last is None:
            state[username] = post["shortcode"]
            updated = True
        elif last != post["shortcode"]:
            state[username] = post["shortcode"]
            updated = True
            dt = datetime.fromisoformat(post["timestamp"]).strftime("%d.%m.%Y %H:%M")
            caption = post["caption"].replace("\n", " ")[:150]
            send_telegram(
                f"🆕 <b>Новий пост від {brand}</b>\n"
                f"📸 @{username}\n"
                f"🕐 {dt} UTC\n"
                f"❤️ {post['likes']:,} лайків\n\n"
                f"📝 {caption}\n\n"
                f"🔗 <a href='{post['url']}'>Переглянути пост</a>"
            )
            print(f"  🔔 Новий пост від {brand}!")
        time.sleep(5)

    if updated:
        save_state(state)


def monitor_loop():
    print("🌻 Kalyna Monitor запущено")
    send_telegram(
        "🌻 <b>Kalyna Monitor запущено!</b>\n\n"
        f"Моніторю {len(COMPETITORS)} конкурентів:\n"
        + "\n".join(f"• {b} (@{u})" for b, u in COMPETITORS.items())
        + f"\n\n⏱ Перевірка кожні {CHECK_INTERVAL // 60} хв."
    )
    while True:
        try:
            last_check["time"] = datetime.now().strftime("%H:%M:%S")
            last_check["status"] = "Виконується перевірка..."
            check_all()
            last_check["status"] = "Очікування наступної перевірки"
        except Exception as e:
            last_check["status"] = f"Помилка: {e}"
            print(f"Помилка: {e}")
        time.sleep(CHECK_INTERVAL)


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""
        <html><body style="font-family:sans-serif; padding:2rem;">
        <h2>🌻 Kalyna Instagram Monitor</h2>
        <p>Статус: <b>{last_check['status']}</b></p>
        <p>Остання перевірка: <b>{last_check['time'] or 'ще не було'}</b></p>
        <p>Конкурентів: <b>{len(COMPETITORS)}</b></p>
        <p>Інтервал: <b>{CHECK_INTERVAL // 60} хвилин</b></p>
        </body></html>
        """
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    print(f"Веб-сервер запущено на порту {PORT}")
    HTTPServer(("0.0.0.0", PORT), StatusHandler).serve_forever()

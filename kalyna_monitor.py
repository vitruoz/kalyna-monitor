#!/usr/bin/env python3
"""
Kalyna Instagram Monitor Bot
Моніторить Instagram акаунти конкурентів і надсилає сповіщення в Telegram
"""

import time
import json
import os
import requests
import instaloader
from datetime import datetime

# ─── НАЛАШТУВАННЯ ───────────────────────────────────────────
TELEGRAM_TOKEN = "8759128369:AAGDPnjMrmI86ofAgf9wrBFEC7zDu5In5JY"
TELEGRAM_CHAT_ID = "354854283"
CHECK_INTERVAL = 3600  # перевірка кожну годину (в секундах)
DATA_FILE = "last_posts.json"  # файл для збереження стану

# Акаунти конкурентів
COMPETITORS = {
    "Мережка":      "merezhka.official",
    "Etnodim":      "etnodim",
    "Barvy":        "vyshyvanka_shop.ua",
    "Svarga":       "svarga_ua",
    "Гаптування":   "gaptuvalnya",
    "Едельвіка":    "edelvika",
    "Галичанка":    "galychanka_ua",
    "Гойра":        "hoyra.com.ua",
    "Vytyn":        "ukrglamour",
    "Vzhe-Vzhe":    "vzhe.vzhe",
    "Масік":        "vyshyvanka.vmv",
}
# ────────────────────────────────────────────────────────────


def send_telegram(message: str):
    """Надсилає повідомлення в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print(f"[Telegram] Помилка надсилання: {e}")


def load_state() -> dict:
    """Завантажує збережений стан (останні пости)"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    """Зберігає поточний стан"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_latest_post(username: str):
    """
    Отримує останній пост з Instagram акаунту.
    Повертає (shortcode, timestamp, caption, url) або None.
    """
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
        posts = profile.get_posts()
        post = next(iter(posts), None)
        if post is None:
            return None
        caption = (post.caption or "")[:200]
        url = f"https://www.instagram.com/p/{post.shortcode}/"
        return {
            "shortcode": post.shortcode,
            "timestamp": post.date_utc.isoformat(),
            "caption": caption,
            "url": url,
            "likes": post.likes,
        }
    except Exception as e:
        print(f"[{username}] Помилка отримання постів: {e}")
        return None


def check_all(state: dict) -> dict:
    """Перевіряє всі акаунти і надсилає сповіщення про нові пости"""
    updated = False

    for brand, username in COMPETITORS.items():
        print(f"Перевіряю @{username} ({brand})...")
        post = get_latest_post(username)

        if post is None:
            continue

        last_shortcode = state.get(username)

        if last_shortcode is None:
            # Перший запуск — просто запам'ятовуємо
            state[username] = post["shortcode"]
            updated = True
            print(f"  ✓ Запам'ятав перший пост: {post['shortcode']}")

        elif last_shortcode != post["shortcode"]:
            # Новий пост!
            state[username] = post["shortcode"]
            updated = True

            dt = datetime.fromisoformat(post["timestamp"])
            dt_str = dt.strftime("%d.%m.%Y %H:%M")

            caption_preview = post["caption"].replace("\n", " ")
            if len(caption_preview) > 150:
                caption_preview = caption_preview[:150] + "..."

            message = (
                f"🆕 <b>Новий пост від {brand}</b>\n"
                f"📸 @{username}\n"
                f"🕐 {dt_str} UTC\n"
                f"❤️ {post['likes']:,} лайків\n\n"
                f"📝 {caption_preview}\n\n"
                f"🔗 <a href='{post['url']}'>Переглянути пост</a>"
            )
            send_telegram(message)
            print(f"  🔔 Новий пост! Сповіщення надіслано.")
        else:
            print(f"  — Нових постів немає.")

        # Пауза між запитами щоб не отримати бан від Instagram
        time.sleep(5)

    if updated:
        save_state(state)

    return state


def main():
    print("=" * 50)
    print("🌻 Kalyna Instagram Monitor запущено")
    print(f"⏱  Перевірка кожні {CHECK_INTERVAL // 60} хвилин")
    print(f"📋 Моніториться {len(COMPETITORS)} конкурентів")
    print("=" * 50)

    # Надсилаємо стартове повідомлення
    send_telegram(
        "🌻 <b>Kalyna Monitor запущено!</b>\n\n"
        f"Моніторю {len(COMPETITORS)} конкурентів:\n"
        + "\n".join(f"• {b} (@{u})" for b, u in COMPETITORS.items())
        + f"\n\n⏱ Перевірка кожні {CHECK_INTERVAL // 60} хв."
    )

    state = load_state()

    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Починаю перевірку...")
            state = check_all(state)
            print(f"Наступна перевірка через {CHECK_INTERVAL // 60} хвилин.")
        except KeyboardInterrupt:
            print("\nЗупинено вручну.")
            send_telegram("⏹ Kalyna Monitor зупинено.")
            break
        except Exception as e:
            print(f"Помилка: {e}")
            send_telegram(f"⚠️ Помилка моніторингу: {e}")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()

import os

import requests

from .util import log


def _cfg():
    return os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def message(text):
    tok, chat = _cfg()
    if not tok or not chat:
        log("Telegram not configured; message:", text)
        return
    requests.post(f"https://api.telegram.org/bot{tok}/sendMessage", data={"chat_id": chat, "text": text[:4000]}, timeout=30)


def send_video(video, thumb, caption):
    tok, chat = _cfg()
    if not tok or not chat:
        log("Telegram not configured; skipping upload")
        return
    with open(video, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{tok}/sendVideo",
                          data={"chat_id": chat, "caption": caption[:1000], "supports_streaming": "true"},
                          files={"video": f}, timeout=300)
    r.raise_for_status()
    if thumb:
        with open(thumb, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{tok}/sendPhoto",
                          data={"chat_id": chat, "caption": "Thumbnail"}, files={"photo": f}, timeout=120)

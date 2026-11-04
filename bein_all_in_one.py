
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MOUD TV - Channel Collector & Monitor
مراقبة مصادر القنوات وتحديث الملفات تلقائياً.
للمصادر وواجهات API المصرح باستخدامها.
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone

import requests

# =====================================
# الإعدادات
# =====================================

OUTPUT_DIR = "output"
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")

CHECK_INTERVAL = 60       # كل 60 ثانية
REQUEST_TIMEOUT = 20

os.makedirs(HISTORY_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(OUTPUT_DIR, "changes.log"),
    level=logging.INFO,
    format="%(asctime)s | %(message)s"
)

# =====================================
# المصادر المصرح بها
# ضع روابط JSON الخاصة بك هنا
# =====================================

SOURCES = {
    "dramalive_bein": {
        "url": "YOUR_AUTHORIZED_BEIN_JSON_API",
        "category": "bein"
    },

    "dramalive_arabic": {
        "url": "YOUR_AUTHORIZED_ARABIC_JSON_API",
        "category": "arabic"
    },

    "dramalive_alwan": {
        "url": "YOUR_AUTHORIZED_ALWAN_JSON_API",
        "category": "alwan"
    },

    "prime_alwan": {
        "url": "YOUR_AUTHORIZED_PRIME_JSON_API",
        "category": "alwan"
    },

    "bein": {
        "url": "YOUR_AUTHORIZED_BEIN_SOURCE_API",
        "category": "bein"
    },

    "arabic": {
        "url": "YOUR_AUTHORIZED_ARABIC_SOURCE_API",
        "category": "arabic"
    }
}

session = requests.Session()
session.headers.update({
    "User-Agent": "MOUD-TV-Monitor/1.0",
    "Accept": "application/json"
})

# =====================================
# جلب البيانات
# =====================================

def fetch_data(url):
    if not url.startswith("https://"):
        raise ValueError("يجب استخدام HTTPS للمصدر")

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()
    return response.json()


# =====================================
# توحيد شكل القنوات
# =====================================

def normalize_channels(data):

    if isinstance(data, dict):
        channels = (
            data.get("channels")
            or data.get("live")
            or data.get("data")
            or []
        )
    elif isinstance(data, list):
        channels = data
    else:
        channels = []

    result = {}

    for channel in channels:

        if not isinstance(channel, dict):
            continue

        name = str(channel.get("name", "")).strip()
        if not name:
            continue

        logo = channel.get("logo", "")
        urls = channel.get("servers", [])

        if isinstance(urls, str):
            urls = [urls]

        if not urls and channel.get("url"):
            urls = [channel["url"]]

        servers = []

        for item in urls:
            if isinstance(item, dict):
                link = item.get("url", "")
            else:
                link = str(item)

            if link.startswith(("https://", "http://")):
                if link not in servers:
                    servers.append(link)

        if not servers:
            continue

        result[name] = {
            "name": name,
            "logo": logo,
            "live": True,
            "servers": servers
        }

    return result


# =====================================
# بصمة البيانات لاكتشاف التغيير
# =====================================

def calculate_hash(data):

    content = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True
    )

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


def read_old_data(filename):

    if not os.path.exists(filename):
        return None

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


# =====================================
# حفظ JSON و M3U
# =====================================

def save_source(source_name, channels):

    json_path = os.path.join(
        OUTPUT_DIR,
        source_name + ".json"
    )

    m3u_path = os.path.join(
        OUTPUT_DIR,
        source_name + ".m3u8"
    )

    output = {
        "source": source_name,
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "channels": channels
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    lines = ["#EXTM3U"]

    for channel in channels.values():

        name = channel["name"]
        logo = channel["logo"]

        for url in channel["servers"]:

            lines.append(
                f'#EXTINF:-1 tvg-name="{name}" '
                f'tvg-logo="{logo}",{name}'
            )

            lines.append(url)

    with open(m3u_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# =====================================
# مقارنة التحديثات
# =====================================

def monitor_source(source_name, config):

    try:

        print(f"\n[FETCH] {source_name}")

        raw_data = fetch_data(config["url"])
        channels = normalize_channels(raw_data)

        if not channels:
            print("[WARNING] لا توجد قنوات في البيانات")
            return

        json_path = os.path.join(
            OUTPUT_DIR,
            source_name + ".json"
        )

        old_data = read_old_data(json_path)
        old_channels = (
            old_data.get("channels", {})
            if isinstance(old_data, dict)
            else {}
        )

        old_hash = calculate_hash(old_channels)
        new_hash = calculate_hash(channels)

        if old_hash == new_hash:
            print("[UNCHANGED] لا توجد تغييرات")
            return

        old_names = set(old_channels)
        new_names = set(channels)

        added = new_names - old_names
        removed = old_names - new_names

        changed = {
            name for name in old_names & new_names
            if old_channels[name] != channels[name]
        }

        # الاحتفاظ بنسخة قبل التحديث
        if old_data is not None:

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            backup = os.path.join(
                HISTORY_DIR,
                f"{source_name}_{timestamp}.json"
            )

            with open(backup, "w", encoding="utf-8") as f:
                json.dump(
                    old_data,
                    f,
                    ensure_ascii=False,
                    indent=2
                )

        save_source(source_name, channels)

        message = (
            f"{source_name} | "
            f"Added: {len(added)} | "
            f"Removed: {len(removed)} | "
            f"Changed: {len(changed)}"
        )

        logging.info(message)

        print("[UPDATED]", message)

        if added:
            print("  + New:", ", ".join(sorted(added)))

        if removed:
            print("  - Removed:", ", ".join(sorted(removed)))

        if changed:
            print("  * Modified:", ", ".join(sorted(changed)))

    except Exception as error:

        logging.error(
            "%s | ERROR | %s",
            source_name,
            str(error)
        )

        print("[ERROR]", source_name, error)


# =====================================
# المراقبة المستمرة
# =====================================

def main():

    print("=" * 45)
    print("MOUD TV - AUTO CHANNEL MONITOR")
    print("Monitoring interval:", CHECK_INTERVAL, "seconds")
    print("=" * 45)

    while True:

        start = time.time()

        for source_name, config in SOURCES.items():
            monitor_source(source_name, config)

        elapsed = time.time() - start

        print(
            f"\n[WAIT] انتهت الدورة خلال {elapsed:.1f} ثانية"
        )

        print(
            f"إعادة المراقبة بعد {CHECK_INTERVAL} ثانية..."
        )

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("\nتم إيقاف المراقبة.")

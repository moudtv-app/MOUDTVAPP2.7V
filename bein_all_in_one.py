#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bein_all_in_one.py
سكربت موحّد لجلب روابط beIN Sports من عدة مصادر
يعمل تلقائياً عبر GitHub Actions
"""

import os
import base64
import json
import re
import time
import shutil
import sys

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None
    print("⚠️  curl_cffi غير مثبّت — سيتم استخدام requests العادي")

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("⚠️  pycryptodome غير مثبّت — المصدر 1 لن يعمل")

import requests


# ═══════════════════════════════════════════════════════════
#  إعدادات عامة
# ═══════════════════════════════════════════════════════════
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BEIN_FINAL_FILE = os.path.join(OUTPUT_DIR, "bein_final.m3u8")
BEIN_ALL_FILE   = os.path.join(OUTPUT_DIR, "bein_all.m3u8")
BEIN_JSON_FILE  = os.path.join(OUTPUT_DIR, "bein_data.json")


# ═══════════════════════════════════════════════════════════
#  المصدر 1: publicdataroute (AES)
# ═══════════════════════════════════════════════════════════
KEY = b"0123456789abcdef"
IV  = b"fedcba9876543210"


def aes_encrypt(data: str) -> str:
    ct = AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(data.encode(), 16))
    return base64.b64encode(ct).decode() + ":" + base64.b64encode(IV).decode()


def aes_decrypt(enc: str) -> str:
    p = enc.split(":")
    return unpad(
        AES.new(KEY, AES.MODE_CBC, base64.b64decode(p[1]))
        .decrypt(base64.b64decode(p[0])),
        16,
    ).decode()


def api_call(endpoint, payload, host="live.publicdataroute.cc", is_redirect=False):
    enc = aes_encrypt(json.dumps(payload, separators=(",", ":")))

    if is_redirect:
        url = f"https://{host}/redirect/{endpoint}"
    else:
        url = f"https://{host}/api/live/livedrama/v13.0.0/{endpoint}"

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; M2007J20CG MIUI/V12.0.9.0.QJGMIXM)",
    }
    try:
        if curl_requests:
            r = curl_requests.post(
                url, data=enc, headers=headers,
                timeout=20, impersonate="chrome", verify=False,
            )
        else:
            r = requests.post(url, data=enc, headers=headers, timeout=20, verify=False)
        if r.status_code in (200, 201):
            return json.loads(aes_decrypt(r.text.strip()))
    except Exception as e:
        print(f"   (خطأ API: {str(e)[:50]})")
    return None


def base_payload():
    return {
        "user_id": "_4244_1793052507021_notloggedin.com_dramalive3",
        "device_id": "6e38bfe9-fe7e-4baf-81ae-99d214928f27",
        "device_api": "29", "version_name": "185", "language": "ar",
        "timezone": "Africa/Casablanca", "device_type": "phone",
        "KEY_ACTIVATED_TYPE": "202122", "store": "playStore",
        "isStoreVersion": True, "isPremium": False,
        "isCoupon_active": False, "hideAds": False,
        "appCount": json.dumps({"adsFailed": 1, "adsLoaded": 0, "adsShowed": 0, "runCount": 4}),
        "mainServer": "http://main.backendcoreapi.com/api/live/livedrama/v13.0.0/",
    }


def resolve_redirect(redirect_url, agent="redirect"):
    payload = base_payload()
    payload["id"]    = "live_tv_beinsport1"
    payload["url"]   = redirect_url
    payload["agent"] = agent
    data = api_call("getLiveByRedirect", payload,
                    "redirect.publicdataroute.cc", is_redirect=True)
    if data and data.get("result") == 0:
        inner_json = data.get("data", {}).get("url", "")
        try:
            return json.loads(inner_json).get("url")
        except Exception:
            pass
    return None


def get_channel_data(channel_id):
    payload = base_payload()
    payload["id"] = channel_id
    data = api_call("getLiveAllStreamsById", payload)
    if data and data.get("result") == 0:
        return data.get("live", {})
    return None


BEIN_CHANNELS = [
    ("live_tv_beinsportnews", "Bein S. News"),
    ("live_tv_beinsport1", "Bein S. 1"),
    ("live_tv_beinsport2", "Bein S. 2"),
    ("live_tv_beinsport3", "Bein S. 3"),
    ("live_tv_beinsport4", "Bein S. 4"),
    ("live_tv_beinsport5", "Bein S. 5"),
    ("live_tv_beinsport6", "Bein S. 6"),
    ("live_tv_beinsport7", "Bein S. 7"),
    ("live_tv_beinsport8", "Bein S. 8"),
    ("live_tv_beinsport9", "Bein S. 9"),
    ("live_tv_beinsport11", "Bein S. En 1"),
    ("live_tv_beinsport12", "Bein S. En 2"),
    ("live_tv_beinsport13", "Bein S. En 3"),
    ("live_tv_beinsport14", "Bein S. En 4"),
    ("live_tv_beinsportfr1", "Bein S. Fr 1"),
    ("live_tv_beinsportfr2", "Bein S. Fr 2"),
    ("live_tv_beinsportfr3", "Bein S. Fr 3"),
    ("live_tv_beinsporttr1", "Bein S. Tr 1"),
    ("live_tv_beinsporttr2", "Bein S. Tr 2"),
    ("live_tv_beinsporttr3", "Bein S. Tr 3"),
    ("live_tv_beinsporttr4", "Bein S. Tr 4"),
]


def collect_source1():
    print("\n" + "═" * 60)
    print("🎯 [المصدر 1] publicdataroute — beIN Sports")
    print("═" * 60)

    if not HAS_CRYPTO:
        print("❌ تم تخطّي المصدر 1 (pycryptodome غير مثبّت)")
        return []

    m3u8 = ["#EXTM3U"]
    total = 0
    results = []

    for i, (ch_id, name) in enumerate(BEIN_CHANNELS, 1):
        print(f"[{i}/{len(BEIN_CHANNELS)}] {name}...", end=" ", flush=True)
        live = get_channel_data(ch_id)

        if not live:
            print("❌")
            time.sleep(0.2)
            continue

        all_text = (live.get("url", "") or "") + " " + (live.get("backup", "") or "")
        direct_links   = re.findall(r'https?://[^\s"\'\\]+\.(?:m3u8|mpd)[^\s"\'\\]*', all_text)
        redirect_links = re.findall(r'http://\.LS\.V2[^\s"\'\\]+/s', all_text)

        resolved_links = []
        for r_url in redirect_links:
            resolved = resolve_redirect(r_url)
            if resolved:
                resolved_links.append(resolved)

        final_links = list(dict.fromkeys(direct_links + resolved_links))
        if final_links:
            print(f"✅ {len(final_links)} سيرفر")
            for j, link in enumerate(final_links, 1):
                m3u8.append(f'#EXTINF:-1 tvg-id="{ch_id}",{name} (سيرفر {j})')
                m3u8.append(link)
                m3u8.append("")
                results.append({"id": ch_id, "name": name, "url": link})
            total += len(final_links)
        else:
            print("❌")
        time.sleep(0.2)

    with open(BEIN_FINAL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u8))
    print(f"\n✅ إجمالي المصدر 1: {total} سيرفر → {BEIN_FINAL_FILE}")

    return results


# ═══════════════════════════════════════════════════════════
#  المصدر 2: redperch.space
# ═══════════════════════════════════════════════════════════
REDPERCH_COOKIE = os.environ.get(
    "REDPERCH_COOKIE",
    'rplayer_access=1d442accd87af8a69978d18e1r65ca559683678661313c722667ce79dd905606'
)


def collect_source2():
    print("\n" + "═" * 60)
    print("🎯 [المصدر 2] redperch.space")
    print("═" * 60)

    headers = {
        "Cookie": REDPERCH_COOKIE,
        "User-Agent": "okhttp/4.12.0",
        "Accept": "*/*",
    }

    ids_to_test = []
    for i in range(1, 11):
        ids_to_test += [f"beinsport{i}_4K", f"beinsport{i}_HD", f"beinsport{i}"]
    ids_to_test += [
        "beinsportmax1", "beinsportmax2", "beinsportmax3", "beinsportmax4",
        "beinsportnews", "beinsportpremium1", "beinsportpremium2",
        "beinsportxtra1", "beinsportxtra2",
    ]

    print(f"⏳ فحص {len(ids_to_test)} معرّف...")
    working = []

    for channel_id in ids_to_test:
        url = f"https://redperch.space/dramacardinalv2.php?id={channel_id}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            ct = r.headers.get("Content-Type", "").lower()
            if r.status_code == 200 and ("mpegurl" in ct or "octet-stream" in ct):
                print(f"✅ {channel_id}")
                working.append({
                    "id": channel_id,
                    "name": channel_id,
                    "url": url,
                })
            else:
                print(f"❌ {channel_id} (الحالة: {r.status_code})")
        except Exception as e:
            print(f"❌ {channel_id} (خطأ: {str(e)[:30]})")

    print(f"\n🎉 المصدر 2: {len(working)} قناة عاملة")
    return working


# ═══════════════════════════════════════════════════════════
#  المصدر 3: primetv.cc.cd (ALWAN Sport)
# ═══════════════════════════════════════════════════════════
PRIMETV_BASE  = "https://primetv.cc.cd"
PRIMETV_TOKEN = "StreamAuthorized_Native_App"


def collect_source3():
    print("\n" + "═" * 60)
    print("🎯 [المصدر 3] primetv.cc.cd — ALWAN Sport 1–6")
    print("═" * 60)

    results = []
    for i in range(1, 7):
        url = f"{PRIMETV_BASE}/alwhd{i}/index.m3u8"
        print(f"▶ ALWAN Sport {i} → {url}")
        results.append({
            "id": f"alwhd{i}",
            "name": f"ALWAN Sport {i}",
            "url": url,
        })

    return results


# ═══════════════════════════════════════════════════════════
#  كتابة الملف الموحّد + JSON
# ═══════════════════════════════════════════════════════════
def write_unified(all_links):
    m3u8 = ["#EXTM3U"]
    for item in all_links:
        name = item.get("name", item.get("id", "channel"))
        m3u8.append(f'#EXTINF:-1 tvg-id="{item.get("id","")}",{name}')
        m3u8.append(item["url"])
        m3u8.append("")

    with open(BEIN_ALL_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u8))
    print(f"\n💾 ملف موحّد: {BEIN_ALL_FILE}")

    with open(BEIN_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total": len(all_links),
            "channels": all_links,
        }, f, ensure_ascii=False, indent=2)
    print(f"💾 ملف JSON: {BEIN_JSON_FILE}")


# ═══════════════════════════════════════════════════════════
#  إرسال إلى التطبيق (Webhook) — اختياري
# ═══════════════════════════════════════════════════════════
def notify_app(all_links):
    webhook = os.environ.get("APP_WEBHOOK_URL", "").strip()
    if not webhook:
        print("ℹ️  APP_WEBHOOK_URL غير مضبوط — تم تخطي الإرسال")
        return

    try:
        with open(BEIN_ALL_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        payload = {
            "type": "bein_links",
            "total": len(all_links),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "m3u8": content,
        }
        r = requests.post(webhook, json=payload, timeout=30)
        print(f"📤 Webhook → {webhook} | الحالة: {r.status_code}")
    except Exception as e:
        print(f"❌ فشل الإرسال: {e}")


# ═══════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════
def main():
    start = time.time()
    all_links = []

    for func_name, func in [
        ("source1", collect_source1),
        ("source2", collect_source2),
        ("source3", collect_source3),
    ]:
        try:
            all_links += func()
        except Exception as e:
            print(f"❌ خطأ في {func_name}: {e}")

    print("\n" + "═" * 60)
    print(f"📦 إجمالي الروابط: {len(all_links)}")
    print(f"⏱️  الزمن: {time.time() - start:.1f} ثانية")
    print("═" * 60)

    write_unified(all_links)
    notify_app(all_links)

    # فشل صريح إذا لم نجمع أي رابط (ليظهر الخطأ في GitHub Actions)
    if not all_links:
        print("❌ لم يتم جمع أي رابط!")
        sys.exit(1)


if __name__ == "__main__":
    main()

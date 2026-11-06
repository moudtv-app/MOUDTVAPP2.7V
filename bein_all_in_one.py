#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOUD TV - DRAMALIVE ONLY COLLECTOR V13.0
- يجلب كل تصنيفات تطبيق DramaLive
- يجلب كل قنوات كل تصنيف
- ينشئ ملف JSON + M3U8 لكل تصنيف منفصل
- ينشئ ملف M3U8 موحد يجمع كل التصنيفات
"""

import os
import re
import json
import time
import base64
import hashlib
import logging
import requests

from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

# ==================================================
# SETTINGS
# ==================================================
APP_NAME = "MOUD TV - DramaLive"
VERSION = "13.0"

OUTPUT_DIR = "output"
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")
CATEGORIES_DIR = os.path.join(OUTPUT_DIR, "categories")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(CATEGORIES_DIR, exist_ok=True)

KEEP_HISTORY = True

logging.basicConfig(
    filename=os.path.join(OUTPUT_DIR, "changes.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

# ==================================================
# الشعارات
# ==================================================
CHANNEL_LOGOS = {
    "beIN SPORTS 1": "https://i.ibb.co/Z9j8xcc/1746540952466.png",
    "beIN SPORTS 2": "https://i.ibb.co/jkvhHK8X/1746540948199.png",
    "beIN SPORTS 3": "https://i.ibb.co/RkqLyt1G/1746540954929.png",
    "beIN SPORTS 4": "https://i.ibb.co/qP7GZCX/1746540949804.png",
    "beIN SPORTS 5": "https://i.ibb.co/9HcbW8JB/1746540954072.png",
    "beIN SPORTS 6": "https://i.ibb.co/TMmMz3r8/1746540949013.png",
    "beIN SPORTS 7": "https://i.ibb.co/LDf6XWy5/1746540947397.png",
    "beIN SPORTS 8": "https://i.ibb.co/LzJYf9xt/1746540951661.png",
    "beIN SPORTS 9": "https://i.ibb.co/4gYJdLNw/1746540953273.png",
    "ALWAN SPORT 1": "https://i.ibb.co/xSY5mrj5/1761851652531-1.jpg",
    "ALWAN SPORT 2": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 3": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 4": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 5": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 6": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "SSC 1": "https://i.ibb.co/1K8bB6B/ssc1.png", "SSC 2": "https://i.ibb.co/Vvz3x4N/ssc2.png", 
    "SSC 3": "https://i.ibb.co/fYhFz6G/ssc3.png", "SSC 4K": "https://i.ibb.co/xL9yC8Z/ssc4k.png",
    "KSA SPORTS 1": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    "AD SPORT 1": "https://i.ibb.co/84QN1BRV/images-7-24.jpg", "AD SPORT 2": "https://i.ibb.co/bgW4zJVp/images-7-25.jpg",
    "DUBAI SPORTS 1": "https://i.ibb.co/6P6xYqZ/dubai-sports1.png",
    "ON SPORT": "https://i.ibb.co/mVF7TfsB/images-8-1.jpg",
    "STC TV": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "DEFAULT": "https://i.ibb.co/Z9j8xcc/1746540952466.png"
}

# ==================================================
# HELPERS
# ==================================================
def utc_now(): return datetime.now(timezone.utc).isoformat()
def sha256(data):
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
def is_http_url(url):
    try:
        parsed = urlparse(str(url))
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except: return False

def load_json(path):
    if not os.path.exists(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def save_json(path, data):
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)

def sanitize_filename(name):
    """تنظيف اسم الملف من الرموز غير المسموحة"""
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    name = re.sub(r'\s+', "_", name.strip())
    return name[:80] or "unknown"

def get_logo_for_channel(name, api_logo=""):
    if api_logo and is_http_url(api_logo): return api_logo
    name_upper = name.upper().strip()
    if name_upper in CHANNEL_LOGOS: return CHANNEL_LOGOS[name_upper]
    for key, logo in CHANNEL_LOGOS.items():
        if key != "DEFAULT" and (key in name_upper or name_upper in key): return logo
    return CHANNEL_LOGOS["DEFAULT"]

# ==================================================
# DramaLive Core API
# ==================================================
KEY = b"0123456789abcdef"
IV  = b"fedcba9876543210"

def aes_encrypt(data: str) -> str:
    ct = AES.new(KEY, AES.MODE_CBC, IV).encrypt(pad(data.encode(), 16))
    return base64.b64encode(ct).decode() + ":" + base64.b64encode(IV).decode()

def aes_decrypt(enc: str) -> str:
    p = enc.split(":")
    return unpad(AES.new(KEY, AES.MODE_CBC, base64.b64decode(p[1])).decrypt(base64.b64decode(p[0])), 16).decode()

def api_call(endpoint, payload, host="live.publicdataroute.cc", is_redirect=False):
    enc = aes_encrypt(json.dumps(payload, separators=(",", ":")))
    url = f"https://{host}/redirect/{endpoint}" if is_redirect else f"https://{host}/api/live/livedrama/v13.0.0/{endpoint}"
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; M2007J20CG MIUI/V12.0.9.0.QJGMIXM)"}
    try:
        if curl_requests:
            r = curl_requests.post(url, data=enc, headers=headers, timeout=15, impersonate="chrome", verify=False)
        else:
            r = requests.post(url, data=enc, headers=headers, timeout=15, verify=False)
        if r.status_code in [200, 201]: return json.loads(aes_decrypt(r.text.strip()))
    except Exception as e:
        logging.warning(f"api_call {endpoint} failed: {e}")
    return None

def base_payload():
    return {
        "user_id": "_4244_1793052507021_notloggedin.com_dramalive3",
        "device_id": "6e38bfe9-fe7e-4baf-81ae-99d214928f27",
        "device_api": "29", "version_name": "185", "language": "ar",
        "timezone": "Africa/Casablanca", "device_type": "phone",
        "KEY_ACTIVATED_TYPE": "202122", "store": "playStore",
        "isStoreVersion": True, "isPremium": False, "isCoupon_active": False, "hideAds": False,
        "appCount": json.dumps({"adsFailed": 6, "adsLoaded": 0, "adsShowed": 0, "runCount": 14}),
        "mainServer": "http://main.backendcoreapi.com/api/live/livedrama/v13.0.0/",
    }

def resolve_redirect(redirect_url, ch_id):
    payload = base_payload()
    payload.update({"id": ch_id, "url": redirect_url, "agent": "redirect"})
    data = api_call("getLiveByRedirect", payload, "redirect.publicdataroute.cc", is_redirect=True)
    if data and data.get("result") == 0:
        try: return json.loads(data.get("data", {}).get("url", "")).get("url")
        except: pass
    return None

def get_channel_data(channel_id):
    payload = base_payload()
    payload["id"] = channel_id
    data = api_call("getLiveAllStreamsById", payload)
    if data and data.get("result") == 0: return data.get("live", {})
    return None

# ==================================================
# 1. جلب كل التصنيفات (Categories/Topics)
# ==================================================
def fetch_all_categories():
    """
    يجلب قائمة بكل تصنيفات التطبيق.
    نجرّب عدة endpoints محتملة حسب بنية API التطبيق.
    """
    print("\n🎯 [جلب قائمة تصنيفات DramaLive]")
    
    # المحاولة 1: endpoint مباشر للتصنيفات
    for endpoint in ["getCategories", "getTopics", "getLiveTopics", "getAllTopics"]:
        data = api_call(endpoint, base_payload())
        if data and data.get("result") == 0:
            raw = data.get("categories") or data.get("topics") or data.get("live") or []
            if isinstance(raw, list) and raw:
                cats = []
                for c in raw:
                    cat_id = c.get("id") or c.get("id_topic") or c.get("topic_id")
                    cat_name = c.get("name") or c.get("title") or c.get("topic") or "Unknown"
                    if cat_id:
                        cats.append({
                            "id": str(cat_id),
                            "name": cat_name,
                            "type": c.get("type", "tv")
                        })
                if cats:
                    print(f"  ✅ عُثر على {len(cats)} تصنيف عبر '{endpoint}'")
                    return cats
    
    # المحاولة 2: استخدام getLiveByTopic بقيم معروفة + اكتشاف تلقائي
    print("  ⚠️ لم نعثر على endpoint مباشر للتصنيفات، نجرب القيم المعروفة...")
    
    known_topics = ["arabic_sport", "movies", "kids", "news", "documentary", "sport_global", "arabic", "islamic", "music", "entertainment"]
    found_cats = []
    for t in known_topics:
        resp = api_call("getLiveByTopic", {**base_payload(), "type": "tv", "topic": t})
        if resp and resp.get("live"):
            found_cats.append({"id": t, "name": t.replace("_", " ").title(), "type": "tv", "internal": t})
            print(f"  ✅ topic '{t}' → {len(resp['live'])} قناة")
        time.sleep(0.2)
    
    return found_cats

# ==================================================
# 2. جلب قنوات تصنيف معيّن
# ==================================================
def fetch_topic_channels(topic, category_id, filter_func=None):
    """يجلب كل قنوات topic معيّن ويعيد dict"""
    results = {}
    # إذا كان topic يحتوي على internal (اسم topic الحقيقي) نستخدمه
    real_topic = topic.get("internal", topic.get("name", "")) if isinstance(topic, dict) else topic
    type_val = topic.get("type", "tv") if isinstance(topic, dict) else "tv"
    
    resp = api_call("getLiveByTopic", {**base_payload(), "type": type_val, "topic": real_topic})
    if not resp or "live" not in resp: 
        return results

    for c in resp["live"]:
        name = c.get("name", "").strip().title()
        if not name: continue
        n_lower = name.lower()
        
        if filter_func and not filter_func(n_lower): continue
        
        ch_id = c.get("id_live")
        api_logo = c.get("logo", "") or c.get("image", "") or c.get("icon", "")
        final_logo = get_logo_for_channel(name, api_logo)
        
        print(f"    {name}...", end=" ", flush=True)
        live = get_channel_data(ch_id)
        if live:
            text = (live.get("url", "") or "") + " " + (live.get("backup", "") or "")
            links = list(dict.fromkeys(re.findall(r"https?://[^\s\"\x27\\]+\.(?:m3u8|mpd)[^\s\"\x27\\]*", text)))
            for r_url in re.findall(r"http://\.LS\.V2[^\s\"\x27\\]+/s", text):
                res = resolve_redirect(r_url, ch_id)
                if res and res not in links: links.append(res)
            if links:
                print(f"✅ {len(links)}")
                results[name] = {
                    "id": ch_id, "name": name, "logo": final_logo,
                    "category": category_id, "category_name": topic.get("name", real_topic) if isinstance(topic, dict) else real_topic,
                    "live": True, "streamType": "m3u8",
                    "servers": [{"url": l, "headers": {}} for l in links]
                }
            else: print("❌")
        else: print("❌")
        time.sleep(0.1)
    return results

# ==================================================
# M3U & SAVE
# ==================================================
def create_m3u(channels, playlist_name="DramaLive"):
    lines = ["#EXTM3U"]
    for channel in channels.values():
        name = channel["name"]
        logo = channel.get("logo", "")
        for server in channel["servers"]:
            url = server["url"]
            headers = server.get("headers", {})
            lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{playlist_name}",{name}')
            if headers:
                if headers.get("User-Agent"): lines.append("#EXTVLCOPT:http-user-agent=" + headers["User-Agent"])
                if headers.get("Referer"): lines.append("#EXTVLCOPT:http-referrer=" + headers["Referer"])
                if headers.get("x-auth-token"): lines.append("#EXTVLCOPT:http-x-auth-token=" + headers["x-auth-token"])
            lines.append(url)
    return "\n".join(lines) + "\n"

def save_category(category_name, channels):
    """يحفظ تصنيفاً واحداً كملف JSON + M3U8 منفصل"""
    safe_name = sanitize_filename(category_name)
    json_path = os.path.join(CATEGORIES_DIR, safe_name + ".json")
    m3u_path = os.path.join(CATEGORIES_DIR, safe_name + ".m3u8")
    
    data = {
        "app": APP_NAME,
        "version": VERSION,
        "category": category_name,
        "updatedAt": utc_now(),
        "channels_count": len(channels),
        "channels": channels
    }
    save_json(json_path, data)
    
    temp = m3u_path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        f.write(create_m3u(channels, playlist_name=category_name))
    os.replace(temp, m3u_path)
    return m3u_path

def save_master_playlist(all_channels_by_cat):
    """ينشئ ملف M3U8 موحد يجمع كل التصنيفات"""
    lines = ["#EXTM3U"]
    total = 0
    for cat_name, channels in all_channels_by_cat.items():
        for channel in channels.values():
            name = channel["name"]
            logo = channel.get("logo", "")
            for server in channel["servers"]:
                url = server["url"]
                headers = server.get("headers", {})
                lines.append(
                    f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" '
                    f'group-title="{cat_name}",{name}'
                )
                if headers:
                    if headers.get("User-Agent"): lines.append("#EXTVLCOPT:http-user-agent=" + headers["User-Agent"])
                    if headers.get("Referer"): lines.append("#EXTVLCOPT:http-referrer=" + headers["Referer"])
                lines.append(url)
                total += 1
    
    master_path = os.path.join(OUTPUT_DIR, "dramalive_all.m3u8")
    temp = master_path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(temp, master_path)
    print(f"\n📦 الملف الموحد: {master_path} ({total} رابط)")
    
    # نسخة JSON موحدة أيضاً
    master_json = {
        "app": APP_NAME,
        "version": VERSION,
        "updatedAt": utc_now(),
        "total_categories": len(all_channels_by_cat),
        "total_channels": sum(len(c) for c in all_channels_by_cat.values()),
        "categories": {
            cat: {"channels_count": len(chs), "channels": chs}
            for cat, chs in all_channels_by_cat.items()
        }
    }
    save_json(os.path.join(OUTPUT_DIR, "dramalive_all.json"), master_json)

# ==================================================
# MAIN
# ==================================================
def main():
    print("=" * 55)
    print("MOUD TV - DRAMALIVE ONLY COLLECTOR V13.0")
    print("=" * 55)

    if not HAS_CRYPTO:
        print("❌ تحتاج مكتبة pycryptodome: pip install pycryptodome")
        return

    # 1. جلب قائمة التصنيفات
    categories = fetch_all_categories()
    if not categories:
        print("❌ لم يتم العثور على أي تصنيف!")
        return

    print(f"\n📋 إجمالي التصنيفات: {len(categories)}")
    for c in categories:
        print(f"   • {c['name']}  (id={c['id']})")

    # 2. جلب قنوات كل تصنيف وحفظها منفصلة
    all_channels_by_cat = {}
    for cat in categories:
        cat_name = cat["name"]
        cat_id = cat["id"]
        print(f"\n🎯 [تصنيف: {cat_name}]")
        
        try:
            channels = fetch_topic_channels(cat, cat_id, filter_func=None)
            if channels:
                all_channels_by_cat[cat_name] = channels
                path = save_category(cat_name, channels)
                print(f"  💾 {path} ({len(channels)} قناة)")
            else:
                print(f"  ⚠️ لا توجد قنوات في '{cat_name}'")
        except Exception as e:
            print(f"  ❌ خطأ في '{cat_name}': {e}")
            logging.error(f"category {cat_name} failed: {e}")
        time.sleep(0.3)

    # 3. إنشاء الملفات الموحدة
    if all_channels_by_cat:
        save_master_playlist(all_channels_by_cat)
    
    # 4. ملخص
    print("\n" + "=" * 55)
    print("📊 الملخص النهائي")
    print("=" * 55)
    total = 0
    for cat, chs in all_channels_by_cat.items():
        print(f"   {cat}: {len(chs)} قناة")
        total += len(chs)
    print(f"\n   ✅ إجمالي القنوات: {total}")
    print(f"   📁 ملفات التصنيفات: {CATEGORIES_DIR}/")
    print(f"   📦 الملف الموحد: {OUTPUT_DIR}/dramalive_all.m3u8")
    print("✅ Done!")

if __name__ == "__main__":
    main()

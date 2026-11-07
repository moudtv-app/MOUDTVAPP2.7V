#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOUD TV - ULTIMATE COLLECTOR V11.1
- إضافة Azam Sports و SuperSport كملفات منفصلة من DramaLive
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
APP_NAME = "MOUD TV"
VERSION = "11.1 Ultimate"

OUTPUT_DIR = "output"
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)

KEEP_HISTORY = True

logging.basicConfig(
    filename=os.path.join(OUTPUT_DIR, "changes.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

# ==================================================
# الشعارات الافتراضية
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
    "AZAM SPORTS 1": "https://i.ibb.co/Z9j8xcc/1746540952466.png",
    "AZAM SPORTS 2": "https://i.ibb.co/Z9j8xcc/1746540952466.png",
    "SUPERSPORT 1": "https://i.ibb.co/Z9j8xcc/1746540952466.png",
    "SUPERSPORT 2": "https://i.ibb.co/Z9j8xcc/1746540952466.png",
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

def get_logo_for_channel(name, api_logo=""):
    if api_logo and is_http_url(api_logo): return api_logo
    name_upper = name.upper().strip()
    if name_upper in CHANNEL_LOGOS: return CHANNEL_LOGOS[name_upper]
    for key, logo in CHANNEL_LOGOS.items():
        if key != "DEFAULT" and (key in name_upper or name_upper in key): return logo
    return CHANNEL_LOGOS["DEFAULT"]

# ==================================================
# DramaLive Decryption & API
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
    except: pass
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
# OZ-TV & Alwan & Redperch (المصادر القديمة)
# ==================================================
def fetch_oz_tv():
    print("\n🎯 [جلب قنوات OZ-TV]")
    KEY_OZ = bytes.fromhex("4b7c9f2ae58d1b6c3f9a7e2d5c8b4f1a")
    MAGIC = b"GFEDCBA@ONMLKJIH"
    SECRET = bytes(KEY_OZ[i] ^ MAGIC[i] for i in range(16))
    try: IP = requests.get("https://api.ipify.org", timeout=10).text.strip()
    except: IP = "196.70.148.78"
    NOW = int(time.time()); EXPIRES = NOW + 21600
    data = f"{IP}-{NOW}-{EXPIRES}".encode()
    h = hashlib.sha256(SECRET + data).digest()
    TOKEN = base64.b64encode(h + b"-" + data).decode()
    CHANNELS = {"bein_sport_1": "beIN SPORTS 1", "bein_sport_2": "beIN SPORTS 2", "bein_sport_3": "beIN SPORTS 3", "bein_sport_4": "beIN SPORTS 4", "bein_sport_5": "beIN SPORTS 5", "bein_sport_7": "beIN SPORTS 7"}
    results = {}
    for ch_id, ch_name in CHANNELS.items():
        url = f"https://sr.oz-tv.space/{ch_id}/index.m3u8?token={TOKEN}"
        print(f"  {ch_name}...", end=" ", flush=True)
        try:
            r = requests.get(url, headers={"user-agent": "Mozilla/5.0", "x-auth-token": TOKEN}, timeout=15)
            if r.status_code == 200 and "#EXTM3U" in r.text:
                print("✅")
                results[ch_name] = {"id": ch_id, "name": ch_name, "logo": get_logo_for_channel(ch_name), "category": "-Oy71oID8jDKWM314zRb", "live": True, "streamType": "m3u8", "servers": [{"url": url, "headers": {"x-auth-token": TOKEN, "User-Agent": "Mozilla/5.0"}}]}
            else: print("❌")
        except: print("❌")
    return results

def fetch_alwan_live():
    print("\n🎯 [جلب قنوات Alwan Live]")
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
    BASE = "https://live.alwan.live/api_v3/service/getcardinal"
    results = {}
    for i in range(1, 10):
        ch_id = f"becardinal{i}"; name = f"ALWAN SPORT {i}"
        print(f"  {name}...", end=" ", flush=True)
        try:
            r = requests.get(f"{BASE}/{ch_id}", headers={"user-agent": UA, "weare": "rtvcardinal", "accept": "text/html,application/json,*/*"}, timeout=15)
            if r.status_code == 200:
                match = re.search(r'name="sc-session-profile" content="([^"]+)"', r.text)
                if match:
                    data = match.group(1)
                    data = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1),16)), data)
                    data = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1),16)), data)
                    if data.startswith("http"):
                        print("✅")
                        results[name] = {"id": ch_id, "name": name, "logo": get_logo_for_channel(name), "category": "-Oz-D3gFEv7WZ3nQYrSt", "live": True, "streamType": "m3u8", "servers": [{"url": data, "headers": {"User-Agent": UA}}]}
                    else: print("❌")
                else: print("❌")
            else: print("❌")
        except: print("❌")
        time.sleep(1)
    return results

def fetch_redperch():
    print("\n🎯 [جلب قنوات Redperch]")
    COOKIE = 'rplayer_access=1d442accd87af8a69978d18e1r65ca559683678661313c722667ce79dd905606'
    HEADERS = {'Cookie': COOKIE, 'User-Agent': 'okhttp/4.12.0', 'Accept': '*/*'}
    ids_to_test = []
    for i in range(1, 10): ids_to_test += [f"beinsport{i}_4K", f"beinsport{i}_HD", f"beinsport{i}"]
    ids_to_test += ["beinsportxtra1"]
    results = {}
    for channel_id in ids_to_test:
        url = f"https://redperch.space/dramacardinalv2.php?id={channel_id}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200 and 'mpegurl' in r.headers.get('Content-Type', ''):
                base_name = channel_id.split('_')[0].replace("beinsport", "beIN SPORTS ")
                if "xtra" in base_name: base_name = "beIN SPORTS XTRA"
                print(f"  {channel_id}... ✅")
                if base_name not in results:
                    results[base_name] = {"id": channel_id, "name": base_name, "logo": get_logo_for_channel(base_name), "category": "-Oy71oID8jDKWM314zRb", "live": True, "streamType": "m3u8", "servers": []}
                results[base_name]["servers"].append({"url": f"{url}|User-Agent=Rplayerv2.0.16&Cookie={COOKIE}", "headers": {"User-Agent": "Rplayerv2.0.16", "Cookie": COOKIE}})
        except: pass
    return results

# ==================================================
# دالة التجميع الرئيسية لـ DramaLive (تصنيفات مخصصة)
# ==================================================
def fetch_dramalive_topic(topic_name, category_id, filter_func=None):
    print(f"\n🎯 [جلب تصنيف DramaLive: {topic_name}]")
    results = {}
    resp = api_call("getLiveByTopic", {**base_payload(), "type": "tv", "topic": topic_name})
    if not resp or "live" not in resp: return results

    for c in resp["live"]:
        name = c.get("name", "").title()
        n_lower = name.lower()
        
        # إذا كان هناك فلتر مخصص، قم بتطبيقه
        if filter_func and not filter_func(n_lower): continue
        
        ch_id = c.get("id_live")
        api_logo = c.get("logo", "") or c.get("image", "") or c.get("icon", "")
        final_logo = get_logo_for_channel(name, api_logo)
        
        print(f"  {name}...", end=" ", flush=True)
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
                    "category": category_id, "live": True, "streamType": "m3u8",
                    "servers": [{"url": l, "headers": {}} for l in links]
                }
            else: print("❌")
        else: print("❌")
        time.sleep(0.1)
    return results

# ==================================================
# M3U & SAVE
# ==================================================
def create_m3u(channels):
    lines = ["#EXTM3U"]
    for channel in channels.values():
        name = channel["name"]
        logo = channel.get("logo", "")
        for server in channel["servers"]:
            url = server["url"]
            headers = server.get("headers", {})
            lines.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}",{name}')
            if headers:
                if headers.get("User-Agent"): lines.append("#EXTVLCOPT:http-user-agent=" + headers["User-Agent"])
                if headers.get("Referer"): lines.append("#EXTVLCOPT:http-referrer=" + headers["Referer"])
                if headers.get("x-auth-token"): lines.append("#EXTVLCOPT:http-x-auth-token=" + headers["x-auth-token"])
            lines.append(url)
    return "\n".join(lines) + "\n"

def save_source(source_name, channels):
    data = {"app": APP_NAME, "version": VERSION, "source": source_name, "updatedAt": utc_now(), "channels": channels}
    json_path = os.path.join(OUTPUT_DIR, source_name + ".json")
    m3u_path = os.path.join(OUTPUT_DIR, source_name + ".m3u8")
    save_json(json_path, data)
    temp = m3u_path + ".tmp"
    with open(temp, "w", encoding="utf-8") as f: f.write(create_m3u(channels))
    os.replace(temp, m3u_path)

def monitor_source(source_name, fetcher_func):
    print(f"\n[SCAN] {source_name}")
    try:
        channels = fetcher_func()
        if not channels: return {}
        json_path = os.path.join(OUTPUT_DIR, source_name + ".json")
        old_file = load_json(json_path)
        old_channels = old_file.get("channels", {}) if isinstance(old_file, dict) else {}
        old_hash = sha256(old_channels)
        new_hash = sha256(channels)
        if old_hash == new_hash:
            print("[UNCHANGED]")
            return channels
        if KEEP_HISTORY and old_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_json(os.path.join(HISTORY_DIR, f"{source_name}_{timestamp}.json"), old_file)
        save_source(source_name, channels)
        print(f"[UPDATED] {len(channels)} channels")
        return channels
    except Exception as error:
        print("[ERROR]", source_name, str(error))
        return None

# ==================================================
# MAIN
# ==================================================
def main():
    print("=" * 50)
    print("MOUD TV ULTIMATE COLLECTOR V11.1")
    print("=" * 50)

    # 1. المصادر الأساسية
    monitor_source("bein_dramalive", lambda: fetch_dramalive_topic("arabic_sport", "-Oy71oID8jDKWM314zRb", lambda n: "bein" in n or "beinsport" in n))
    monitor_source("arabic_dramalive", lambda: fetch_dramalive_topic("arabic_sport", "-OzEkaXpB8w2bevneCNC", lambda n: ("bein" not in n and "alwan" not in n and "azam" not in n and "super" not in n and re.search(r"[\u0600-\u06FF]", n))))
    monitor_source("alwan_dramalive", lambda: fetch_dramalive_topic("arabic_sport", "-Oz-D3gFEv7WZ3nQYrSt", lambda n: "alwan" in n))
    
    monitor_source("bein_oztv", fetch_oz_tv)
    monitor_source("alwan_live", fetch_alwan_live)
    monitor_source("bein_redperch", fetch_redperch)

    # 2. استخراج Azam Sports و SuperSport من DramaLive
    print("\n🎯 [استخراج Azam Sports من DramaLive]")
    monitor_source("azam_sports", lambda: fetch_dramalive_topic("arabic_sport", "azam", lambda n: "azam" in n))

    print("\n🎯 [استخراج SuperSport من DramaLive]")
    monitor_source("supersport", lambda: fetch_dramalive_topic("arabic_sport", "supersport", lambda n: "super" in n))

    # 3. التصنيفات الإضافية من DramaLive
    extra_topics = {
        "movies": "-P-SQj4m5683guf8BY62",
        "kids": "-P-Hwow2Rkm1UH9a9k29",
        "news": "-P-Hz4StTjPFh1M0bzQd",
        "documentary": "-P-NO5XBeTFR3gxTlfcg",
        "sport_global": "-P-SLnGBvS90DSvxj4PK"
    }
    for topic, cat_id in extra_topics.items():
        monitor_source(f"topic_{topic}", lambda t=topic, c=cat_id: fetch_dramalive_topic(t, c, None))

    print("\n✅ Done!")

if __name__ == "__main__":
    main()

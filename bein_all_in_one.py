#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOUD TV - ULTIMATE COLLECTOR V7.0
- جلب الشعارات مباشرة من API (إذا توفرت)
- فصل كل مصدر في ملفاته الخاصة
- تنزيل الشعارات محلياً
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
VERSION = "7.0 Ultimate"

OUTPUT_DIR = "output"
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")
LOGO_DIR = os.path.join(OUTPUT_DIR, "logos")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(OUTPUT_DIR, "changes.log"),
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8"
)

CHECK_TIMEOUT = 8
DOWNLOAD_LOGOS = True
KEEP_HISTORY = True

# ==================================================
# قاموس الشعارات الاحتياطي (Fallback)
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
    "beIN SPORTS NEWS": "https://i.ibb.co/Z9j8xcc/1746540952466.png",
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
def safe_name(name): return re.sub(r"[^a-zA-Z0-9_-]", "_", name)
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
    """إذا كان الـ API يوفر شعاراً، استخدمه. وإلا ابحث في القاموس."""
    if api_logo and is_http_url(api_logo):
        return api_logo
        
    name_upper = name.upper().strip()
    if name_upper in CHANNEL_LOGOS: return CHANNEL_LOGOS[name_upper]
    for key, logo in CHANNEL_LOGOS.items():
        if key != "DEFAULT" and (key in name_upper or name_upper in key): return logo
    return CHANNEL_LOGOS["DEFAULT"]

def download_logo(url, channel_name):
    if not DOWNLOAD_LOGOS or not is_http_url(url): return url
    try:
        response = requests.get(url, timeout=CHECK_TIMEOUT, stream=True)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        extensions = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        extension = next((ext for mime, ext in extensions.items() if mime in content_type), ".png")
        filename = safe_name(channel_name) + extension
        path = os.path.join(LOGO_DIR, filename)
        with open(path, "wb") as f:
            for chunk in response.iter_content(8192):
                if chunk: f.write(chunk)
        return "logos/" + filename
    except: return url

# ==================================================
# المصدر 1: DramaLive (Decryption)
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
# المصدر 2: OZ-TV Token
# ==================================================
def fetch_oz_tv():
    print("\n🎯 [جلب قنوات OZ-TV]")
    KEY_OZ = bytes.fromhex("4b7c9f2ae58d1b6c3f9a7e2d5c8b4f1a")
    MAGIC = b"GFEDCBA@ONMLKJIH"
    SECRET = bytes(KEY_OZ[i] ^ MAGIC[i] for i in range(16))
    
    try: IP = requests.get("https://api.ipify.org", timeout=10).text.strip()
    except: IP = "196.70.148.78"
        
    NOW = int(time.time())
    EXPIRES = NOW + 21600
    data = f"{IP}-{NOW}-{EXPIRES}".encode()
    h = hashlib.sha256(SECRET + data).digest()
    TOKEN = base64.b64encode(h + b"-" + data).decode()
    
    CHANNELS = {
        "bein_sport_1": "beIN SPORTS 1", "bein_sport_2": "beIN SPORTS 2",
        "bein_sport_3": "beIN SPORTS 3", "bein_sport_4": "beIN SPORTS 4",
        "bein_sport_5": "beIN SPORTS 5", "bein_sport_7": "beIN SPORTS 7",
    }
    
    results = {}
    for ch_id, ch_name in CHANNELS.items():
        url = f"https://sr.oz-tv.space/{ch_id}/index.m3u8?token={TOKEN}"
        print(f"  {ch_name}...", end=" ", flush=True)
        try:
            r = requests.get(url, headers={"user-agent": "Mozilla/5.0", "x-auth-token": TOKEN}, timeout=15)
            if r.status_code == 200 and "#EXTM3U" in r.text:
                print("✅")
                results[ch_name] = {
                    "id": ch_id, "name": ch_name, "logo": get_logo_for_channel(ch_name, ""), # لا يوجد شعار في API
                    "category": "-Oy71oID8jDKWM314zRb", "live": True, "streamType": "m3u8",
                    "servers": [{"url": url, "headers": {"x-auth-token": TOKEN, "User-Agent": "Mozilla/5.0"}}]
                }
            else: print("❌")
        except: print("❌")
    return results

# ==================================================
# FETCHERS (BeIN, Arabic, Alwan)
# ==================================================
def fetch_bein_dl():
    print("\n🎯 [جلب قنوات beIN من DramaLive]")
    bein_names = ["beIN SPORTS NEWS", "beIN SPORTS 1", "beIN SPORTS 2", "beIN SPORTS 3", "beIN SPORTS 4", "beIN SPORTS 5", "beIN SPORTS 6", "beIN SPORTS 7", "beIN SPORTS 8", "beIN SPORTS 9"]
    results = {}
    resp = api_call("getLiveByTopic", {**base_payload(), "type": "tv", "topic": "arabic_sport"})
    if resp and "live" in resp:
        for c in resp["live"]:
            name_lower = c.get("name", "").lower()
            if "bein" in name_lower or "beinsport" in name_lower:
                custom_name = c.get("name").title()
                for b_name in bein_names:
                    if b_name.lower() in custom_name.lower() or custom_name.lower().replace("beinsport", "bein sports") == b_name.lower():
                        custom_name = b_name
                        break
                ch_id = c.get("id_live")
                
                # جلب الشعار من الـ API إذا وجد
                api_logo = c.get("logo", "") or c.get("image", "") or c.get("icon", "")
                final_logo = get_logo_for_channel(custom_name, api_logo)
                
                print(f"  {custom_name}...", end=" ", flush=True)
                live = get_channel_data(ch_id)
                if live:
                    text = (live.get("url", "") or "") + " " + (live.get("backup", "") or "")
                    links = list(dict.fromkeys(re.findall(r"https?://[^\s\"\x27\\]+\.(?:m3u8|mpd)[^\s\"\x27\\]*", text)))
                    for r_url in re.findall(r"http://\.LS\.V2[^\s\"\x27\\]+/s", text):
                        res = resolve_redirect(r_url, ch_id)
                        if res and res not in links: links.append(res)
                    if links:
                        print(f"✅ {len(links)}")
                        results[custom_name] = {
                            "id": ch_id, "name": custom_name, "logo": final_logo,
                            "category": "-Oy71oID8jDKWM314zRb", "live": True, "streamType": "m3u8",
                            "servers": [{"url": l, "headers": {}} for l in links]
                        }
                    else: print("❌")
                else: print("❌")
    return results

ARABIC_SPORTS = {"stc tv", "stc tv 2", "ad sport 1", "ad sport 2", "ad sport premium 1", "ad sport premium 2", "dubai sports 1", "dubai sports 2", "dubai sports 3", "dubai racing 1", "dubai racing 2", "al iraqiya sports", "al rabiaa iraq sport", "al rabiaa iraq", "libya sport 1", "libya sport 2", "almaghribia 5", "arryadia 3", "arryadia", "mbc 1", "al ahly", "al zamalek", "on sport", "on sport 1", "on sport 2", "on sport 3", "ksa sports 1", "ksa sports 2", "ksa sports 3", "ksa sport 1", "ksa sport 2", "ksa sport 3", "ssc 1", "ssc 2", "ssc 3", "ssc 4k", "ssc action waleed", "ssc action", "thmanyah 1", "thmanyah 2", "thmanyah 3", "watania 1", "watania 2", "watania sports", "algeria 1", "algeria 6"}

def fetch_arabic():
    print("\n🎯 [جلب القنوات الرياضية العربية]")
    results = {}
    resp = api_call("getLiveByTopic", {**base_payload(), "type": "tv", "topic": "arabic_sport"})
    if not resp or "live" not in resp: return results
    for c in resp["live"]:
        name = c.get("name", "")
        n_lower = name.lower()
        if "bein" in n_lower or "beinsport" in n_lower or "alwan" in n_lower: continue
        if not any(ar in n_lower for ar in ARABIC_SPORTS) and not re.search(r"[\u0600-\u06FF]", n_lower): continue
        ch_id = c.get("id_live")
        custom_name = name.title()
        
        # جلب الشعار من الـ API إذا وجد
        api_logo = c.get("logo", "") or c.get("image", "") or c.get("icon", "")
        final_logo = get_logo_for_channel(custom_name, api_logo)
        
        print(f"  {custom_name}...", end=" ", flush=True)
        live = get_channel_data(ch_id)
        if live:
            text = (live.get("url", "") or "") + " " + (live.get("backup", "") or "")
            links = list(dict.fromkeys(re.findall(r"https?://[^\s\"\x27\\]+\.(?:m3u8|mpd)[^\s\"\x27\\]*", text)))
            for r_url in re.findall(r"http://\.LS\.V2[^\s\"\x27\\]+/s", text):
                res = resolve_redirect(r_url, ch_id)
                if res and res not in links: links.append(res)
            if links:
                print(f"✅ {len(links)}")
                results[custom_name] = {
                    "id": ch_id, "name": custom_name, "logo": final_logo,
                    "category": "-OzEkaXpB8w2bevneCNC", "live": True, "streamType": "m3u8",
                    "servers": [{"url": l, "headers": {}} for l in links]
                }
            else: print("❌")
        else: print("❌")
    return results

def fetch_alwan_prime():
    print("\n🎯 [جلب قنوات ALWAN من Primetv]")
    results = {}
    for i in range(1, 7):
        name = f"ALWAN SPORT {i}"
        url = f"https://primetv.cc.cd/alwhd{i}/index.m3u8"
        headers = {"User-Agent": "VLC/3.0", "X-Media-Access-Token": "StreamAuthorized_Native_App"}
        print(f"  {name}... ✅")
        results[name] = {
            "id": f"alwan_prime_{i}", "name": name, "logo": get_logo_for_channel(name, ""),
            "category": "-Oz-D3gFEv7WZ3nQYrSt", "live": True, "streamType": "m3u8",
            "servers": [{"url": url, "headers": headers}]
        }
    return results

def fetch_alwan_dl():
    print("\n🎯 [جلب قنوات ALWAN من DramaLive]")
    results = {}
    resp = api_call("getLiveByTopic", {**base_payload(), "type": "tv", "topic": "arabic_sport"})
    if resp and "live" in resp:
        for c in resp["live"]:
            name = c.get("name", "")
            if "alwan" in name.lower():
                ch_id = c.get("id_live")
                custom_name = name.title().replace("Alwan", "ALWAN SPORT")
                
                # جلب الشعار من الـ API إذا وجد
                api_logo = c.get("logo", "") or c.get("image", "") or c.get("icon", "")
                final_logo = get_logo_for_channel(custom_name, api_logo)
                
                print(f"  {custom_name}...", end=" ", flush=True)
                live = get_channel_data(ch_id)
                if live:
                    text = (live.get("url", "") or "") + " " + (live.get("backup", "") or "")
                    links = list(dict.fromkeys(re.findall(r"https?://[^\s\"\x27\\]+\.(?:m3u8|mpd)[^\s\"\x27\\]*", text)))
                    for r_url in re.findall(r"http://\.LS\.V2[^\s\"\x27\\]+/s", text):
                        res = resolve_redirect(r_url, ch_id)
                        if res and res not in links: links.append(res)
                    if links:
                        print(f"✅ {len(links)}")
                        if custom_name in results: results[custom_name]["servers"].extend([{"url": l, "headers": {}} for l in links])
                        else:
                            results[custom_name] = {
                                "id": ch_id, "name": custom_name, "logo": final_logo,
                                "category": "-Oz-D3gFEv7WZ3nQYrSt", "live": True, "streamType": "m3u8",
                                "servers": [{"url": l, "headers": {}} for l in links]
                            }
                    else: print("❌")
                else: print("❌")
    return results

# ==================================================
# M3U EXPORT & SAVE
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
        for name, ch in channels.items():
            if DOWNLOAD_LOGOS and is_http_url(ch["logo"]): ch["logo"] = download_logo(ch["logo"], name)
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
    print("MOUD TV ULTIMATE COLLECTOR V7.0")
    print("=" * 50)

    monitor_source("bein_dramalive", fetch_bein_dl)
    monitor_source("bein_oztv", fetch_oz_tv)
    monitor_source("arabic_dramalive", fetch_arabic)
    monitor_source("alwan_primetv", fetch_alwan_prime)
    monitor_source("alwan_dramalive", fetch_alwan_dl)

    print("\n✅ Done!")

if __name__ == "__main__":
    main()

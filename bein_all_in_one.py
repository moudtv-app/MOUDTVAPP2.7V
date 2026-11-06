#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOUD TV - ULTIMATE COLLECTOR V4.0
مع جلب الشعارات الحقيقية وتنزيلها محلياً
"""

import os
import re
import json
import time
import base64
import hashlib
import logging
import requests

from copy import deepcopy
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
VERSION = "4.0 Ultimate"

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
# قاموس الشعارات الحقيقية (Logos Dictionary)
# ==================================================
CHANNEL_LOGOS = {
    # beIN SPORTS
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
    
    # ALWAN SPORTS
    "ALWAN SPORT 1": "https://i.ibb.co/xSY5mrj5/1761851652531-1.jpg",
    "ALWAN SPORT 2": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 3": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 4": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 5": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    "ALWAN SPORT 6": "https://i.ibb.co/N6zLf9N2/1761851652531-1.jpg",
    
    # SSC Sports (السعودية)
    "SSC 1": "https://i.ibb.co/1K8bB6B/ssc1.png",
    "SSC 2": "https://i.ibb.co/Vvz3x4N/ssc2.png",
    "SSC 3": "https://i.ibb.co/fYhFz6G/ssc3.png",
    "SSC 4K": "https://i.ibb.co/xL9yC8Z/ssc4k.png",
    "SSC ACTION": "https://i.ibb.co/gJpWqH4/ssc-action.png",
    "SSC EXTRA 1": "https://i.ibb.co/L5tX9B2/ssc-extra1.png",
    "SSC EXTRA 2": "https://i.ibb.co/M6wY8V3/ssc-extra2.png",
    "SSC EXTRA 3": "https://i.ibb.co/P8kZ7V4/ssc-extra3.png",
    
    # KSA Sports
    "KSA SPORTS 1": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    "KSA SPORTS 2": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    "KSA SPORTS 3": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    "KSA SPORT 1": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    "KSA SPORT 2": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    "KSA SPORT 3": "https://i.ibb.co/FLn1py5D/images-8-3.jpg",
    
    # AD Sports (أبوظبي)
    "AD SPORT 1": "https://i.ibb.co/84QN1BRV/images-7-24.jpg",
    "AD SPORT 2": "https://i.ibb.co/bgW4zJVp/images-7-25.jpg",
    "AD SPORT PREMIUM 1": "https://i.ibb.co/84QN1BRV/images-7-24.jpg",
    "AD SPORT PREMIUM 2": "https://i.ibb.co/bgW4zJVp/images-7-25.jpg",
    
    # Dubai Sports
    "DUBAI SPORTS 1": "https://i.ibb.co/6P6xYqZ/dubai-sports1.png",
    "DUBAI SPORTS 2": "https://i.ibb.co/8N5zXvB/dubai-sports2.png",
    "DUBAI SPORTS 3": "https://i.ibb.co/7K4yWqC/dubai-sports3.png",
    "DUBAI RACING 1": "https://i.ibb.co/9M3vXzD/dubai-racing1.png",
    "DUBAI RACING 2": "https://i.ibb.co/5L2wYtE/dubai-racing2.png",
    
    # MBC
    "MBC 1": "https://i.ibb.co/nsmS6mrR/images-4-11.jpg",
    
    # ON Sport (مصر)
    "ON SPORT": "https://i.ibb.co/mVF7TfsB/images-8-1.jpg",
    "ON SPORT 1": "https://i.ibb.co/mVF7TfsB/images-8-1.jpg",
    "ON SPORT 2": "https://i.ibb.co/mVF7TfsB/images-8-1.jpg",
    "ON SPORT 3": "https://i.ibb.co/mVF7TfsB/images-8-1.jpg",
    
    # STC TV
    "STC TV": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "STC TV 2": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    
    # Others
    "AL AHLY": "https://i.ibb.co/7J1zmwgx/images-3-16.jpg",
    "AL ZAMALEK": "https://i.ibb.co/7J1zmwgx/images-3-16.jpg",
    "ALMAGHRIBIA 5": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "ARRYADIA 3": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "ARRYADIA": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "WATANIA 1": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "WATANIA 2": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "WATANIA SPORTS": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "ALGERIA 1": "https://i.ibb.co/35N9nq7K/images-8-7.jpg",
    "ALGERIA 6": "https://i.ibb.co/35N9nq7K/images-8-7.jpg",
    "THMANYAH 1": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "THMANYAH 2": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    "THMANYAH 3": "https://i.ibb.co/6R1Xg0hz/images-3-29.jpg",
    
    # Default Logo
    "DEFAULT": "https://i.ibb.co/Z9j8xcc/1746540952466.png"
}

# ==================================================
# HELPERS
# ==================================================
def utc_now():
    return datetime.now(timezone.utc).isoformat()

def sha256(data):
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def safe_name(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)

def is_http_url(url):
    try:
        parsed = urlparse(str(url))
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def load_json(path):
    if not os.path.exists(path): return None
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except (OSError, json.JSONDecodeError): return None

def save_json(path, data):
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)

def get_logo_for_channel(name):
    """البحث عن الشعار المناسب للقناة"""
    name_upper = name.upper().strip()
    
    # البحث المباشر
    if name_upper in CHANNEL_LOGOS:
        return CHANNEL_LOGOS[name_upper]
    
    # البحث التقريبي (إذا كان الاسم يحتوي على كلمة من القاموس)
    for key, logo in CHANNEL_LOGOS.items():
        if key != "DEFAULT" and (key in name_upper or name_upper in key):
            return logo
            
    return CHANNEL_LOGOS["DEFAULT"]

# ==================================================
# LOGO DOWNLOADER
# ==================================================
def download_logo(url, channel_name):
    if not DOWNLOAD_LOGOS or not is_http_url(url): return url
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https": return url
        response = requests.get(url, timeout=CHECK_TIMEOUT, stream=True)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        extensions = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "image/gif": ".gif"}
        extension = next((ext for mime, ext in extensions.items() if mime in content_type), ".png")
        
        filename = safe_name(channel_name) + extension
        path = os.path.join(LOGO_DIR, filename)
        
        with open(path, "wb") as f:
            for chunk in response.iter_content(8192):
                if chunk: f.write(chunk)
                
        return "logos/" + filename
    except Exception as e:
        logging.warning(f"Logo download failed: {channel_name} | {e}")
        return url

# ==================================================
# DRAMALIVE DECRYPTION
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
        if r.status_code in [200, 201]:
            return json.loads(aes_decrypt(r.text.strip()))
    except Exception:
        pass
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
        try:
            return json.loads(data.get("data", {}).get("url", "")).get("url")
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

# ==================================================
# FETCHERS
# ==================================================
def fetch_bein():
    print("\n🎯 [جلب قنوات beIN SPORTS]")
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
                            "id": ch_id, "name": custom_name, "logo": get_logo_for_channel(custom_name),
                            "category": "-Oy71oID8jDKWM314zRb", "live": True, "streamType": "m3u8",
                            "servers": [{"url": l, "headers": {}} for l in links]
                        }
                    else: print("❌")
                else: print("❌")
    return results

ARABIC_SPORTS = {
    "stc tv", "stc tv 2", "ad sport 1", "ad sport 2", "ad sport premium 1", "ad sport premium 2",
    "dubai sports 1", "dubai sports 2", "dubai sports 3", "dubai racing 1", "dubai racing 2",
    "al iraqiya sports", "al rabiaa iraq sport", "al rabiaa iraq", "libya sport 1", "libya sport 2",
    "almaghribia 5", "arryadia 3", "arryadia", "mbc 1", "al ahly", "al zamalek", "on sport", 
    "on sport 1", "on sport 2", "on sport 3", "ksa sports 1", "ksa sports 2", "ksa sports 3", 
    "ksa sport 1", "ksa sport 2", "ksa sport 3", "ssc 1", "ssc 2", "ssc 3", "ssc 4k", 
    "ssc action waleed", "ssc action", "thmanyah 1", "thmanyah 2", "thmanyah 3", "watania 1", 
    "watania 2", "watania sports", "algeria 1", "algeria 6",
}

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
                    "id": ch_id, "name": custom_name, "logo": get_logo_for_channel(custom_name),
                    "category": "-OzEkaXpB8w2bevneCNC", "live": True, "streamType": "m3u8",
                    "servers": [{"url": l, "headers": {}} for l in links]
                }
            else: print("❌")
        else: print("❌")
    return results

def fetch_alwan():
    print("\n🎯 [جلب قنوات ALWAN SPORTS]")
    results = {}
    for i in range(1, 7):
        name = f"ALWAN SPORT {i}"
        url = f"https://primetv.cc.cd/alwhd{i}/index.m3u8"
        headers = {"User-Agent": "VLC/3.0", "X-Media-Access-Token": "StreamAuthorized_Native_App"}
        print(f"  {name} (Primetv)... ✅")
        results[name] = {
            "id": f"alwan_{i}", "name": name, "logo": get_logo_for_channel(name),
            "category": "-Oz-D3gFEv7WZ3nQYrSt", "live": True, "streamType": "m3u8",
            "servers": [{"url": url, "headers": headers}]
        }

    resp = api_call("getLiveByTopic", {**base_payload(), "type": "tv", "topic": "arabic_sport"})
    if resp and "live" in resp:
        for c in resp["live"]:
            name = c.get("name", "")
            if "alwan" in name.lower():
                ch_id = c.get("id_live")
                custom_name = name.title().replace("Alwan", "ALWAN SPORT")
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
                                "id": ch_id, "name": custom_name, "logo": get_logo_for_channel(custom_name),
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
        if not channels:
            print("[WARNING] Empty source")
            return {}

        # تنزيل الشعارات
        for name, ch in channels.items():
            if DOWNLOAD_LOGOS and is_http_url(ch["logo"]):
                ch["logo"] = download_logo(ch["logo"], name)

        json_path = os.path.join(OUTPUT_DIR, source_name + ".json")
        old_file = load_json(json_path)
        old_channels = old_file.get("channels", {}) if isinstance(old_file, dict) else {}

        # الفحص الذكي
        old_hash = sha256(old_channels)
        new_hash = sha256(channels)

        if old_hash == new_hash:
            print("[UNCHANGED] No changes")
            return channels

        # حفظ التاريخ
        if KEEP_HISTORY and old_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_json(os.path.join(HISTORY_DIR, f"{source_name}_{timestamp}.json"), old_file)

        save_source(source_name, channels)
        print(f"[UPDATED] {len(channels)} channels")
        return channels

    except Exception as error:
        logging.exception(f"Source error: {source_name}")
        print("[ERROR]", source_name, str(error))
        return None

# ==================================================
# MAIN
# ==================================================
def main():
    print("=" * 50)
    print("MOUD TV ULTIMATE COLLECTOR V4.0")
    print("=" * 50)

    all_sources = {}
    all_sources["bein"] = monitor_source("bein", fetch_bein)
    all_sources["arabic"] = monitor_source("arabic", fetch_arabic)
    all_sources["alwan"] = monitor_source("alwan", fetch_alwan)

    # دمج الكل
    merged = {}
    for source_name, channels in all_sources.items():
        if channels is None: continue
        for name, channel in channels.items():
            merged[f"{source_name}_{name}"] = deepcopy(channel)

    if merged:
        data = {"app": APP_NAME, "updatedAt": utc_now(), "totalChannels": len(merged), "channels": merged}
        json_path = os.path.join(OUTPUT_DIR, "all_channels.json")
        m3u_path = os.path.join(OUTPUT_DIR, "all_channels.m3u8")
        
        old = load_json(json_path)
        if not old or sha256(old.get("channels", {})) != sha256(merged):
            save_json(json_path, data)
            temp = m3u_path + ".tmp"
            with open(temp, "w", encoding="utf-8") as f: f.write(create_m3u(merged))
            os.replace(temp, m3u_path)
            print(f"[UNIFIED] {len(merged)} channels saved")
        else:
            print("[UNIFIED] Unchanged")

    print("\n✅ Done!")

if __name__ == "__main__":
    main()

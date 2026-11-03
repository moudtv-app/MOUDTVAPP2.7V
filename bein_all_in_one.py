#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bein_all_in_one.py
سكربت متكامل (بدون فحص) لجلب وتصنيف القنوات الرياضية (بين، عربية، الوان)
"""

import os
import base64
import json
import re
import time
import uuid
import sys

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

import requests

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
#  إعدادات الفحص (تم إيقافه للسرعة القصوى)
# ═══════════════════════════════════════════════════════════
CHECK_SERVERS = False 
MAX_SERVERS_TO_CHECK = 3 
CHECK_TIMEOUT = 3         

# ═══════════════════════════════════════════════════════════
#  الشعارات
# ═══════════════════════════════════════════════════════════
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
    "DEFAULT": "https://i.ibb.co/Z9j8xcc/1746540952466.png"
}

# ═══════════════════════════════════════════════════════════
#  المصدر 1: DramaLive
# ═══════════════════════════════════════════════════════════
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

def check_url(url):
    # تم إيقاف الفحص تماماً
    return True

# ═══════════════════════════════════════════════════════════
#  تجميع القنوات
# ═══════════════════════════════════════════════════════════
def get_bein_channels():
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
                    
                    # بدون فحص - نأخذ كل السيرفرات
                    if links:
                        print(f"✅ {len(links)}")
                        if custom_name not in results: results[custom_name] = []
                        results[custom_name].extend(links)
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

def get_arabic_channels():
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
                if custom_name not in results: results[custom_name] = []
                results[custom_name].extend(links)
            else: print("❌")
        else: print("❌")
    return results

def get_alwan_channels():
    print("\n🎯 [جلب قنوات ALWAN SPORTS]")
    results = {}
    for i in range(1, 7):
        name = f"ALWAN SPORT {i}"
        url = f"https://primetv.cc.cd/alwhd{i}/index.m3u8|User-Agent=VLC/3.0&otherHeaders=X-Media-Access-Token: StreamAuthorized_Native_App"
        print(f"  {name} (Primetv)... ✅")
        if name not in results: results[name] = []
        results[name].append(url)

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
                        if custom_name not in results: results[custom_name] = []
                        results[custom_name].extend(links)
                    else: print("❌")
                else: print("❌")
    return results

# ═══════════════════════════════════════════════════════════
#  الحفظ
# ═══════════════════════════════════════════════════════════
def save_files(data, prefix, category_id):
    final_json = {"channels": {}}
    m3u8_lines = ["#EXTM3U"]
    order_counter = 1
    
    for ch_name, links in data.items():
        servers_array = []
        for link in links:
            servers_array.append(f"{link}|name={ch_name}")
            m3u8_lines.append(f'#EXTINF:-1 tvg-id="{ch_name.replace(" ", "_")}" tvg-logo="{CHANNEL_LOGOS.get(ch_name, CHANNEL_LOGOS["DEFAULT"])}",{ch_name}')
            m3u8_lines.append(link)
            
        ch_id = f"-{prefix}_{uuid.uuid4().hex[:10]}"
        final_json["channels"][ch_id] = {
            "category": category_id,
            "live": True,
            "logo": CHANNEL_LOGOS.get(ch_name, CHANNEL_LOGOS["DEFAULT"]),
            "name": ch_name,
            "order": order_counter,
            "servers": servers_array,
            "streamUrl": "|".join(servers_array)
        }
        order_counter += 1

    with open(os.path.join(OUTPUT_DIR, f"{prefix}.json"), "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, f"{prefix}.m3u8"), "w", encoding="utf-8") as f:
        f.write("\n".join(m3u8_lines))
    print(f"✅ تم حفظ: {prefix}.json و {prefix}.m3u8")

# ═══════════════════════════════════════════════════════════
#  main
# ═══════════════════════════════════════════════════════════
def main():
    start_time = time.time()
    print("⏳ البدء (بدون فحص - سرعة قصوى)...")
    
    bein_data = get_bein_channels()
    if bein_data: save_files(bein_data, "bein", "-Oy71oID8jDKWM314zRb")

    arabic_data = get_arabic_channels()
    if arabic_data: save_files(arabic_data, "arabic", "-OzEkaXpB8w2bevneCNC")

    alwan_data = get_alwan_channels()
    if alwan_data: save_files(alwan_data, "alwan", "-Oz-D3gFEv7WZ3nQYrSt")

    elapsed = time.time() - start_time
    print(f"\n🎉 انتهى كل شيء في {elapsed:.1f} ثانية!")

if __name__ == "__main__":
    main()

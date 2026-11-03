#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bein_all_in_one.py
سكربت موحّد لجلب روابط beIN Sports وتصديرها بصيغة JSON و M3U8
"""

import os
import base64
import json
import re
import time
import uuid

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None
    print("⚠️ curl_cffi غير مثبّت — سيتم استخدام requests العادي")

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False
    print("⚠️ pycryptodome غير مثبّت — المصدر 1 لن يعمل")

import requests

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
#  الشعارات الخاصة بالقنوات
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
}

# ═══════════════════════════════════════════════════════════
#  المصدر 1: publicdataroute (DramaLive)
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
    url = f"https://{host}/redirect/{endpoint}" if is_redirect else f"https://{host}/api/live/livedrama/v13.0.0/{endpoint}"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 10; M2007J20CG MIUI/V12.0.9.0.QJGMIXM)",
    }
    try:
        if curl_requests:
            r = curl_requests.post(url, data=enc, headers=headers, timeout=20, impersonate="chrome", verify=False)
        else:
            r = requests.post(url, data=enc, headers=headers, timeout=20, verify=False)
        if r.status_code in (200, 201):
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
        "isStoreVersion": True, "isPremium": False,
        "isCoupon_active": False, "hideAds": False,
        "appCount": json.dumps({"adsFailed": 1, "adsLoaded": 0, "adsShowed": 0, "runCount": 4}),
        "mainServer": "http://main.backendcoreapi.com/api/live/livedrama/v13.0.0/",
    }

def resolve_redirect(redirect_url):
    payload = base_payload()
    payload["id"] = "live_tv_beinsport1"
    payload["url"] = redirect_url
    payload["agent"] = "redirect"
    data = api_call("getLiveByRedirect", payload, "redirect.publicdataroute.cc", is_redirect=True)
    if data and data.get("result") == 0:
        try:
            inner_json = data.get("data", {}).get("url", "")
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
    ("live_tv_beinsport1", "beIN SPORTS 1"),
    ("live_tv_beinsport2", "beIN SPORTS 2"),
    ("live_tv_beinsport3", "beIN SPORTS 3"),
    ("live_tv_beinsport4", "beIN SPORTS 4"),
    ("live_tv_beinsport5", "beIN SPORTS 5"),
    ("live_tv_beinsport6", "beIN SPORTS 6"),
    ("live_tv_beinsport7", "beIN SPORTS 7"),
    ("live_tv_beinsport8", "beIN SPORTS 8"),
    ("live_tv_beinsport9", "beIN SPORTS 9"),
    ("live_tv_beinsportnews", "beIN SPORTS NEWS"),
]

def collect_source1():
    print("\n🎯 [المصدر 1] DramaLive (publicdataroute)")
    if not HAS_CRYPTO: return {}
    
    results = {}
    for ch_id, name in BEIN_CHANNELS:
        print(f"جلب {name}...", end=" ", flush=True)
        live = get_channel_data(ch_id)
        if not live:
            print("❌")
            continue
            
        all_text = (live.get("url", "") or "") + " " + (live.get("backup", "") or "")
        direct_links = re.findall(r'https?://[^\s"\'\\]+\.(?:m3u8|mpd)[^\s"\'\\]*', all_text)
        redirect_links = re.findall(r'http://\.LS\.V2[^\s"\'\\]+/s', all_text)
        
        resolved_links = []
        for r_url in redirect_links:
            resolved = resolve_redirect(r_url)
            if resolved: resolved_links.append(resolved)
            
        final_links = list(dict.fromkeys(direct_links + resolved_links))
        if final_links:
            print(f"✅ {len(final_links)}")
            results[name] = final_links
        else:
            print("❌")
        time.sleep(0.2)
    return results

# ═══════════════════════════════════════════════════════════
#  المصدر 2: redperch.space
# ═══════════════════════════════════════════════════════════
REDPERCH_COOKIE = os.environ.get("REDPERCH_COOKIE", 'rplayer_access=1d442accd87af8a69978d18e1r65ca559683678661313c722667ce79dd905606')

def collect_source2():
    print("\n🎯 [المصدر 2] redperch.space")
    headers = {"Cookie": REDPERCH_COOKIE, "User-Agent": "okhttp/4.12.0", "Accept": "*/*"}
    results = {}
    
    for i in range(1, 10):
        name = f"beIN SPORTS {i}"
        ids_to_test = [f"beinsport{i}_4K", f"beinsport{i}_HD", f"beinsport{i}"]
        found_links = []
        
        print(f"جلب {name}...", end=" ", flush=True)
        for channel_id in ids_to_test:
            url = f"https://redperch.space/dramacardinalv2.php?id={channel_id}"
            try:
                r = requests.get(url, headers=headers, timeout=10)
                ct = r.headers.get("Content-Type", "").lower()
                if r.status_code == 200 and ("mpegurl" in ct or "octet-stream" in ct):
                    link_with_headers = f"{url}|User-Agent=Rplayerv2.0.16&Cookie={REDPERCH_COOKIE}"
                    found_links.append(link_with_headers)
                    break
            except Exception:
                pass
        
        if found_links:
            print("✅")
            results[name] = found_links
        else:
            print("❌")
            
    return results

# ═══════════════════════════════════════════════════════════
#  المصدر 3: primetv.cc.cd (ALWAN)
# ═══════════════════════════════════════════════════════════
def collect_source3():
    print("\n🎯 [المصدر 3] primetv.cc.cd (ALWAN Sport)")
    results = {}
    for i in range(1, 7):
        name = f"ALWAN SPORT {i}"
        url = f"https://primetv.cc.cd/alwhd{i}/index.m3u8|User-Agent=VLC/3.0&otherHeaders=X-Media-Access-Token: StreamAuthorized_Native_App"
        print(f"جلب {name}... ✅")
        results[name] = [url]
    return results

# ═══════════════════════════════════════════════════════════
#  دمج النتائج وتوليد JSON + M3U8
# ═══════════════════════════════════════════════════════════
def main():
    all_data = {}
    
    # دمج النتائج حسب اسم القناة
    for source_func in [collect_source1, collect_source2, collect_source3]:
        source_results = source_func()
        for ch_name, links in source_results.items():
            if ch_name not in all_data:
                all_data[ch_name] = []
            all_data[ch_name].extend(links)

    # 1. بناء هيكل JSON
    final_json = {"channels": {}}
    # 2. بناء هيكل M3U8
    m3u8_lines = ["#EXTM3U"]
    
    order_counter = 1
    
    for ch_name, links in all_data.items():
        servers_array = []
        for idx, link in enumerate(links, 1):
            # --- التعديل هنا: إزالة أسماء المصادر وجعل الاسم هو اسم القناة ---
            server_name = ch_name 
                
            # إضافة السيرفر للـ JSON
            servers_array.append(f"{link}|name={server_name}")
            
            # إضافة السيرفر للـ M3U8
            m3u8_lines.append(f'#EXTINF:-1 tvg-id="{ch_name.replace(" ", "_")}" tvg-logo="{CHANNEL_LOGOS.get(ch_name, "")}",{ch_name}')
            m3u8_lines.append(link)
            
        # إنشاء قناة جديدة بنفس هيكل تطبيقك في JSON
        ch_id = f"-Generated_{uuid.uuid4().hex[:10]}"
        final_json["channels"][ch_id] = {
            "category": "-Oy71oID8jDKWM314zRb", # تصنيف beIN SPORTS MO
            "live": True,
            "logo": CHANNEL_LOGOS.get(ch_name, "https://i.ibb.co/Z9j8xcc/1746540952466.png"),
            "name": ch_name,
            "order": order_counter,
            "servers": servers_array,
            "streamUrl": "|".join(servers_array)
        }
        order_counter += 1

    # حفظ ملف JSON
    with open(os.path.join(OUTPUT_DIR, "channels.json"), "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)
        
    # حفظ ملف M3U8
    with open(os.path.join(OUTPUT_DIR, "bein_all.m3u8"), "w", encoding="utf-8") as f:
        f.write("\n".join(m3u8_lines))
        
    print(f"\n✅ تم إنشاء الملفين بنجاح في مجلد output:")
    print(f"1. channels.json (لتطبيقك)")
    print(f"2. bein_all.m3u8 (للمشغلات)")

if __name__ == "__main__":
    main()

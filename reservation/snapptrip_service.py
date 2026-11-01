import logging
import random
import re
import threading
import time
from datetime import datetime, timedelta
from decimal import Decimal
import requests
import jdatetime
from django.conf import settings
from django.db.models import Q
from .models import (
    Hotel,
    Room,
    RoomDatePrice,
    CancellationPenalty,
    SnappHotelDirectory,
    SnappTripSetting,
    City,
    RoomService,
    Reservationhotel
)

logger = logging.getLogger(__name__)

# نگاشت کامل شناسه‌های شهری اسنپ‌تریپ
IRAN_CITIES_MAP = {
    '6208': 'تهران', 'tehran': 'تهران', '1': 'تهران',
    '6209': 'مشهد', 'mashhad': 'مشهد', '2': 'مشهد',
    '6216': 'اصفهان', 'isfahan': 'اصفهان', '3': 'اصفهان',
    '6220': 'شیراز', 'shiraz': 'شیراز', '4': 'شیراز',
    '6224': 'تبریز', 'tabriz': 'تبریز', '5': 'تبریز',
    '6225': 'کیش', 'kish': 'کیش', '6': 'کیش',
    '6234': 'قشم', 'qeshm': 'قشم', '7': 'قشم',
    '6237': 'یزد', 'yazd': 'یزد', '8': 'یزد',
    '6260': 'رشت', 'rasht': 'رشت', '9': 'رشت',
    '6262': 'ساری', 'sari': 'ساری', '10': 'ساری',
    '6264': 'رامسر', 'ramsar': 'رامسر', '11': 'رامسر',
    '6269': 'کرمان', 'kerman': 'کرمان', '12': 'کرمان',
    '6288': 'اهواز', 'ahvaz': 'اهواز', '13': 'اهواز',
    '6289': 'بندرعباس', 'bandarabbas': 'بندرعباس', '14': 'بندرعباس',
    '6303': 'کرمانشاه', 'kermanshah': 'کرمانشاه', '15': 'کرمانشاه',
    '6319': 'همدان', 'hamedan': 'همدان', '16': 'همدان',
    '6321': 'قم', 'qom': 'قم', '17': 'قم',
    '6326': 'اراک', 'arak': 'اراک', '18': 'اراک',
    '6336': 'زنجان', 'zanjan': 'زنجان', '19': 'زنجان',
    '6341': 'سنندج', 'sanandaj': 'سنندج', '20': 'سنندج',
    '6349': 'ارومیه', 'urmia': 'ارومیه', '21': 'ارومیه',
    '6352': 'اردبیل', 'ardabil': 'اردبیل', '22': 'اردبیل',
    '6363': 'کاشان', 'kashan': 'کاشان', '23': 'کاشان',
    '6390': 'گرگان', 'gorgan': 'گرگان', '24': 'گرگان',
    '6433': 'چابهار', 'chabahar': 'چابهار', '25': 'چابهار',
    '6447': 'بوشهر', 'bushehr': 'بوشهر', '26': 'بوشهر',
    '6452': 'چالوس', 'chalus': 'چالوس', '27': 'چالوس',
    '6460': 'نوشهر', 'noshahr': 'نوشهر', '28': 'نوشهر',
    '6469': 'لاهیجان', 'lahijan': 'لاهیجان', '29': 'لاهیجان',
    '6497': 'بندر انزلی', 'anzali': 'بندر انزلی', '30': 'انزلی',
    '6503': 'سرعین', 'sarein': 'سرعین',
}

BOARD_TYPE_TITLES = {
    'room_only': 'اقامت بدون صبحانه',
    'bed_breakfast': 'صبحانه بوفه رایگان',
    'half_board': 'هافبرد (صبحانه + یک وعده غذا)',
    'full_board': 'فولبرد (صبحانه + ناهار + شام)',
}

PERSIAN_CAPACITY_WORDS = {
    'یک': 1, 'سینگل': 1, 'تک': 1,
    'دو': 2, 'دبل': 2, 'توئین': 2,
    'سه': 3, 'تریپل': 3,
    'چهار': 4, 'کواد': 4,
    'پنج': 5,
    'شش': 6,
    'هفت': 7,
    'هشت': 8,
    'نه': 9,
    'ده': 10,
}


def get_snapptrip_client_config():
    """خواندن آدرس و کلید API از تنظیمات پنل ادمین"""
    setting = SnappTripSetting.objects.first()
    if setting and setting.is_active and setting.api_key:
        base_url = setting.base_url.rstrip('/')
        api_key = setting.api_key.strip()
    else:
        base_url = getattr(settings, 'SNAPPE_TRIP_BASE_URL', 'https://b2bapiv2.snapptrip.com').rstrip('/')
        api_key = getattr(settings, 'SNAPPE_TRIP_API_KEY', '')

    headers = {
        'api-key': api_key,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    return base_url, headers


def get_snapptrip_wallet_balance():
    """استعلام موجودی کیف پول B2B در اسنپ‌تریپ (GET /balance/)"""
    base_url, headers = get_snapptrip_client_config()
    try:
        res = requests.get(f"{base_url}/balance/", headers=headers, timeout=12)
        if res.status_code == 200:
            data = res.json()
            return data.get('balance', 0), "موفق"
        return 0, f"کد {res.status_code}: {res.text[:100]}"
    except Exception as e:
        return 0, str(e)


def fetch_with_rate_limit(url, headers, max_retries=3):
    """ارسال امن درخواست با مدیریت خطای 429"""
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 429:
                logger.warning("محدودیت Rate Limit اسنپ (429). ۱۰ ثانیه توقف...")
                time.sleep(10)
                continue
            return res
        except Exception:
            time.sleep(1.5)
    return None


def extract_list_from_response(data):
    """استخراج هوشمند آرایه از ساختارهای مختلف پاسخ وب‌سرویس اسنپ"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ['availability', 'rooms', 'room', 'data', 'results', 'result', 'hotels', 'cities', 'items', 'list']:
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                return val
            if isinstance(val, dict):
                nested = extract_list_from_response(val)
                if nested:
                    return nested
        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                return val
    return []


def extract_room_id(r_item):
    """استخراج شناسه عددی اتاق"""
    if not isinstance(r_item, dict):
        if isinstance(r_item, (int, str)) and str(r_item).isdigit():
            return int(r_item)
        return None

    for nested_key in ['room', 'room_type', 'details']:
        if isinstance(r_item.get(nested_key), dict):
            sub_id = extract_room_id(r_item[nested_key])
            if sub_id:
                return sub_id

    for key in ['id', 'room_id', 'room_type_id', 'roomTypeId', 'roomId', 'code', 'room_code', 'hotel_room_id', 'uid', 'pk']:
        val = r_item.get(key)
        if val is not None and str(val).strip() != '':
            try:
                return int(val)
            except (ValueError, TypeError):
                return str(val)
    return None


def extract_room_title(r_item, default_id):
    """استخراج عنوان واقعی اتاق از تمام کلیدها و آبجکت‌های تودرتوی اسنپ"""
    if not isinstance(r_item, dict):
        return f"اتاق {default_id}"

    for nested_key in ['room_type', 'room', 'details', 'roomType', 'info']:
        nested_obj = r_item.get(nested_key)
        if isinstance(nested_obj, dict):
            title = extract_room_title(nested_obj, None)
            if title and not title.startswith("اتاق None") and not title.isdigit():
                return title
        elif isinstance(nested_obj, str) and nested_obj.strip() and not nested_obj.strip().isdigit():
            return nested_obj.strip()

    for key in ['name_fa', 'title_fa', 'room_type_name', 'room_name', 'name', 'title', 'room_title', 'persian_title']:
        val = r_item.get(key)
        if val and isinstance(val, str) and val.strip() and not val.strip().isdigit():
            return val.strip()

    return f"اتاق {default_id}"


def extract_room_capacity(r_item, room_title=""):
    """استخراج دقیق و تضمینی ظرفیت اصلی اتاق (از وب‌سرویس و از روی عنوان)"""
    candidate_keys = ['capacity', 'room_capacity', 'standard_capacity', 'base_capacity', 'standard_pax', 'pax', 'adults']
    objects_to_check = [r_item]

    for nested in ['room', 'room_type', 'details', 'roomType', 'info']:
        if isinstance(r_item.get(nested), dict):
            objects_to_check.append(r_item[nested])

    found_cap = None
    for obj in objects_to_check:
        for k in candidate_keys:
            val = obj.get(k)
            if val is not None and str(val).isdigit():
                v_int = int(val)
                if v_int > 0:
                    found_cap = v_int
                    break
        if found_cap is not None:
            break

    title = (room_title or "").strip()
    inferred_cap = None

    for word, num in PERSIAN_CAPACITY_WORDS.items():
        if f"{word} تخته" in title or f"{word}تخته" in title or f"{word} نفره" in title or f"{word}نفره" in title:
            inferred_cap = num
            break

    if not inferred_cap:
        m = re.search(r'([0-9۰-۹]+)\s*(?:تخته|نفره)', title)
        if m:
            raw_num = m.group(1)
            fa_to_en = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            inferred_cap = int(raw_num.translate(fa_to_en))

    if inferred_cap:
        if found_cap is None or found_cap < inferred_cap:
            return inferred_cap

    return found_cap or inferred_cap or 2


def extract_extra_capacity(r_item, room_title="", has_extra_bed_price=False):
    """استخراج هوشمند ظرفیت نفر اضافه"""
    candidate_keys = ['extra_capacity', 'extra_bed_capacity', 'extra_beds', 'extra_pax', 'extra_guest_capacity', 'extra_guests']
    objects_to_check = [r_item]

    for nested in ['room', 'room_type', 'details', 'roomType', 'info']:
        if isinstance(r_item.get(nested), dict):
            objects_to_check.append(r_item[nested])

    for obj in objects_to_check:
        for k in candidate_keys:
            val = obj.get(k)
            if val is not None and str(val).isdigit():
                v_int = int(val)
                if v_int > 0:
                    return v_int

    title = (room_title or "").strip()
    if "تخت اضافه" in title or "نفر اضافه" in title:
        m = re.search(r'([0-9۰-۹]+)\s*(?:تخت|نفر)\s*اضافه', title)
        if m:
            raw_num = m.group(1)
            fa_to_en = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
            return int(raw_num.translate(fa_to_en))
        return 1

    if has_extra_bed_price:
        return 1

    return 0


def extract_room_description(r_item):
    """استخراج متن توضیحات اتاق"""
    if isinstance(r_item.get('room'), dict):
        r_item = r_item['room']
    for key in ['description', 'desc', 'details', 'room_description', 'about', 'view']:
        val = r_item.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ''


def extract_stars_comprehensive(h):
    """استخراج ستاره‌های هتل"""
    if not isinstance(h, dict):
        return '-'

    star_keys = [
        'stars', 'star', 'stars_count', 'star_count', 'starsCount', 'starCount',
        'star_rating', 'starRating', 'hotel_stars', 'hotelStars', 'hotel_star', 'hotelStar',
        'rating', 'rate', 'grade', 'rank', 'stars_num', 'stars_number', 'category'
    ]
    for key in star_keys:
        val = h.get(key)
        if val is not None and str(val).strip() not in ['', 'None', 'null', '-']:
            if isinstance(val, dict):
                for sub_k in ['count', 'stars', 'value', 'id', 'name']:
                    if val.get(sub_k) is not None:
                        return str(val[sub_k]).strip()
            return str(val).strip()

    for parent_key in ['details', 'attributes', 'meta', 'info', 'hotel', 'hotel_details']:
        if isinstance(h.get(parent_key), dict):
            sub_res = extract_stars_comprehensive(h[parent_key])
            if sub_res != '-':
                return sub_res

    name = h.get('name') or h.get('title') or ''
    for s_num, s_words in [
        ('5', ['۵ ستاره', '5 ستاره', 'پنج ستاره', '5-star', '5 star']),
        ('4', ['۴ ستاره', '4 ستاره', 'چهار ستاره', '4-star', '4 star']),
        ('3', ['۳ ستاره', '3 ستاره', 'سه ستاره', '3-star', '3 star']),
        ('2', ['۲ ستاره', '2 ستاره', 'دو ستاره', '2-star', '2 star']),
        ('1', ['۱ ستاره', '1 ستاره', 'یک ستاره', '1-star', '1 star']),
    ]:
        if any(w in name for w in s_words):
            return s_num

    return '-'


def extract_hotel_rules_and_cancellation(h_data):
    """استخراج قوانین هتل و قوانین کنسلی"""
    rules_text = ""
    cancellation_text = ""

    if isinstance(h_data, dict):
        for r_k in ['rules', 'hotel_rules', 'regulations', 'law', 'hotel_policy']:
            val = h_data.get(r_k)
            if val and isinstance(val, str) and val.strip():
                rules_text = val.strip()
                break

        for c_k in ['cancellation_rules', 'cancellation_policy', 'cancel_rules', 'cancellation', 'important_note', 'cancellation_terms']:
            val = h_data.get(c_k)
            if val and isinstance(val, str) and val.strip():
                cancellation_text = val.strip()
                break

    return rules_text, cancellation_text


def is_room_online_instant(r_item):
    """تشخیص رزرو آنی بدون نیاز به تایید طبق پاسخ اسنپ"""
    if r_item.get('is_online') is True or r_item.get('online') is True:
        return True
    if r_item.get('is_instant') is True or r_item.get('instant') is True:
        return True
    
    booking_type = str(r_item.get('booking_type', '')).lower()
    if booking_type in ['online', 'instant', 'guaranteed']:
        return True
    if booking_type in ['offline', 'on_request', 'inquiry']:
        return False

    if r_item.get('is_online') is False or r_item.get('online') is False:
        return False
    if r_item.get('need_approval') is True or r_item.get('requires_confirmation') is True:
        return False

    return True


def calculate_customer_club_points(stars_val, price_val):
    """محاسبه امتیاز باشگاه مشتریان"""
    try:
        stars = int(stars_val) if str(stars_val).isdigit() else 3
    except Exception:
        stars = 3
    stars = max(1, min(stars, 5))

    price = int(price_val or 1500000)
    price_score = (price // 500000) * 4
    star_score = random.randint(stars * 12, stars * 22)
    return max(15, round((star_score + price_score) / 5) * 5)


# ==============================================================================
# بخش ۱: توابع رزرواسیون و استعلام زنده لحظه‌ای
# ==============================================================================

def get_snapptrip_booking_status(snapp_reservation_code: str):
    """استعلام وضعیت رزرو از اسنپ"""
    base_url, headers = get_snapptrip_client_config()
    url = f"{base_url}/booking/{snapp_reservation_code}"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            return (
                data.get('state') or 
                data.get('status') or 
                data.get('data', {}).get('state') or 
                data.get('data', {}).get('status') or 
                'confirmed'
            ), res.text
        return "unknown", f"کد {res.status_code}: {res.text[:120]}"
    except Exception as e:
        logger.error(f"Error fetching booking status from Snapp ({snapp_reservation_code}): {e}")
        return "unknown", str(e)


def check_room_realtime_availability(hotel_snapp_id: int, room_snapp_id: int, checkin_str: str, checkout_str: str):
    """
    استعلام زنده موجودی در صدم‌ثانیه قبل از پرداخت:
    جلوی اوربوکینگ در رزروهای زیر ۲ ساعت و رزروهای فوری را کاملاً می‌گیرد.
    """
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, False, {}, "کلید API اسنپ‌تریپ در سیستم تنظیم نشده است."

    url = f"{base_url}/availability/hotels/{hotel_snapp_id}?checkin={checkin_str}&checkout={checkout_str}"
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            return False, False, {}, f"خطا در استعلام ظرفیت از اسنپ (کد {res.status_code})"

        data = res.json()
        rooms = extract_list_from_response(data)

        for r in rooms:
            rid = extract_room_id(r)
            if rid == room_snapp_id:
                is_instant = is_room_online_instant(r)
                pricing = r.get('pricing', {})
                return True, is_instant, pricing, ""

        return False, False, {}, "این اتاق در بازه تاریخی انتخابی، تکمیل ظرفیت شده است."
    except Exception as e:
        logger.error(f"Error checking real-time availability: {e}")
        return False, False, {}, f"خطای ارتباط با سرور اسنپ: {str(e)}"


def create_snapptrip_booking(reservation: Reservationhotel, room_snapp_id: int, hotel_snapp_id: int, quantity: int = 1):
    """ثبت پیش‌رزرو در اسنپ‌تریپ (POST /booking/create)"""
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, None, False, "کلید API اسنپ‌تریپ تنظیم نشده است."

    check_in_g = reservation.check_in_date.togregorian() if hasattr(reservation.check_in_date, 'togregorian') else reservation.check_in_date
    check_out_g = reservation.check_out_date.togregorian() if hasattr(reservation.check_out_date, 'togregorian') else reservation.check_out_date

    checkin_str = check_in_g.strftime('%Y-%m-%d')
    checkout_str = check_out_g.strftime('%Y-%m-%d')

    buyer = getattr(reservation, 'buyer', None)
    user_phone = (buyer.phone_number if buyer and getattr(buyer, 'phone_number', None) else "09127752353").strip()

    profile = getattr(buyer, 'natural_profile', None) if buyer else None
    default_fn = (getattr(profile, 'first_name', '') if profile else '') or reservation.reserver_first_name or "مسافر"
    default_ln = (getattr(profile, 'last_name', '') if profile else '') or reservation.reserver_last_name or "اصلی"
    default_nc = (getattr(profile, 'national_code', '') if profile else '') or reservation.reserver_national_code or "0012345679"

    guests_payload = []
    first_room = reservation.reservation_rooms.first()
    if first_room and first_room.passengers.exists():
        for p in first_room.passengers.all():
            p_phone = (p.mobile_number or user_phone).strip()
            guests_payload.append({
                "first_name": p.first_name or default_fn,
                "last_name": p.last_name or default_ln,
                "national_code": p.national_code or default_nc,
                "phone": p_phone,
                "phone_number": p_phone,
                "mobile": p_phone,
                "foreigner": False,
                "gender": "male"
            })
    else:
        guests_payload.append({
            "first_name": default_fn,
            "last_name": default_ln,
            "national_code": default_nc,
            "phone": user_phone,
            "phone_number": user_phone,
            "mobile": user_phone,
            "foreigner": False,
            "gender": "male"
        })

    rooms_payload = []
    for _ in range(quantity):
        rooms_payload.append({
            "room_id": int(room_snapp_id),
            "passengers": guests_payload,
            "guests": guests_payload
        })

    create_url = f"{base_url}/booking/create"
    payload = {
        "hotel_id": int(hotel_snapp_id),
        "checkin": checkin_str,
        "checkout": checkout_str,
        "phone": user_phone,
        "phone_number": user_phone,
        "mobile": user_phone,
        "rooms": rooms_payload,
        "passengers": guests_payload,
        "guests": guests_payload,
        "note": reservation.additional_notes or ""
    }

    try:
        res = requests.post(create_url, json=payload, headers=headers, timeout=20)
        
        if res.status_code not in [200, 201]:
            alt_rooms = []
            for _ in range(quantity):
                alt_rooms.append({
                    "room_id": int(room_snapp_id),
                    "count": 1,
                    "passengers": guests_payload
                })
            payload["rooms"] = alt_rooms
            res = requests.post(create_url, json=payload, headers=headers, timeout=20)

        if res.status_code not in [200, 201]:
            logger.error(f"Snapp create booking failed: {res.status_code} - {res.text}")
            return False, None, False, f"خطای ثبت در اسنپ: {res.text[:220]}"

        res_data = res.json()
        snapp_code = (
            res_data.get('reservation_code') or 
            res_data.get('code') or 
            res_data.get('data', {}).get('reservation_code') or
            res_data.get('data', {}).get('code')
        )

        if not snapp_code:
            return False, None, False, f"کد پیگیری از اسنپ دریافت نشد: {res.text[:180]}"

        state_val = res_data.get('state') or res_data.get('status') or 'draft'
        is_instant = state_val not in ['availability_checking', 'availability_pending', 'offline']

        return True, str(snapp_code), is_instant, state_val

    except Exception as e:
        logger.error(f"Error creating booking in Snapp: {e}")
        return False, None, False, f"خطای ارتباط با سرور اسنپ: {str(e)}"


def confirm_snapptrip_booking(snapp_reservation_code: str):
    """تأیید نهایی رزرو پس از پرداخت مسافر (POST /booking/{code}/confirm)"""
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, "failed", "کلید API اسنپ‌تریپ تنظیم نشده است."

    code_str = str(snapp_reservation_code).strip()
    confirm_url = f"{base_url}/booking/{code_str}/confirm"
    try:
        res = requests.post(confirm_url, json={}, headers=headers, timeout=20)
        
        if res.status_code not in [200, 201]:
            err_msg = res.text[:120]
            logger.error(f"Confirm failed on Snapp ({code_str}): {res.status_code} - {res.text}")
            return False, "failed", f"خطای تأیید در اسنپ: {err_msg}"

        final_status, _ = get_snapptrip_booking_status(code_str)
        real_status = "confirmed" if final_status in ['confirmed', 'unknown', ''] else final_status
        return True, real_status[:30], "رزرو با موفقیت در اسنپ قطعی شد."
    except Exception as e:
        logger.error(f"Error confirming booking {code_str}: {e}")
        return False, "failed", f"خطای ارتباط با اسنپ: {str(e)[:50]}"


def auto_confirm_snapp_reservation_if_charged(reservation):
    """بررسی خودکار کیف پول اسنپ بعد از پرداخت مسافر و نهایی کردن رزرو"""
    if not reservation.is_snapptrip_reservation or not reservation.snapp_reservation_code:
        return False, "رزرو اسنپی نیست."

    snapp_balance, b_msg = get_snapptrip_wallet_balance()
    required_price = int(reservation.final_price or reservation.total_price or 0)

    logger.info(f"🔍 بررسی کیف‌پول: موجودی={snapp_balance:,} | نیاز={required_price:,} | رزرو={reservation.tracking_code}")

    if snapp_balance < required_price:
        logger.warning(f"⚠️ کیف پول اسنپ شارژ ندارد ({snapp_balance:,} تومان). وضعیت: insufficient_credit")
        reservation.snapp_status = 'insufficient_credit'
        reservation.save(update_fields=['snapp_status'])
        return False, f"کیف‌پول اسنپ شارژ ندارد (موجودی: {snapp_balance:,} تومان)"

    success, final_stat, msg = confirm_snapptrip_booking(reservation.snapp_reservation_code)
    
    if success:
        reservation.snapp_status = str(final_stat)[:30]
        logger.info(f"✅ رزرو {reservation.snapp_reservation_code} در اسنپ قطعی شد.")
    else:
        if "insufficient credit" in msg.lower():
            reservation.snapp_status = 'insufficient_credit'
        else:
            reservation.snapp_status = 'failed'

    reservation.save(update_fields=['snapp_status'])
    return success, msg


# ==============================================================================
# بخش ۲: همگام‌سازی اتاق‌ها با نمایش تضمینی اتاق‌های تکمیل‌ظرفیت (Sold Out)
# ==============================================================================

def sync_hotel_and_rooms_from_snapp(hotel_id: int):
    """
    همگام‌سازی هتل و اتاق‌ها از اسنپ‌تریپ:
    - همه اتاق‌ها (خالی و تکمیل ظرفیت) در سیستم حفظ می‌شوند.
    - اتاق‌های تکمیل ظرفیت با موجودی ۰ ثبت می‌شوند تا در سایت دیده شوند ولی رزرو نشوند.
    """
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات وارد نشده است!"

    try:
        hotel = Hotel.objects.get(pk=hotel_id)
    except Hotel.DoesNotExist:
        return False, "هتل پیدا نشد."

    if not hotel.snapptrip_hotel_id:
        return False, "شناسه اسنپ‌تریپ برای این هتل وارد نشده است."

    snapp_h_id = hotel.snapptrip_hotel_id
    now = datetime.now()
    checkin_str = now.strftime('%Y-%m-%d')
    checkout_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    calendar_from_str = now.strftime('%Y-%m-%d')
    calendar_to_str = (now + timedelta(days=30)).strftime('%Y-%m-%d')

    all_rooms_dict = {}
    available_room_ids = set()

    # ۱. استخراج اطلاعات کامل هتل و اتاق‌های استاتیک
    static_room_urls = [
        f"{base_url}/hotels/{snapp_h_id}/",
        f"{base_url}/hotels/{snapp_h_id}",
        f"{base_url}/hotels/rooms/?hotel_id={snapp_h_id}",
        f"{base_url}/hotels/{snapp_h_id}/rooms/",
        f"{base_url}/hotels/rooms/{snapp_h_id}/",
    ]

    for h_url in static_room_urls:
        try:
            hotel_res = requests.get(h_url, headers=headers, timeout=15)
            if hotel_res.status_code != 200:
                continue

            h_data = hotel_res.json()
            if isinstance(h_data, dict) and 'data' in h_data and isinstance(h_data['data'], dict):
                h_data = h_data['data']

            if isinstance(h_data, dict):
                h_rules, h_cancellation = extract_hotel_rules_and_cancellation(h_data)
                if h_rules:
                    hotel.rules = h_rules
                if h_cancellation:
                    hotel.important_notes = h_cancellation

                hotel.is_snapptrip = True
                hotel.status = 'published'

                if not hotel.city:
                    dir_entry = SnappHotelDirectory.objects.filter(snapp_hotel_id=snapp_h_id).first()
                    city_search_name = ""
                    if dir_entry and dir_entry.city_name:
                        city_search_name = dir_entry.city_name.split(' - ')[-1].strip()

                    if city_search_name:
                        matched_city = City.objects.filter(
                            Q(name__iexact=city_search_name) |
                            Q(slug__iexact=city_search_name) |
                            Q(name__icontains=city_search_name)
                        ).first()
                        if matched_city:
                            hotel.city = matched_city

                hotel.save(update_fields=['rules', 'important_notes', 'is_snapptrip', 'status', 'city'])
                CancellationPenalty.objects.get_or_create(hotel=hotel, defaults={'penalty_percentage': 0})

            extracted = []
            if isinstance(h_data, list):
                extracted = h_data
            elif isinstance(h_data, dict):
                for r_key in ['rooms', 'room', 'room_types', 'accommodations', 'results', 'data']:
                    val = h_data.get(r_key)
                    if isinstance(val, list) and len(val) > 0:
                        extracted = val
                        break
                if not extracted:
                    extracted = extract_list_from_response(h_data)

            if extracted:
                for item in extracted:
                    rid = extract_room_id(item)
                    if rid:
                        all_rooms_dict[rid] = item
                if all_rooms_dict:
                    break
        except Exception as e:
            logger.error(f"Error fetching static rooms from {h_url}: {e}")

    # ۲. استعلام ظرفیت و قیمت‌های زنده (Availability)
    avail_urls = [
        f"{base_url}/availability/hotels/{snapp_h_id}?checkin={checkin_str}&checkout={checkout_str}",
        f"{base_url}/availability/hotels/{snapp_h_id}/?checkin={checkin_str}&checkout={checkout_str}",
    ]
    for a_url in avail_urls:
        try:
            avail_res = requests.get(a_url, headers=headers, timeout=15)
            if avail_res.status_code == 200:
                avail_items = extract_list_from_response(avail_res.json())
                for a_item in avail_items:
                    a_id = extract_room_id(a_item)
                    if not a_id:
                        continue

                    is_sold_out = False
                    if a_item.get('is_available') is False or a_item.get('available') is False:
                        is_sold_out = True
                    if a_item.get('sold_out') is True or str(a_item.get('status')).lower() in ['sold_out', 'full', 'unavailable']:
                        is_sold_out = True

                    if not is_sold_out:
                        available_room_ids.add(a_id)

                    if a_id in all_rooms_dict:
                        all_rooms_dict[a_id].update(a_item)
                    else:
                        all_rooms_dict[a_id] = a_item
                break
        except Exception as e:
            logger.error(f"Error fetching real-time availability: {e}")

    # ۳. فال‌بک تقویم اگر اتاقی یافت نشد
    if not all_rooms_dict:
        fallback_urls = [
            f"{base_url}/availability/hotels/{snapp_h_id}/calendar?from={calendar_from_str}&to={calendar_to_str}",
            f"{base_url}/hotels/rooms/{snapp_h_id}/",
        ]
        for f_url in fallback_urls:
            try:
                f_res = requests.get(f_url, headers=headers, timeout=15)
                if f_res.status_code == 200:
                    f_items = extract_list_from_response(f_res.json())
                    for item in f_items:
                        r_id = extract_room_id(item)
                        if r_id:
                            all_rooms_dict[r_id] = item
                            available_room_ids.add(r_id)
                    if all_rooms_dict:
                        break
            except Exception:
                continue

    if not all_rooms_dict:
        return False, f"هیچ اتاقی از اسنپ برای هتل {hotel.name} دریافت نشد."

    synced_snapp_room_ids = []
    synced_rooms_count = 0
    synced_prices_count = 0

    today_j = jdatetime.date.fromgregorian(date=now.date())
    end_30_days_j = jdatetime.date.fromgregorian(date=(now + timedelta(days=30)).date())

    # ۴. ساخت یا به‌روزرسانی تک‌تک اتاق‌ها
    for snapp_room_id, r_item in all_rooms_dict.items():
        synced_snapp_room_ids.append(snapp_room_id)
        room_title = extract_room_title(r_item, snapp_room_id)
        room_desc = extract_room_description(r_item)

        pricing = r_item.get('pricing') if isinstance(r_item.get('pricing'), dict) else {}
        base_client_sell_price = 0
        base_agency_buy_price = 0
        base_extra_bed_price = 0

        if pricing:
            p_price = int(Decimal(str(pricing.get('price') or 0)))
            p_orig = int(Decimal(str(pricing.get('original_sell_price') or 0)))
            base_client_sell_price = p_orig if p_orig > 0 else p_price
            base_agency_buy_price = p_price if p_price > 0 else base_client_sell_price
            base_extra_bed_price = int(Decimal(str(
                pricing.get('extra_bed_price') or pricing.get('extra_passenger_price') or 0
            )))

        has_capacity = (snapp_room_id in available_room_ids)
        if r_item.get('is_available') is False or r_item.get('available') is False or r_item.get('sold_out') is True:
            has_capacity = False

        room_cap = extract_room_capacity(r_item, room_title)
        extra_cap = extract_extra_capacity(r_item, room_title, has_extra_bed_price=(base_extra_bed_price > 0))
        board_type = r_item.get('board_type', 'bed_breakfast')

        room_rules = (
            r_item.get('rules') or 
            r_item.get('policy') or 
            r_item.get('cancellation_rules') or 
            r_item.get('cancellation_policy') or 
            ''
        )

        is_online = True
        if 'is_online' in r_item:
            is_online = bool(r_item['is_online'])
        elif 'online' in r_item:
            is_online = bool(r_item['online'])
        elif r_item.get('booking_type') == 'offline':
            is_online = False

        # تعیین موجودی صفر برای اتاق‌های پر شده (جهت نمایش تکمیل‌ظرفیت در سایت)
        if not has_capacity:
            inv_count = 0
            count_val = 0
            auto_approved_val = 0
        else:
            inv_count = 100
            count_val = 0 if is_online else inv_count
            auto_approved_val = inv_count if is_online else 0

        room, created = Room.objects.update_or_create(
            hotel=hotel,
            snapptrip_room_id=snapp_room_id,
            defaults={
                'title': room_title,
                'description': room_desc,
                'rules': room_rules,
                'room_capacity': room_cap,
                'extra_capacity': extra_cap,
                'board_type': board_type,
                'inventory': inv_count,
                'count': count_val,
                'auto_approved_count': auto_approved_val,
                'is_snapptrip': True,
            }
        )
        synced_rooms_count += 1

        service_title = BOARD_TYPE_TITLES.get(board_type, 'همراه با صبحانه رایگان')
        board_service, _ = RoomService.objects.get_or_create(title=service_title)
        room.services.add(board_service)

        # حفظ قیمت پیشین دیتابیس اگر اتاق پر شده و قیمت لحظه‌ای خالی برگشته
        if base_client_sell_price <= 0 and not created:
            last_date_price = RoomDatePrice.objects.filter(room=room).order_by('-id').first()
            if last_date_price:
                base_client_sell_price = last_date_price.price
                base_agency_buy_price = last_date_price.purchase_price
                base_extra_bed_price = last_date_price.extra_passenger_price

        # استعلام تقویم روزانه نرخ‌ها
        cal_candidate_urls = [
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar?from={calendar_from_str}&to={calendar_to_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar/?from={calendar_from_str}&to={calendar_to_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar",
        ]

        room_calendar_synced = False
        first_valid_client_price = base_client_sell_price
        first_valid_agency_price = base_agency_buy_price
        first_valid_extra = base_extra_bed_price

        for cal_url in cal_candidate_urls:
            try:
                cal_res = requests.get(cal_url, headers=headers, timeout=15)
                if cal_res.status_code == 200:
                    calendar_items = extract_list_from_response(cal_res.json())

                    for day_data in calendar_items:
                        if not isinstance(day_data, dict):
                            continue

                        g_date_str = day_data.get('date') or day_data.get('day')
                        if not g_date_str:
                            continue
                        g_date_str = str(g_date_str)[:10]

                        try:
                            g_dt = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                            j_dt = jdatetime.date.fromgregorian(date=g_dt)
                        except Exception:
                            continue

                        raw_price = 0
                        for pk in ['price', 'current_price', 'sell_price', 'amount']:
                            if day_data.get(pk):
                                try:
                                    raw_price = int(Decimal(str(day_data[pk])))
                                    if raw_price > 0:
                                        break
                                except Exception:
                                    pass

                        raw_original = 0
                        for opk in ['original_sell_price', 'original_price', 'base_price', 'board_price']:
                            if day_data.get(opk):
                                try:
                                    p = int(Decimal(str(day_data[opk])))
                                    if p > 0:
                                        raw_original = p
                                        break
                                except Exception:
                                    pass

                        snapp_extra = 0
                        for epk in ['extra_bed_price', 'extra_passenger_price', 'extra_price', 'extra_bed']:
                            if day_data.get(epk):
                                try:
                                    snapp_extra = int(Decimal(str(day_data[epk])))
                                    break
                                except Exception:
                                    pass
                        if snapp_extra == 0:
                            snapp_extra = base_extra_bed_price

                        if raw_price <= 0 and base_agency_buy_price <= 0:
                            continue

                        if raw_original > 0:
                            day_client_sell_price = raw_original
                            day_agency_buy_price = raw_price
                        elif base_client_sell_price > 0 and base_agency_buy_price > 0:
                            ratio = Decimal(base_client_sell_price) / Decimal(base_agency_buy_price)
                            day_agency_buy_price = raw_price if raw_price > 0 else base_agency_buy_price
                            day_client_sell_price = int(Decimal(day_agency_buy_price) * ratio)
                        else:
                            day_client_sell_price = raw_price
                            day_agency_buy_price = raw_price

                        if not first_valid_client_price:
                            first_valid_client_price = day_client_sell_price
                            first_valid_agency_price = day_agency_buy_price
                            first_valid_extra = snapp_extra

                        RoomDatePrice.objects.update_or_create(
                            room=room,
                            start_date=j_dt,
                            end_date=j_dt,
                            user_level=None,
                            defaults={
                                'purchase_price': day_agency_buy_price,
                                'price': day_client_sell_price,
                                'extra_passenger_price': snapp_extra,
                                'discount_type': 'none',
                                'discount_value': 0,
                                'discount_date': None,
                                'is_fixed_discount_one_time': False,
                            }
                        )
                        synced_prices_count += 1
                        room_calendar_synced = True

                    if room_calendar_synced:
                        break
            except Exception as e:
                logger.error(f"Error fetching calendar for room {snapp_room_id}: {e}")

        if room_calendar_synced:
            RoomDatePrice.objects.filter(
                room=room,
                start_date=today_j,
                end_date=end_30_days_j
            ).delete()
        else:
            final_base_price = first_valid_client_price or base_client_sell_price
            final_agency_price = first_valid_agency_price or base_agency_buy_price
            final_extra = first_valid_extra or base_extra_bed_price

            if final_base_price > 0:
                RoomDatePrice.objects.update_or_create(
                    room=room,
                    start_date=today_j,
                    end_date=end_30_days_j,
                    user_level=None,
                    defaults={
                        'purchase_price': final_agency_price,
                        'price': final_base_price,
                        'extra_passenger_price': final_extra,
                        'discount_type': 'none',
                        'discount_value': 0,
                        'discount_date': None,
                        'is_fixed_discount_one_time': False,
                    }
                )
                synced_prices_count += 1

        club_points = calculate_customer_club_points(
            hotel.stars,
            first_valid_client_price or base_client_sell_price
        )
        room.customer_club_points = club_points
        room.save(update_fields=['customer_club_points'])

    # ۵. صفر کردن موجودی برای اتاق‌های غایب در استعلام جدید (به جای حذف فیزیکی دیتابیس)
    if synced_snapp_room_ids:
        missing_count = Room.objects.filter(
            hotel=hotel,
            is_snapptrip=True
        ).exclude(
            snapptrip_room_id__in=synced_snapp_room_ids
        ).update(
            inventory=0,
            count=0,
            auto_approved_count=0
        )
        if missing_count > 0:
            logger.info(f"{missing_count} اتاق خارج از دسترس به وضعیت تکمیل‌ظرفیت تغییر یافتند.")

    if synced_rooms_count == 0:
        return False, f"تعداد {len(all_rooms_dict)} آیتم اتاق از اسنپ دریافت شد اما شناسه‌های آن‌ها خوانده نشد!"

    return True, f"هماهنگ‌سازی هتل {hotel.name} انجام شد: {synced_rooms_count} اتاق ثبت و بروز شدند."


# ==============================================================================
# بخش ۳: موتور خودکار زمان‌بندی هوشمند (پیک و آخر هفته‌ها ۱۰ دقیقه / خلوت ۲ ساعت)
# ==============================================================================

def sync_all_hotels_from_snapp():
    """همگام‌سازی دسته‌جمعی تمامی هتل‌های فعال اسنپ‌تریپ"""
    hotels = Hotel.objects.filter(is_snapptrip=True, snapptrip_hotel_id__isnull=False)
    total = hotels.count()
    logger.info(f"شروع همگام‌سازی {total} هتل اسنپ‌تریپ...")

    for hotel in hotels:
        try:
            ok, msg = sync_hotel_and_rooms_from_snapp(hotel.id)
            if ok:
                logger.info(f"✓ {hotel.name}: {msg}")
            else:
                logger.warning(f"✗ {hotel.name}: {msg}")
        except Exception as e:
            logger.error(f"خطا در همگام‌سازی {hotel.name}: {e}")

        # توقف ۲ ثانیه‌ای بین هر هتل برای رعایت سقف درخواست (Rate Limit)
        time.sleep(2)

    return True


_auto_sync_thread_started = False

def _auto_sync_loop():
    """
    حلقه زمان‌بندی هوشمند و پویا:
    - آخر هفته‌های ایران (چهارشنبه، پنج‌شنبه، جمعه) و ساعات پیک روز (۱۰ صبح تا ۲۳ شب): بازه ۱۰ دقیقه.
    - ساعات خلوت شب و روزهای عادی: بازه ۲ ساعت (برای جلوگیری از خطای ۴۲۹ اسنپ).
    """
    logger.info("موتور زمان‌بندی هوشمند اسنپ در پس‌زمینه فعال شد.")
    while True:
        try:
            sync_all_hotels_from_snapp()
        except Exception as e:
            logger.error(f"خطا در لوپ خودکار اسنپ: {e}")

        now = datetime.now()
        weekday = now.weekday()  # دوشنبه=0 ... چهارشنبه=2، پنجشنبه=3، جمعه=4
        hour = now.hour

        # آخر هفته ایران (چهارشنبه، پنج‌شنبه، جمعه) یا ساعات شلوغ روز (۱۰ صبح تا ۲۳ شب)
        is_iran_weekend = weekday in [2, 3, 4]
        is_peak_hours = (10 <= hour <= 23)

        if is_iran_weekend or is_peak_hours:
            sleep_seconds = 10 * 60  # ۱۰ دقیقه
            logger.info("حالت پیک / آخر هفته فعال است: آپدیت بعدی ۱۰ دقیقه دیگر.")
        else:
            sleep_seconds = 2 * 3600  # ۲ ساعت
            logger.info("حالت کم‌ترافیک / شب فعال است: آپدیت بعدی ۲ ساعت دیگر.")

        time.sleep(sleep_seconds)


def start_snapp_auto_sync_thread():
    """روشن کردن ترد آپدیت خودکار هوشمند در پس‌زمینه"""
    global _auto_sync_thread_started
    if _auto_sync_thread_started:
        return

    _auto_sync_thread_started = True
    thread = threading.Thread(
        target=_auto_sync_loop,
        daemon=True,
        name="SnappTripAutoSyncThread"
    )
    thread.start()
    logger.info("ترد آپدیت خودکار اسنپ با موفقیت استارت خورد.")


def sync_all_snapptrip_hotels_directory():
    """همگام‌سازی بانک مرجع هتل‌های اسنپ‌تریپ"""
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات وارد نشده است!"

    cities_res = fetch_with_rate_limit(f"{base_url}/cities/", headers)
    if not cities_res:
        return False, "ارتباط با سرور اسنپ برقرار نشد."
    
    if cities_res.status_code == 429:
        return False, "محدودیت درخواست (Rate Limit). لطفاً کمی بعد تلاش کنید."

    if cities_res.status_code != 200:
        return False, f"خطا در دریافت لیست شهرها: کد {cities_res.status_code}"

    cities_list = extract_list_from_response(cities_res.json())
    if not cities_list:
        return False, "هیچ شهری دریافت نشد!"

    all_hotel_objects = []

    for city in cities_list:
        city_id = str(city.get('id') or city.get('city_id') or city.get('code') or '').strip()
        if not city_id:
            continue

        raw_city_name = ""
        for k in ['title_fa', 'name_fa', 'persian_name', 'title', 'name', 'city_name', 'city', 'slug']:
            val = city.get(k)
            if val and isinstance(val, str) and not val.strip().isdigit():
                raw_city_name = val.strip()
                break

        pure_name = IRAN_CITIES_MAP.get(city_id) or IRAN_CITIES_MAP.get(str(raw_city_name).lower()) or raw_city_name
        formatted_city = f"{city_id} - {pure_name}" if pure_name and pure_name != city_id else f"{city_id}"

        offset = 0
        limit = 100

        for _ in range(15):
            url = f"{base_url}/cities/{city_id}/hotels?limit={limit}&offset={offset}"
            res = fetch_with_rate_limit(url, headers)

            if not res or res.status_code != 200:
                url_alt = f"{base_url}/cities/{city_id}/hotels"
                res = fetch_with_rate_limit(url_alt, headers)

            if res and res.status_code == 200:
                batch = extract_list_from_response(res.json())
                if not batch:
                    break

                for h in batch:
                    if not isinstance(h, dict):
                        continue
                    h_id = h.get('id') or h.get('hotel_id') or h.get('code')
                    if not h_id:
                        continue
                    h_name = h.get('name_fa') or h.get('title_fa') or h.get('name') or h.get('title') or f"هتل {h_id}"
                    stars = extract_stars_comprehensive(h)

                    all_hotel_objects.append(SnappHotelDirectory(
                        snapp_hotel_id=h_id,
                        name=str(h_name).strip(),
                        city_name=formatted_city,
                        city_id=city_id,
                        stars=stars
                    ))

                if len(batch) < limit:
                    break
                offset += limit
            else:
                break

            time.sleep(0.3)

        time.sleep(0.3)

    if not all_hotel_objects:
        return False, "هیچ هتلی استخراج نشد."

    unique_hotels = {}
    for h_obj in all_hotel_objects:
        unique_hotels[h_obj.snapp_hotel_id] = h_obj

    hotels_to_save = list(unique_hotels.values())

    SnappHotelDirectory.objects.bulk_create(
        hotels_to_save,
        update_conflicts=True,
        update_fields=['name', 'city_name', 'city_id', 'stars', 'last_synced'],
        unique_fields=['snapp_hotel_id']
    )

    return True, f"بروزرسانی کامل شد: {len(hotels_to_save)} هتل ذخیره شدند."
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# ایجاد یک سشن سراسری برای استفاده از قابلیت Keep-Alive و افزایش سرعت درخواست‌ها
_snapp_session = requests.Session()

IRAN_CITIES_MAP = {
    '1': 'تهران', 'tehran': 'تهران',
    '2': 'مشهد', 'mashhad': 'مشهد',
    '3': 'اصفهان', 'isfahan': 'اصفهان',
    '4': 'شیراز', 'shiraz': 'شیراز',
    '5': 'تبریز', 'tabriz': 'تبریز',
    '6': 'کیش', 'kish': 'کیش',
    '7': 'قشم', 'qeshm': 'قشم',
    '8': 'یزد', 'yazd': 'یزد',
    '9': 'رشت', 'rasht': 'رشت',
    '10': 'ساری', 'sari': 'ساری',
    '11': 'رامسر', 'ramsar': 'رامسر',
    '12': 'کرمان', 'kerman': 'کرمان',
    '13': 'اهواز', 'ahvaz': 'اهواز',
    '14': 'بندرعباس', 'bandarabbas': 'بندرعباس',
    '15': 'کرمانشاه', 'kermanshah': 'کرمانشاه',
    '16': 'همدان', 'hamedan': 'همدان',
    '17': 'قم', 'qom': 'قم',
    '18': 'اراک', 'arak': 'اراک',
    '19': 'زنجان', 'zanjan': 'زنجان',
    '20': 'سنندج', 'sanandaj': 'سنندج',
    '21': 'ارومیه', 'urmia': 'ارومیه',
    '22': 'اردبیل', 'ardabil': 'اردبیل',
    '23': 'کاشان', 'kashan': 'کاشان',
    '24': 'گرگان', 'gorgan': 'گرگان',
    '25': 'چابهار', 'chabahar': 'چابهار',
    '26': 'بوشهر', 'bushehr': 'بوشهر',
    '27': 'چالوس', 'chalus': 'چالوس',
    '28': 'نوشهر', 'noshahr': 'نوشهر',
    '29': 'لاهیجان', 'lahijan': 'لاهیجان',
    '30': 'انزلی', 'anzali': 'بندر انزلی',
}

BOARD_TYPE_TITLES = {
    'room_only': 'اقامت بدون صبحانه',
    'bed_breakfast': 'صبحانه بوفه رایگان',
    'half_board': 'هافبرد (صبحانه + یک وعده غذا)',
    'full_board': 'فولبرد (صبحانه + ناهار + شام)',
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
        res = _snapp_session.get(f"{base_url}/balance/", headers=headers, timeout=10)
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
            res = _snapp_session.get(url, headers=headers, timeout=12)
            if res.status_code == 429:
                logger.warning("محدودیت Rate Limit اسنپ (429). ۵ ثانیه توقف...")
                time.sleep(5)
                continue
            return res
        except Exception:
            time.sleep(1)
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
    """استخراج عنوان اتاق"""
    if isinstance(r_item.get('room'), dict):
        r_item = r_item['room']
    for key in ['title_fa', 'name_fa', 'name', 'title', 'room_name', 'room_title', 'room_type_name']:
        val = r_item.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return f"اتاق {default_id}"


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
# بخش ۱: توابع رزرواسیون و پیگیری وضعیت در اسنپ‌تریپ (بهینه‌شده برای سرعت بالا)
# ==============================================================================

def get_snapptrip_booking_status(snapp_reservation_code: str):
    """استعلام وضعیت رزرو از اسنپ (GET /booking/{code})"""
    base_url, headers = get_snapptrip_client_config()
    url = f"{base_url}/booking/{snapp_reservation_code}"
    try:
        res = _snapp_session.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return (
                data.get('status') or 
                data.get('data', {}).get('status') or 
                'confirmed'
            ), res.text
        return "unknown", f"کد {res.status_code}: {res.text[:120]}"
    except Exception as e:
        logger.error(f"Error fetching booking status from Snapp ({snapp_reservation_code}): {e}")
        return "unknown", str(e)


def check_room_realtime_availability(hotel_snapp_id: int, room_snapp_id: int, checkin_str: str, checkout_str: str):
    """استعلام زنده موجودی و وضعیت تایید اتاق از اسنپ (بهینه‌شده)"""
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, False, {}, "کلید API اسنپ‌تریپ در سیستم تنظیم نشده است."

    url = f"{base_url}/availability/hotels/{hotel_snapp_id}?checkin={checkin_str}&checkout={checkout_str}"
    try:
        res = _snapp_session.get(url, headers=headers, timeout=10)
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

        return False, False, {}, "این اتاق در بازه تاریخی انتخابی، ظرفیت خالی ندارد."
    except Exception as e:
        logger.error(f"Error checking real-time availability: {e}")
        return False, False, {}, f"خطای ارتباط با سرور اسنپ: {str(e)}"


def create_snapptrip_booking(reservation: Reservationhotel, room_snapp_id: int, hotel_snapp_id: int, quantity: int = 1):
    """
    ثبت پیش‌رزرو در اسنپ‌تریپ (POST /booking/create) - نسخه پرسرعت و بهینه‌سازی شده
    """
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, None, False, "کلید API اسنپ‌تریپ تنظیم نشده است."

    check_in_g = reservation.check_in_date.togregorian() if hasattr(reservation.check_in_date, 'togregorian') else reservation.check_in_date
    check_out_g = reservation.check_out_date.togregorian() if hasattr(reservation.check_out_date, 'togregorian') else reservation.check_out_date

    checkin_str = check_in_g.strftime('%Y-%m-%d')
    checkout_str = check_out_g.strftime('%Y-%m-%d')

    user_phone = "09127752353"

    # استعلام همزمان و سریع موجودی
    is_avail, is_instant, pricing, err = check_room_realtime_availability(
        hotel_snapp_id, room_snapp_id, checkin_str, checkout_str
    )
    if not is_avail:
        return False, None, False, err

    buyer = getattr(reservation, 'buyer', None)
    profile = getattr(buyer, 'natural_profile', None) if buyer else None
    default_fn = (getattr(profile, 'first_name', '') if profile else '') or reservation.reserver_first_name or "مسافر"
    default_ln = (getattr(profile, 'last_name', '') if profile else '') or reservation.reserver_last_name or "اصلی"
    default_nc = (getattr(profile, 'national_code', '') if profile else '') or reservation.reserver_national_code or ""

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

    rooms_payload = [{"room_id": int(room_snapp_id), "passengers": guests_payload, "guests": guests_payload} for _ in range(quantity)]

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
        # کاهش تایم‌اوت به ۱۵ ثانیه برای سرعت‌بخشی به پاسخ‌دهی به کاربر
        res = _snapp_session.post(create_url, json=payload, headers=headers, timeout=15)
        
        if res.status_code not in [200, 201]:
            alt_rooms = [{"room_id": int(room_snapp_id), "count": 1, "passengers": guests_payload} for _ in range(quantity)]
            payload["rooms"] = alt_rooms
            res = _snapp_session.post(create_url, json=payload, headers=headers, timeout=15)

        if res.status_code not in [200, 201]:
            logger.error(f"Snapp create booking failed: {res.status_code} - {res.text}")
            return False, None, is_instant, f"خطای ثبت در اسنپ: {res.text[:220]}"

        res_data = res.json()
        snapp_code = (
            res_data.get('reservation_code') or 
            res_data.get('code') or 
            res_data.get('data', {}).get('reservation_code') or
            res_data.get('data', {}).get('code')
        )

        if not snapp_code:
            return False, None, is_instant, f"کد پیگیری از اسنپ دریافت نشد: {res.text[:180]}"

        return True, str(snapp_code), is_instant, "پیش‌رزرو با موفقیت در اسنپ ثبت شد."

    except Exception as e:
        logger.error(f"Error creating booking in Snapp: {e}")
        return False, None, is_instant, f"خطای ارتباط با سرور اسنپ: {str(e)}"


def confirm_snapptrip_booking(snapp_reservation_code: str):
    """تأیید نهایی رزرو پس از پرداخت مسافر (بهینه‌شده)"""
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, "failed", "کلید API اسنپ‌تریپ تنظیم نشده است."

    confirm_url = f"{base_url}/booking/{snapp_reservation_code}/confirm"
    try:
        res = _snapp_session.post(confirm_url, json={}, headers=headers, timeout=15)
        
        if res.status_code not in [200, 201]:
            err_msg = res.text[:120]
            logger.error(f"Confirm failed on Snapp: {res.status_code} - {res.text}")
            return False, f"failed: {err_msg}", f"خطای تأیید در اسنپ: {err_msg}"

        final_status, _ = get_snapptrip_booking_status(snapp_reservation_code)
        return True, final_status, "رزرو با موفقیت در اسنپ قطعی شد."
    except Exception as e:
        logger.error(f"Error confirming booking {snapp_reservation_code}: {e}")
        return False, f"failed: {str(e)[:50]}", f"خطای ارتباط با اسنپ: {str(e)}"
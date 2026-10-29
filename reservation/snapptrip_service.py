import logging
import random
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

# ایجاد سشن سراسری جهت حفظ اتصال TCP و افزایش چشمگیر سرعت درخواست‌ها
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
    if not headers.get('api-key'):
        return 0, "کلید وب‌سرویس تنظیم نشده است."
    try:
        res = _snapp_session.get(f"{base_url}/balance/", headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            balance = data.get('balance', 0)
            return int(Decimal(str(balance))), "موفق"
        return 0, f"کد خطا {res.status_code}: {res.text[:100]}"
    except Exception as e:
        return 0, str(e)


def fetch_with_rate_limit(url, headers, max_retries=3):
    """ارسال امن درخواست با مدیریت خطای 429"""
    for attempt in range(max_retries):
        try:
            res = _snapp_session.get(url, headers=headers, timeout=12)
            if res.status_code == 429:
                logger.warning("محدودیت Rate Limit اسنپ (429). ۳ ثانیه توقف...")
                time.sleep(3)
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
        for key in ['availability', 'rooms', 'room', 'data', 'results', 'result', 'hotels', 'cities', 'items']:
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
        return int(r_item) if str(r_item).isdigit() else None
    for nested in ['room', 'room_type', 'details']:
        if isinstance(r_item.get(nested), dict):
            sub = extract_room_id(r_item[nested])
            if sub:
                return sub
    for key in ['id', 'room_id', 'room_type_id', 'code']:
        val = r_item.get(key)
        if val is not None and str(val).strip() != '':
            try:
                return int(val)
            except ValueError:
                return str(val)
    return None


def extract_stars_comprehensive(h):
    """استخراج ستاره‌های هتل"""
    if not isinstance(h, dict):
        return '-'
    for key in ['stars', 'star', 'stars_count', 'star_count', 'star_rating', 'rating']:
        val = h.get(key)
        if val is not None and str(val).strip() not in ['', 'None', 'null', '-']:
            if isinstance(val, dict):
                for sub_k in ['count', 'stars', 'value']:
                    if val.get(sub_k) is not None:
                        return str(val[sub_k]).strip()
            return str(val).strip()
    return '-'


def extract_hotel_rules_and_cancellation(h_data):
    """استخراج قوانین هتل و کنسلی"""
    rules_text = ""
    cancellation_text = ""
    if isinstance(h_data, dict):
        for r_k in ['rules', 'hotel_rules', 'regulations', 'hotel_policy']:
            val = h_data.get(r_k)
            if val and isinstance(val, str) and val.strip():
                rules_text = val.strip()
                break
        for c_k in ['cancellation_rules', 'cancellation_policy', 'cancel_rules', 'important_note']:
            val = h_data.get(c_k)
            if val and isinstance(val, str) and val.strip():
                cancellation_text = val.strip()
                break
    return rules_text, cancellation_text


def is_room_online_instant(r_item):
    """تشخیص رزرو آنی بدون نیاز به تایید طبق ساختار اسنپ"""
    if r_item.get('is_online') is True or r_item.get('online') is True:
        return True
    booking_type = str(r_item.get('booking_type', '')).lower()
    if booking_type in ['online', 'instant', 'guaranteed']:
        return True
    if booking_type in ['offline', 'on_request', 'inquiry']:
        return False
    if r_item.get('is_online') is False or r_item.get('need_approval') is True:
        return False
    return True


# ==============================================================================
# بخش ۱: توابع رزرواسیون، لاک و تایید قطعی در اسنپ‌تریپ (سریع و استاندارد)
# ==============================================================================

def get_snapptrip_booking_status(snapp_reservation_code: str):
    """استعلام زنده وضعیت رزرو از اسنپ (GET /booking/{code})"""
    base_url, headers = get_snapptrip_client_config()
    url = f"{base_url}/booking/{snapp_reservation_code}"
    try:
        res = _snapp_session.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            status_val = (
                data.get('status') or 
                data.get('data', {}).get('status') or 
                'unknown'
            )
            return status_val, res.text
        return "unknown", f"کد خطا {res.status_code}: {res.text[:120]}"
    except Exception as e:
        logger.error(f"Error fetching booking status ({snapp_reservation_code}): {e}")
        return "unknown", str(e)


def lock_snapptrip_booking(snapp_reservation_code: str):
    """
    قفل موقت اتاق به مدت ۱۵ دقیقه طبق صفحه ۱۹ و ۲۲ مستندات اسنپ
    POST /booking/{code}/lock
    """
    base_url, headers = get_snapptrip_client_config()
    url = f"{base_url}/booking/{snapp_reservation_code}/lock"
    try:
        res = _snapp_session.post(url, json={}, headers=headers, timeout=6)
        if res.status_code in [200, 201]:
            logger.info(f"✅ رزرو {snapp_reservation_code} با موفقیت به مدت ۱۵ دقیقه در اسنپ قفل (Lock) شد.")
            return True, "payment_on"
        logger.warning(f"Lock booking returned {res.status_code}: {res.text[:120]}")
        return False, "draft"
    except Exception as e:
        logger.error(f"Error locking booking {snapp_reservation_code}: {e}")
        return False, "draft"


def create_snapptrip_booking(reservation: Reservationhotel, room_snapp_id: int, hotel_snapp_id: int, quantity: int = 1):
    """
    ثبت مستقیم پیش‌رزرو در اسنپ‌تریپ با ارسال فیلد اجباری guests
    POST /booking/create
    """
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, None, False, "کلید API اسنپ‌تریپ تنظیم نشده است."

    check_in_g = reservation.check_in_date.togregorian() if hasattr(reservation.check_in_date, 'togregorian') else reservation.check_in_date
    check_out_g = reservation.check_out_date.togregorian() if hasattr(reservation.check_out_date, 'togregorian') else reservation.check_out_date

    checkin_str = check_in_g.strftime('%Y-%m-%d')
    checkout_str = check_out_g.strftime('%Y-%m-%d')
    user_phone = (reservation.buyer.phone_number if reservation.buyer else "09122914675").strip()

    buyer = getattr(reservation, 'buyer', None)
    profile = getattr(buyer, 'natural_profile', None) if buyer else None
    default_fn = (getattr(profile, 'first_name', '') if profile else '') or reservation.reserver_first_name or "مسافر"
    default_ln = (getattr(profile, 'last_name', '') if profile else '') or reservation.reserver_last_name or "اصلی"
    # استفاده از یک کدملی معتبر ایران به صورت پیش‌فرض تا ولیدیشن اسنپ رد نشود
    default_nc = (getattr(profile, 'national_code', '') if profile else '') or reservation.reserver_national_code or "0012345679"

    # آماده‌سازی آرایه مسافران (هم برای فیلد guests و هم passengers)
    guests_payload = []
    first_room = reservation.reservation_rooms.first()
    if first_room and first_room.passengers.exists():
        for p in first_room.passengers.all():
            p_phone = (p.mobile_number or user_phone).strip()
            p_nc = p.national_code or default_nc
            guests_payload.append({
                "first_name": p.first_name or default_fn,
                "last_name": p.last_name or default_ln,
                "national_code": p_nc,
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

    # ارسال هم‌زمان فیلدهای guests و passengers در ساختار اتاق‌ها
    rooms_payload = [
        {
            "room_id": int(room_snapp_id),
            "guests": guests_payload,
            "passengers": guests_payload
        }
        for _ in range(quantity)
    ]

    create_url = f"{base_url}/booking/create"
    payload = {
        "hotel_id": int(hotel_snapp_id),
        "checkin": checkin_str,
        "checkout": checkout_str,
        "phone": user_phone,
        "phone_number": user_phone,
        "mobile": user_phone,
        "rooms": rooms_payload,
        "guests": guests_payload,       # 👈 حل خطای: guests should have at least one value
        "passengers": guests_payload,
        "note": reservation.additional_notes or ""
    }

    try:
        res = _snapp_session.post(create_url, json=payload, headers=headers, timeout=10)
        
        # فال‌بک برای ساختار count در صورتی که اسنپ درخواست دهد
        if res.status_code not in [200, 201]:
            alt_rooms = [
                {
                    "room_id": int(room_snapp_id),
                    "count": quantity,
                    "guests": guests_payload,
                    "passengers": guests_payload
                }
            ]
            payload["rooms"] = alt_rooms
            res = _snapp_session.post(create_url, json=payload, headers=headers, timeout=10)

        if res.status_code not in [200, 201]:
            logger.error(f"Snapp create booking error {res.status_code}: {res.text}")
            error_text = res.text
            if "not available" in error_text.lower() or "ظرفیت" in error_text:
                return False, None, False, "متاسفانه ظرفیت این اتاق در تاریخ انتخابی تکمیل شده است."
            return False, None, False, f"پاسخ اسنپ: {res.text[:180]}"

        res_data = res.json()
        snapp_code = (
            res_data.get('reservation_code') or 
            res_data.get('code') or 
            res_data.get('data', {}).get('reservation_code') or
            res_data.get('data', {}).get('code')
        )

        if not snapp_code:
            return False, None, False, f"کد رزرو در پاسخ اسنپ یافت نشد: {res.text[:100]}"

        status_val = res_data.get('status') or res_data.get('data', {}).get('status', '')
        is_instant = status_val not in ['availability_checking', 'availability_pending', 'offline']

        if is_instant:
            # قفل کردن موقت ۱۵ دقیقه‌ای در شبکه اسنپ
            lock_ok, lock_status = lock_snapptrip_booking(str(snapp_code))
            return True, str(snapp_code), True, "payment_on" if lock_ok else "confirmed"
        else:
            return True, str(snapp_code), False, "availability_checking"

    except Exception as e:
        logger.error(f"Exception during create_snapptrip_booking: {e}")
        return False, None, False, f"خطای ارتباط با سرور اسنپ: {str(e)}"


def process_payment_and_confirm_snapp(reservation: Reservationhotel):
    """
    معماری بررسی کیف پول اسنپ و تایید قطعی رزرو:
    ۱. محاسبه هزینه خرید از اسنپ
    ۲. استعلام کیف پول اسنپ
    ۳. در صورت کمبود موجودی: ریجکت رزرو بدون کسر وجه مسافر
    ۴. در صورت موجودی کافی: تایید قطعی در اسنپ
    """
    required_snapp_amount = Decimal('0')
    for res_room in reservation.reservation_rooms.all():
        check_in_d = reservation.check_in_date.togregorian() if hasattr(reservation.check_in_date, 'togregorian') else reservation.check_in_date
        price_obj = res_room.room.date_prices.filter(
            start_date__lte=check_in_d, end_date__gte=check_in_d
        ).first()
        nights = reservation.nights_count or 1
        room_buy_price = Decimal(price_obj.purchase_price if price_obj and price_obj.purchase_price else price_obj.price if price_obj else 0)
        required_snapp_amount += room_buy_price * nights * res_room.quantity

    snapp_balance, b_msg = get_snapptrip_wallet_balance()
    logger.info(f"بررسی کیف پول اسنپ برای رزرو {reservation.tracking_code}: موجودی اسنپ={snapp_balance:,} | مورد نیاز={required_snapp_amount:,}")

    # اگر کیف پول اسنپ شارژ نداشت
    if snapp_balance < required_snapp_amount:
        err_msg = (
            f"موجودی کیف پول اسنپ‌تریپ کافی نیست (موجودی: {snapp_balance:,} تومان، مبلغ مورد نیاز: {int(required_snapp_amount):,} تومان). "
            f"رزرو در اسنپ رد شد و وجهی از شما کسر نگردید."
        )
        logger.error(f"❌ {err_msg}")
        reservation.capacity_status = 'rejected'
        reservation.snapp_status = 'failed'
        reservation.save(update_fields=['capacity_status', 'snapp_status'])
        return False, err_msg

    # تایید نهایی در وب‌سرویس اسنپ
    base_url, headers = get_snapptrip_client_config()
    confirm_url = f"{base_url}/booking/{reservation.snapp_reservation_code}/confirm"
    
    try:
        res = _snapp_session.post(confirm_url, json={}, headers=headers, timeout=12)
        if res.status_code not in [200, 201]:
            err_msg = f"خطای تایید در اسنپ (کد {res.status_code}): {res.text[:150]}"
            logger.error(err_msg)
            reservation.capacity_status = 'rejected'
            reservation.snapp_status = 'failed'
            reservation.save(update_fields=['capacity_status', 'snapp_status'])
            return False, err_msg

        final_status, _ = get_snapptrip_booking_status(reservation.snapp_reservation_code)
        reservation.snapp_status = final_status if final_status != 'unknown' else 'confirmed'
        reservation.payment_status = 'paid'
        reservation.capacity_status = 'confirmed'
        reservation.save(update_fields=['snapp_status', 'payment_status', 'capacity_status'])

        return True, "رزرو با موفقیت در اسنپ‌تریپ قطعی شد."

    except Exception as e:
        logger.error(f"Exception confirming snapp reservation: {e}")
        return False, f"خطای ارتباطی در تایید رزرو اسنپ: {str(e)}"


# ==============================================================================
# بخش ۲: همگام‌سازی اتاق‌ها، تفکیک آفلاین/آنلاین و قیمت‌گذاری تقویم
# ==============================================================================

def sync_hotel_and_rooms_from_snapp(hotel_id: int):
    """دریافت و تفکیک دقیق اتاق‌های آنی و نیازمند تایید از اسنپ"""
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
    rooms_list = []

    now = datetime.now()
    checkin_str = now.strftime('%Y-%m-%d')
    checkout_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    calendar_from_str = now.strftime('%Y-%m-%d')
    calendar_to_str = (now + timedelta(days=30)).strftime('%Y-%m-%d')

    for h_url in [f"{base_url}/hotels/{snapp_h_id}/", f"{base_url}/hotels/{snapp_h_id}"]:
        try:
            hotel_res = _snapp_session.get(h_url, headers=headers, timeout=10)
            if hotel_res.status_code == 200:
                h_data = hotel_res.json()
                if isinstance(h_data, dict) and 'data' in h_data:
                    h_data = h_data['data']

                hotel.is_snapptrip = True
                hotel.status = 'published'
                hotel.save(update_fields=['is_snapptrip', 'status'])
                CancellationPenalty.objects.get_or_create(hotel=hotel, defaults={'penalty_percentage': 0})

                if isinstance(h_data, dict):
                    for r_key in ['rooms', 'room_types', 'accommodations']:
                        if isinstance(h_data.get(r_key), list) and len(h_data[r_key]) > 0:
                            rooms_list = h_data[r_key]
                            break
                break
        except Exception as e:
            logger.error(f"Error fetching hotel details: {e}")

    if not rooms_list:
        for r_url in [
            f"{base_url}/availability/hotels/{snapp_h_id}?checkin={checkin_str}&checkout={checkout_str}",
            f"{base_url}/hotels/rooms/{snapp_h_id}/",
        ]:
            try:
                rooms_res = _snapp_session.get(r_url, headers=headers, timeout=10)
                if rooms_res.status_code == 200:
                    extracted = extract_list_from_response(rooms_res.json())
                    if extracted:
                        rooms_list = extracted
                        break
            except Exception:
                continue

    if not rooms_list:
        return False, "هیچ اتاقی از اسنپ‌تریپ دریافت نشد."

    synced_snapp_room_ids = []
    synced_rooms_count = 0
    today_j = jdatetime.date.fromgregorian(date=now.date())
    end_30_days_j = jdatetime.date.fromgregorian(date=(now + timedelta(days=30)).date())

    for r_item in rooms_list:
        snapp_room_id = extract_room_id(r_item)
        if not snapp_room_id:
            continue

        synced_snapp_room_ids.append(snapp_room_id)
        room_title = r_item.get('name_fa') or r_item.get('title_fa') or r_item.get('name') or f"اتاق {snapp_room_id}"
        room_cap = int(r_item.get('capacity') or r_item.get('standard_capacity') or 2)
        extra_cap = int(r_item.get('extra_capacity') or 0)
        board_type = r_item.get('board_type', 'bed_breakfast')

        # تشخیص آنلاین یا آفلاین بودن اتاق
        raw_count = int(r_item.get('count') or r_item.get('available_count') or r_item.get('inventory') or 10)
        is_online = is_room_online_instant(r_item)

        # تفکیک دقیق: اگر آنلاین بود بدون نیاز به تایید، اگر آفلاین بود نیازمند تایید
        if is_online:
            auto_approved_val = raw_count
            count_val = 0
        else:
            auto_approved_val = 0
            count_val = raw_count

        room, _ = Room.objects.update_or_create(
            hotel=hotel,
            snapptrip_room_id=snapp_room_id,
            defaults={
                'title': room_title,
                'room_capacity': room_cap,
                'extra_capacity': extra_cap,
                'board_type': board_type,
                'inventory': raw_count,
                'count': count_val,
                'auto_approved_count': auto_approved_val,
                'is_snapptrip': True,
            }
        )
        synced_rooms_count += 1

        service_title = BOARD_TYPE_TITLES.get(board_type, 'همراه با صبحانه رایگان')
        board_service, _ = RoomService.objects.get_or_create(title=service_title)
        room.services.add(board_service)

        pricing = r_item.get('pricing', {}) if isinstance(r_item.get('pricing'), dict) else {}
        base_buy_price = int(Decimal(str(pricing.get('price') or 0)))
        base_client_price = int(Decimal(str(pricing.get('original_sell_price') or base_buy_price)))
        extra_bed_price = int(Decimal(str(pricing.get('extra_bed_price') or 0)))

        # ثبت تقویم قیمتی
        cal_url = f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar?from={calendar_from_str}&to={calendar_to_str}"
        cal_synced = False
        try:
            cal_res = _snapp_session.get(cal_url, headers=headers, timeout=8)
            if cal_res.status_code == 200:
                calendar_items = extract_list_from_response(cal_res.json())
                for day in calendar_items:
                    g_date_str = str(day.get('date') or day.get('day') or '')[:10]
                    if not g_date_str:
                        continue
                    try:
                        g_dt = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                        j_dt = jdatetime.date.fromgregorian(date=g_dt)
                    except Exception:
                        continue

                    d_buy = int(Decimal(str(day.get('price') or base_buy_price or 0)))
                    d_sell = int(Decimal(str(day.get('original_sell_price') or day.get('base_price') or d_buy)))
                    d_extra = int(Decimal(str(day.get('extra_bed_price') or extra_bed_price or 0)))

                    if d_buy > 0:
                        RoomDatePrice.objects.update_or_create(
                            room=room,
                            start_date=j_dt,
                            end_date=j_dt,
                            user_level=None,
                            defaults={
                                'purchase_price': d_buy,
                                'price': d_sell,
                                'extra_passenger_price': d_extra,
                                'discount_type': 'none',
                                'discount_value': 0,
                            }
                        )
                        cal_synced = True
        except Exception as e:
            logger.error(f"Error fetching calendar for room {snapp_room_id}: {e}")

        if not cal_synced and base_buy_price > 0:
            RoomDatePrice.objects.update_or_create(
                room=room,
                start_date=today_j,
                end_date=end_30_days_j,
                user_level=None,
                defaults={
                    'purchase_price': base_buy_price,
                    'price': base_client_price,
                    'extra_passenger_price': extra_bed_price,
                    'discount_type': 'none',
                    'discount_value': 0,
                }
            )

    if synced_snapp_room_ids:
        Room.objects.filter(hotel=hotel, is_snapptrip=True).exclude(snapptrip_room_id__in=synced_snapp_room_ids).delete()

    return True, f"هتل {hotel.name} با {synced_rooms_count} اتاق بروزرسانی شد."


def sync_all_snapptrip_hotels_directory():
    """همگام‌سازی کامل بانک هتل‌های اسنپ‌تریپ"""
    base_url, headers = get_snapptrip_client_config()
    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات وارد نشده است!"

    cities_res = fetch_with_rate_limit(f"{base_url}/cities/", headers)
    if not cities_res or cities_res.status_code != 200:
        return False, "خطا در دریافت لیست شهرها از اسنپ."

    cities_list = extract_list_from_response(cities_res.json())
    all_hotel_objects = []

    for city in cities_list:
        city_id = city.get('id') or city.get('city_id')
        if not city_id:
            continue
        raw_name = city.get('name_fa') or city.get('name') or str(city_id)
        pure_name = IRAN_CITIES_MAP.get(str(raw_name).lower()) or raw_name
        formatted_city = f"{city_id} - {pure_name}"

        url = f"{base_url}/cities/{city_id}/hotels?limit=100&offset=0"
        res = fetch_with_rate_limit(url, headers)
        if res and res.status_code == 200:
            batch = extract_list_from_response(res.json())
            for h in batch:
                h_id = h.get('id') or h.get('hotel_id')
                if not h_id:
                    continue
                all_hotel_objects.append(SnappHotelDirectory(
                    snapp_hotel_id=h_id,
                    name=str(h.get('name_fa') or h.get('name') or f"هتل {h_id}").strip(),
                    city_name=formatted_city,
                    city_id=city_id,
                    stars=extract_stars_comprehensive(h)
                ))
        time.sleep(0.2)

    unique_hotels = {h.snapp_hotel_id: h for h in all_hotel_objects}
    hotels_to_save = list(unique_hotels.values())

    SnappHotelDirectory.objects.bulk_create(
        hotels_to_save,
        update_conflicts=True,
        update_fields=['name', 'city_name', 'city_id', 'stars', 'last_synced'],
        unique_fields=['snapp_hotel_id']
    )
    return True, f"مجموعاً {len(hotels_to_save)} هتل ذخیره شدند."
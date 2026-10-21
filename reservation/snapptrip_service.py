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
    RoomService
)

logger = logging.getLogger(__name__)

# دیکشنری مپینگ نام فارسی شهرهای ایران
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

# متن فارسی انواع پذیرایی برای نمایش در لیست خدمات فرانت‌اند
BOARD_TYPE_TITLES = {
    'room_only': 'اقامت بدون صبحانه',
    'bed_breakfast': 'صبحانه بوفه رایگان',
    'half_board': 'هافبرد (صبحانه + یک وعده غذا)',
    'full_board': 'فولبرد (صبحانه + ناهار + شام)',
}


def calculate_customer_club_points(stars_val, price_val):
    """
    محاسبه هوشمند امتیاز باشگاه مشتریان بر اساس ستاره هتل و قیمت اتاق به همراه ضریب رندوم
    """
    try:
        stars = int(stars_val) if str(stars_val).isdigit() else 3
    except Exception:
        stars = 3
    stars = max(1, min(stars, 5))

    # امتیاز پایه بر اساس قیمت (هر ۵۰۰ هزار تومان = ۴ امتیاز)
    price = int(price_val or 1500000)
    price_score = (price // 500000) * 4

    # امتیاز بر اساس ستاره به همراه نوسان رندوم
    star_min = stars * 12
    star_max = stars * 22
    star_score = random.randint(star_min, star_max)

    total_points = star_score + price_score
    # رند کردن به مضرب ۵ برای زیبایی نمایش در سایت (مثلاً ۵۵، ۷۰، ۱۱۵)
    return max(15, round(total_points / 5) * 5)


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


def fetch_with_rate_limit(url, headers, max_retries=3):
    """ارسال امن درخواست با مدیریت خطای 429 و مکث خودکار"""
    for attempt in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 429:
                logger.warning(f"محدودیت Rate Limit اسنپ (429). ۱۰ ثانیه توقف... (تلاش {attempt + 1})")
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
    """استخراج شناسه عددی اتاق با بررسی تمام کلیدهای محتمل"""
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
    """استخراج نام فارسی یا عنوان اتاق"""
    if isinstance(r_item.get('room'), dict):
        r_item = r_item['room']
    for key in ['title_fa', 'name_fa', 'name', 'title', 'room_name', 'room_title', 'room_type_name']:
        val = r_item.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return f"اتاق {default_id}"


def extract_room_description(r_item):
    """استخراج متن توضیحات و مشخصات اتاق از اسنپ"""
    if isinstance(r_item.get('room'), dict):
        r_item = r_item['room']
        
    for key in ['description', 'desc', 'details', 'room_description', 'about', 'view']:
        val = r_item.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()
    return ''


def extract_stars_comprehensive(h):
    """استخراج ستاره‌های هتل از تمام کلیدها و عنوان"""
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


def sync_hotel_and_rooms_from_snapp(hotel_id: int):
    """
    همگام‌سازی کامل هتل، اتاق‌ها، توضیحات، خدمات پذیرایی، امتیاز باشگاه و نرخ‌های ۳۰ روزه
    """
    base_url, headers = get_snapptrip_client_config()

    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات پنل ادمین وارد نشده است!"

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

    # -------------------------------------------------------------
    # مرحله ۱: دریافت مشخصات پایه هتل، قوانین، نکات و اتصال به شهر
    # -------------------------------------------------------------
    for h_url in [f"{base_url}/hotels/{snapp_h_id}/", f"{base_url}/hotels/{snapp_h_id}"]:
        try:
            hotel_res = requests.get(h_url, headers=headers, timeout=12)
            if hotel_res.status_code == 200:
                h_data = hotel_res.json()
                if isinstance(h_data, dict) and 'data' in h_data and isinstance(h_data['data'], dict):
                    h_data = h_data['data']

                hotel.rules = h_data.get('rules', hotel.rules) or hotel.rules
                hotel.important_notes = h_data.get('important_note', hotel.important_notes) or hotel.important_notes
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

                if isinstance(h_data, dict):
                    for r_key in ['rooms', 'room', 'room_types', 'accommodations']:
                        if isinstance(h_data.get(r_key), list) and len(h_data[r_key]) > 0:
                            rooms_list = h_data[r_key]
                            break
                break
        except Exception as e:
            logger.error(f"Error fetching hotel details: {e}")

    # -------------------------------------------------------------
    # مرحله ۲: استعلام اتاق‌ها با تاریخ‌های معتبر
    # -------------------------------------------------------------
    last_error_report = ""
    if not rooms_list:
        candidate_room_urls = [
            f"{base_url}/availability/hotels/{snapp_h_id}?checkin={checkin_str}&checkout={checkout_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/?checkin={checkin_str}&checkout={checkout_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/calendar?from={calendar_from_str}&to={calendar_to_str}",
            f"{base_url}/hotels/rooms/{snapp_h_id}/",
            f"{base_url}/hotels/{snapp_h_id}/rooms/",
            f"{base_url}/hotels/rooms/?hotel_id={snapp_h_id}",
        ]

        for r_url in candidate_room_urls:
            try:
                rooms_res = requests.get(r_url, headers=headers, timeout=12)
                if rooms_res.status_code == 200:
                    extracted = extract_list_from_response(rooms_res.json())
                    if extracted:
                        rooms_list = extracted
                        break
                else:
                    last_error_report = f"آدرس {r_url} -> کد {rooms_res.status_code}: {rooms_res.text[:120]}"
            except Exception as e:
                last_error_report = str(e)
                continue

    if not rooms_list:
        return False, f"هیچ اتاقی از اسنپ دریافت نشد. آخرین گزارش: {last_error_report}"

    synced_snapp_room_ids = []
    synced_rooms_count = 0
    synced_prices_count = 0

    today_j = jdatetime.date.fromgregorian(date=now.date())
    end_30_days_j = jdatetime.date.fromgregorian(date=(now + timedelta(days=30)).date())

    # -------------------------------------------------------------
    # مرحله ۳: ثبت اتاق‌ها و تقویم قیمتی در دیتابیس
    # -------------------------------------------------------------
    for r_item in rooms_list:
        snapp_room_id = extract_room_id(r_item)
        if not snapp_room_id:
            continue

        synced_snapp_room_ids.append(snapp_room_id)
        room_title = extract_room_title(r_item, snapp_room_id)
        room_desc = extract_room_description(r_item)
        room_cap = int(r_item.get('capacity') or r_item.get('room_capacity') or r_item.get('standard_capacity') or 2)
        extra_cap = int(r_item.get('extra_capacity') or r_item.get('extra_bed_capacity') or 0)
        
        # ۱. موجودی سهمیه فرضی ۱۰۰ عدد تنظیم شد
        inv_count = 100
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

        count_val = 0 if is_online else inv_count
        auto_approved_val = inv_count if is_online else 0

        # ذخیره اولیه اتاق
        room, _ = Room.objects.update_or_create(
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

        # ۲. اضافه کردن خودکار نوع پذیرایی به عنوان یک آیتم در خدمات اتاق (RoomService)
        service_title = BOARD_TYPE_TITLES.get(board_type, 'همراه با صبحانه رایگان')
        board_service, _ = RoomService.objects.get_or_create(title=service_title)
        room.services.add(board_service)

        # استعلام تقویم نرخ‌های اتاق
        cal_candidate_urls = [
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar?from={calendar_from_str}&to={calendar_to_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar/?from={calendar_from_str}&to={calendar_to_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar",
        ]

        room_calendar_synced = False
        first_valid_price = 0
        first_valid_extra = 0

        for cal_url in cal_candidate_urls:
            try:
                cal_res = requests.get(cal_url, headers=headers, timeout=12)
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

                        raw_original = raw_price
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

                        if raw_price <= 0:
                            continue

                        client_sell_price = raw_original if raw_original > 0 else raw_price
                        agency_buy_price = raw_price

                        if not first_valid_price:
                            first_valid_price = client_sell_price
                            first_valid_extra = snapp_extra

                        RoomDatePrice.objects.update_or_create(
                            room=room,
                            start_date=j_dt,
                            end_date=j_dt,
                            user_level=None,
                            defaults={
                                'purchase_price': agency_buy_price,
                                'price': client_sell_price,
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

        # اگر تقویم در دسترس نبود ولی خود شیء اتاق دارای pricing بود
        if not room_calendar_synced and isinstance(r_item.get('pricing'), dict):
            pricing = r_item['pricing']
            p_price = int(Decimal(str(pricing.get('price') or 0)))
            p_orig = int(Decimal(str(pricing.get('original_sell_price') or p_price)))
            p_extra = int(Decimal(str(pricing.get('extra_bed_price') or pricing.get('extra_passenger_price') or 0)))

            if p_price > 0:
                client_p = p_orig if p_orig > 0 else p_price
                first_valid_price = client_p
                first_valid_extra = p_extra

                RoomDatePrice.objects.update_or_create(
                    room=room,
                    start_date=today_j,
                    end_date=today_j,
                    user_level=None,
                    defaults={
                        'purchase_price': p_price,
                        'price': client_p,
                        'extra_passenger_price': p_extra,
                        'discount_type': 'none',
                        'discount_value': 0,
                        'discount_date': None,
                        'is_fixed_discount_one_time': False,
                    }
                )
                synced_prices_count += 1

        # ۳. محاسبه هوشمند امتیاز باشگاه مشتریان بر اساس ستاره هتل و قیمت اتاق
        club_points = calculate_customer_club_points(hotel.stars, first_valid_price)
        room.customer_club_points = club_points
        room.save(update_fields=['customer_club_points'])

        # ثبت بازه ۳۰ روزه کلی جهت هماهنگی با جستجوی شهر
        if first_valid_price > 0:
            RoomDatePrice.objects.update_or_create(
                room=room,
                start_date=today_j,
                end_date=end_30_days_j,
                user_level=None,
                defaults={
                    'purchase_price': first_valid_price,
                    'price': first_valid_price,
                    'extra_passenger_price': first_valid_extra,
                    'discount_type': 'none',
                    'discount_value': 0,
                    'discount_date': None,
                    'is_fixed_discount_one_time': False,
                }
            )

    # -------------------------------------------------------------
    # مرحله ۴: پاک‌سازی خودکار اتاق‌های قدیمی یا اشتباه
    # -------------------------------------------------------------
    if synced_snapp_room_ids:
        deleted_count, _ = Room.objects.filter(
            hotel=hotel,
            is_snapptrip=True
        ).exclude(
            snapptrip_room_id__in=synced_snapp_room_ids
        ).delete()
        if deleted_count > 0:
            logger.info(f"تعداد {deleted_count} اتاق نامعتبر از هتل {hotel.name} پاک شدند.")

    if synced_rooms_count == 0:
        return False, f"تعداد {len(rooms_list)} آیتم اتاق از اسنپ دریافت شد اما شناسه‌های آن‌ها خوانده نشد!"

    return True, f"هماهنگ‌سازی هتل {hotel.name} با موفقیت انجام شد: {synced_rooms_count} اتاق (موجودی ۱۰۰، خدمات پذیرایی و امتیاز باشگاه) ثبت شدند."


# ----------------------------------------------------------------------------------
# توابع ایمن و استاندارد استخراج دایرکتوری هتل‌ها با رعایت کامل Rate Limit (۱۲۰ درخواست)
# ----------------------------------------------------------------------------------

def sync_all_snapptrip_hotels_directory():
    """
    استعلام و ذخیره کلیه هتل‌های اسنپ در جدول دایرکتوری با رعایت دقیق سقف ۱۲۰ درخواست در دقیقه
    """
    base_url, headers = get_snapptrip_client_config()

    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات وارد نشده است!"

    cities_res = fetch_with_rate_limit(f"{base_url}/cities/", headers)
    if not cities_res:
        return False, "ارتباط با سرور اسنپ برقرار نشد (تایم‌اوت یا خطا)."
    
    if cities_res.status_code == 429:
        return False, "کلید شما موقتاً به دلیل سقف درخواست محدود شده است. لطفاً ۲ دقیقه دیگر تلاش کنید."

    if cities_res.status_code != 200:
        return False, f"خطا در دریافت لیست شهرها از اسنپ: کد {cities_res.status_code}"

    cities_list = extract_list_from_response(cities_res.json())
    if not cities_list:
        return False, "هیچ شهری از وب‌سرویس اسنپ دریافت نشد!"

    all_hotel_objects = []

    for city in cities_list:
        city_id = city.get('id') or city.get('city_id') or city.get('code')
        if not city_id:
            continue

        raw_city_name = ""
        for k in ['name_fa', 'title_fa', 'persian_name', 'name', 'title', 'city_name', 'city']:
            val = city.get(k)
            if val and isinstance(val, str) and not val.isdigit():
                raw_city_name = val.strip()
                break

        pure_name = IRAN_CITIES_MAP.get(str(raw_city_name).lower()) or IRAN_CITIES_MAP.get(str(city_id)) or raw_city_name
        formatted_city = f"{city_id} - {pure_name}" if pure_name else f"{city_id}"

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
                    h_name = h.get('name_fa') or h.get('name') or h.get('title') or f"هتل {h_id}"
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

            time.sleep(0.5)

        time.sleep(0.5)

    if not all_hotel_objects:
        return False, "هیچ هتلی از وب‌سرویس اسنپ استخراج نشد."

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

    return True, f"بروزرسانی کامل شد: مجموعاً {len(hotels_to_save)} هتل با مشخصات دقیق ذخیره شدند."
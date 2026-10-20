import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
import requests
import jdatetime
from django.conf import settings
from .models import Hotel, Room, RoomDatePrice, CancellationPenalty, SnappHotelDirectory, SnappTripSetting

logger = logging.getLogger(__name__)


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


def extract_list_from_response(data):
    """استخراج هوشمند آرایه از هر نوع فرمت پاسخ وب‌سرویس اسنپ (کلیدهای شناخته‌شده یا هر لیست از دیکشنری‌ها)"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # بررسی کلیدهای متداول
        for key in ['data', 'results', 'result', 'rooms', 'room', 'hotels', 'cities', 'items', 'list', 'availability']:
            val = data.get(key)
            if isinstance(val, list) and len(val) > 0:
                return val
            if isinstance(val, dict):
                nested = extract_list_from_response(val)
                if nested:
                    return nested
        # در صورت نبودن کلیدهای بالا، هر کلیدی که مقدارش لیستی از دیکشنری‌ها باشد
        for key, val in data.items():
            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                return val
    return []


def extract_room_id(r_item):
    """استخراج شناسه اتاق با بررسی تمام کلیدهای محتمل و ساختارهای تو در تو"""
    if not isinstance(r_item, dict):
        if isinstance(r_item, (int, str)) and str(r_item).isdigit():
            return int(r_item)
        return None

    # بررسی آبجکت‌های تو در تو
    for nested_key in ['room', 'room_type', 'details']:
        if isinstance(r_item.get(nested_key), dict):
            sub_id = extract_room_id(r_item[nested_key])
            if sub_id:
                return sub_id

    # بررسی کلیدهای مستقیم
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


def sync_hotel_and_rooms_from_snapp(hotel_id: int):
    """
    همگام‌سازی کامل هتل، اتاق‌ها، قوانین و نرخ‌های تقویم ۳۰ روز آینده از اسنپ
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

    # -------------------------------------------------------------
    # مرحله ۱: استعلام مشخصات، قوانین و نکات هتل
    # -------------------------------------------------------------
    hotel_urls = [
        f"{base_url}/hotels/{snapp_h_id}/",
        f"{base_url}/hotels/{snapp_h_id}",
    ]
    for h_url in hotel_urls:
        try:
            hotel_res = requests.get(h_url, headers=headers, timeout=15)
            if hotel_res.status_code == 200:
                h_data = hotel_res.json()
                if isinstance(h_data, dict) and 'data' in h_data and isinstance(h_data['data'], dict):
                    h_data = h_data['data']

                hotel.rules = h_data.get('rules', hotel.rules) or hotel.rules
                hotel.important_notes = h_data.get('important_note', hotel.important_notes) or hotel.important_notes
                hotel.is_snapptrip = True
                hotel.save(update_fields=['rules', 'important_notes', 'is_snapptrip'])
                CancellationPenalty.objects.get_or_create(hotel=hotel, defaults={'penalty_percentage': 0})

                # بررسی اینکه آیا خود پاسخ هتل دارای لیست اتاق‌ها هست یا نه
                if isinstance(h_data, dict):
                    for r_key in ['rooms', 'room', 'room_types', 'accommodations']:
                        if isinstance(h_data.get(r_key), list) and len(h_data[r_key]) > 0:
                            rooms_list = h_data[r_key]
                            break
                break
        except Exception as e:
            logger.error(f"Error fetching hotel details: {e}")

    # -------------------------------------------------------------
    # مرحله ۲: استعلام اتاق‌ها در صورت نبودن در پاسخ اصلی هتل
    # -------------------------------------------------------------
    last_error_report = ""
    if not rooms_list:
        candidate_room_urls = [
            f"{base_url}/hotels/rooms/{snapp_h_id}/",
            f"{base_url}/hotels/rooms/{snapp_h_id}",
            f"{base_url}/hotels/{snapp_h_id}/rooms/",
            f"{base_url}/hotels/{snapp_h_id}/rooms",
            f"{base_url}/hotels/rooms/?hotel_id={snapp_h_id}",
            f"{base_url}/hotels/rooms?hotel_id={snapp_h_id}",
            f"{base_url}/availability/hotels/{snapp_h_id}/",
            f"{base_url}/availability/hotels/{snapp_h_id}",
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
        return False, f"هیچ اتاقی از اسنپ دریافت نشد. آخرین گزارش ارتباط: {last_error_report}"

    synced_rooms_count = 0
    synced_prices_count = 0

    # بازه زمانی ۳۰ روز آینده برای دریافت تقویم قیمت‌ها
    today_dt = datetime.now().date()
    from_date_str = today_dt.strftime('%Y-%m-%d')
    to_date_str = (today_dt + timedelta(days=30)).strftime('%Y-%m-%d')

    # -------------------------------------------------------------
    # مرحله ۳: ثبت اتاق‌ها و تقویم قیمتی در جدول دیتابیس
    # -------------------------------------------------------------
    for r_item in rooms_list:
        snapp_room_id = extract_room_id(r_item)
        if not snapp_room_id:
            continue

        room_title = extract_room_title(r_item, snapp_room_id)
        room_cap = int(r_item.get('capacity') or r_item.get('room_capacity') or r_item.get('standard_capacity') or 2)
        extra_cap = int(r_item.get('extra_capacity') or r_item.get('extra_bed_capacity') or 0)
        inv_count = int(r_item.get('count') or r_item.get('inventory') or r_item.get('available_count') or 5)
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

        if is_online:
            count_val = 0
            auto_approved_val = inv_count
        else:
            count_val = inv_count
            auto_approved_val = 0

        room, _ = Room.objects.update_or_create(
            hotel=hotel,
            snapptrip_room_id=snapp_room_id,
            defaults={
                'title': room_title,
                'description': r_item.get('description', '') or '',
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

        # استعلام تقویم نرخ‌های این اتاق
        cal_candidate_urls = [
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar?from={from_date_str}&to={to_date_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar/?from={from_date_str}&to={to_date_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar/",
        ]

        for cal_url in cal_candidate_urls:
            try:
                cal_res = requests.get(cal_url, headers=headers, timeout=12)
                if cal_res.status_code == 200:
                    calendar_items = extract_list_from_response(cal_res.json())

                    for day_data in calendar_items:
                        if not isinstance(day_data, dict):
                            continue

                        # استخراج تاریخ روز
                        g_date_str = day_data.get('date') or day_data.get('day') or day_data.get('calendar_date')
                        if not g_date_str:
                            continue
                        g_date_str = str(g_date_str)[:10]

                        try:
                            g_dt = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                            j_dt = jdatetime.date.fromgregorian(date=g_dt)
                        except Exception:
                            continue

                        # استخراج قیمت‌ها
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
                        for epk in ['extra_bed_price', 'extra_passenger_price', 'extra_price']:
                            if day_data.get(epk):
                                try:
                                    snapp_extra = int(Decimal(str(day_data[epk])))
                                    break
                                except Exception:
                                    pass

                        if raw_price <= 0:
                            continue

                        # بررسی تخفیف و تنظیم تایمر معکوس
                        if raw_original > raw_price:
                            calculated_percent = round(((raw_original - raw_price) / raw_original) * 100)
                            base_price = raw_original
                            disc_type = 'percentage'
                            disc_val = calculated_percent
                            disc_date = j_dt
                        else:
                            base_price = raw_price
                            disc_type = 'none'
                            disc_val = 0
                            disc_date = None

                        RoomDatePrice.objects.update_or_create(
                            room=room,
                            start_date=j_dt,
                            end_date=j_dt,
                            user_level=None,
                            defaults={
                                'purchase_price': raw_price,
                                'price': base_price,
                                'extra_passenger_price': snapp_extra,
                                'discount_type': disc_type,
                                'discount_value': disc_val,
                                'discount_date': disc_date,
                                'is_fixed_discount_one_time': False,
                            }
                        )
                        synced_prices_count += 1
                    break
            except Exception as e:
                logger.error(f"Error fetching calendar for room {snapp_room_id}: {e}")

    if synced_rooms_count == 0:
        return False, f"تعداد {len(rooms_list)} آیتم اتاق از اسنپ دریافت شد اما کلیدهای شناسه آن‌ها خوانده نشد!"

    return True, f"هماهنگ‌سازی هتل {hotel.name} با موفقیت انجام شد: {synced_rooms_count} اتاق و {synced_prices_count} تاریخ قیمت ذخیره شدند."


def sync_all_snapptrip_hotels_directory():
    """
    دریافت تمام شهرها و تمامی صفحات هتل‌های اسنپ با رفع مشکل صفحه‌بندی (Pagination)
    و استخراج صحیح نام فارسی شهر و تعداد ستاره‌ها
    """
    base_url, headers = get_snapptrip_client_config()

    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات وارد نشده است!"

    # ۱. دریافت لیست شهرها از اسنپ
    try:
        cities_res = requests.get(f"{base_url}/cities/", headers=headers, timeout=20)
        if cities_res.status_code != 200:
            return False, f"خطا در دریافت لیست شهرها از اسنپ: کد {cities_res.status_code}"
        
        cities_data = cities_res.json()
        cities_list = extract_list_from_response(cities_data)
    except Exception as e:
        return False, f"خطای اتصال به سرور اسنپ: {str(e)}"

    if not cities_list:
        return False, "هیچ شهری از وب‌سرویس اسنپ دریافت نشد!"

    total_created = 0
    total_updated = 0

    # ۲. پیمایش تک‌تک شهرها
    for city in cities_list:
        city_id = city.get('id') or city.get('city_id') or city.get('code')
        if not city_id:
            continue

        city_name = ""
        for k in ['name_fa', 'name', 'title_fa', 'title', 'city_name', 'persian_name']:
            val = city.get(k)
            if val and isinstance(val, str) and not val.isdigit():
                city_name = val.strip()
                break

        offset = 0
        limit = 50
        max_pages = 20

        for _ in range(max_pages):
            candidate_urls = [
                f"{base_url}/cities/{city_id}/hotel/?limit={limit}&offset={offset}",
                f"{base_url}/cities/{city_id}/hotels/?limit={limit}&offset={offset}",
                f"{base_url}/cities/{city_id}/hotels?limit={limit}&offset={offset}",
            ]

            hotels_batch = []
            for hotels_url in candidate_urls:
                try:
                    hotels_res = requests.get(hotels_url, headers=headers, timeout=12)
                    if hotels_res.status_code == 200:
                        extracted = extract_list_from_response(hotels_res.json())
                        if extracted:
                            hotels_batch = extracted
                            break
                except Exception:
                    continue

            if not hotels_batch:
                break

            for h in hotels_batch:
                h_id = h.get('id') or h.get('hotel_id') or h.get('code')
                if not h_id:
                    continue

                h_name = ""
                for k in ['name_fa', 'name', 'title_fa', 'title', 'hotel_name']:
                    val = h.get(k)
                    if val and isinstance(val, str):
                        h_name = val.strip()
                        break
                if not h_name:
                    h_name = f"هتل {h_id}"

                current_city_name = city_name
                if not current_city_name:
                    h_city = h.get('city')
                    if isinstance(h_city, dict):
                        current_city_name = h_city.get('name_fa') or h_city.get('name') or h_city.get('title')
                    elif isinstance(h_city, str) and not h_city.isdigit():
                        current_city_name = h_city
                    elif h.get('city_name'):
                        current_city_name = h.get('city_name')

                stars = "-"
                for k in ['stars', 'star', 'stars_count', 'star_rating', 'rating', 'grade', 'hotel_stars']:
                    if k in h and h[k] is not None:
                        stars_val = str(h[k]).strip()
                        if stars_val:
                            stars = stars_val
                            break

                obj, created = SnappHotelDirectory.objects.update_or_create(
                    snapp_hotel_id=h_id,
                    defaults={
                        'name': h_name,
                        'city_name': current_city_name or f"شهر {city_id}",
                        'city_id': city_id,
                        'stars': stars,
                    }
                )
                if created:
                    total_created += 1
                else:
                    total_updated += 1

            if len(hotels_batch) < limit:
                break

            offset += limit
            time.sleep(0.04)

        time.sleep(0.04)

    return True, f"بروزرسانی کامل شد: مجموعاً {total_created + total_updated} هتل با نام شهر و ستاره‌ها ثبت شدند."
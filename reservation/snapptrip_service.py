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
    """استخراج هوشمند آرایه از هر نوع فرمت پاسخ وب‌سرویس اسنپ (شامل data، results و تو در تو)"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ['data', 'results', 'result', 'hotels', 'cities', 'rooms', 'items', 'list']:
            val = data.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                nested = extract_list_from_response(val)
                if nested:
                    return nested
    return []

def sync_hotel_and_rooms_from_snapp(hotel_id: int):
    """
    ۱. دریافت قوانین و نکات هتل و ذخیره در Hotel
    ۲. دریافت اتاق‌ها با تست فرمت‌های استاندارد اندپوینت اتاق‌های اسنپ
    ۳. تفکیک خودکار اتاق‌های آنی (dont_accept_need) و استعلامی (accept_need)
    ۴. محاسبه خودکار تخفیف درصدی و ذخیره نرخ‌های ۳۰ روز آینده در RoomDatePrice
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
    rooms_from_hotel_details = []

    # -------------------------------------------------------------
    # مرحله ۱: دریافت قوانین کلی، نکات مهم و مشخصات هتل
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
                if isinstance(h_data, dict) and 'data' in h_data:
                    h_data = h_data['data']
                hotel.rules = h_data.get('rules', hotel.rules) or hotel.rules
                hotel.important_notes = h_data.get('important_note', hotel.important_notes) or hotel.important_notes
                hotel.is_snapptrip = True
                hotel.save(update_fields=['rules', 'important_notes', 'is_snapptrip'])
                CancellationPenalty.objects.get_or_create(hotel=hotel, defaults={'penalty_percentage': 0})

                # بررسی اینکه آیا خود پاسخ هتل شامل لیست اتاق‌ها هم هست یا خیر
                if isinstance(h_data, dict) and 'rooms' in h_data and isinstance(h_data['rooms'], list):
                    rooms_from_hotel_details = h_data['rooms']
                break
        except Exception as e:
            logger.error(f"Error fetching hotel details from Snapp: {e}")

    # -------------------------------------------------------------
    # مرحله ۲: دریافت اتاق‌ها (بررسی مسیرهای استاندارد Path و Query)
    # -------------------------------------------------------------
    rooms_list = rooms_from_hotel_details
    last_error_text = ""
    last_status_code = None

    if not rooms_list:
        candidate_room_urls = [
            f"{base_url}/hotels/rooms/{snapp_h_id}/",
            f"{base_url}/hotels/rooms/{snapp_h_id}",
            f"{base_url}/hotels/{snapp_h_id}/rooms/",
            f"{base_url}/hotels/{snapp_h_id}/rooms",
            f"{base_url}/hotels/rooms/?hotel_id={snapp_h_id}",
            f"{base_url}/hotels/rooms?hotel_id={snapp_h_id}",
            f"{base_url}/hotels/rooms/?id={snapp_h_id}",
            f"{base_url}/hotels/rooms?id={snapp_h_id}",
        ]

        for r_url in candidate_room_urls:
            try:
                rooms_res = requests.get(r_url, headers=headers, timeout=15)
                last_status_code = rooms_res.status_code
                if rooms_res.status_code == 200:
                    rooms_payload = rooms_res.json()
                    extracted = extract_list_from_response(rooms_payload)
                    if extracted:
                        rooms_list = extracted
                        break
                else:
                    last_error_text = f"کد {rooms_res.status_code} روی آدرس {r_url}: {rooms_res.text[:150]}"
            except Exception as e:
                last_error_text = str(e)
                continue

    if not rooms_list:
        return False, f"خطا در دریافت لیست اتاق‌ها از اسنپ: {last_error_text}"

    synced_rooms_count = 0
    synced_prices_count = 0

    # تاریخ ۳۰ روز آینده برای تقویم
    today_dt = datetime.now().date()
    from_date_str = today_dt.strftime('%Y-%m-%d')
    to_date_str = (today_dt + timedelta(days=30)).strftime('%Y-%m-%d')

    # -------------------------------------------------------------
    # مرحله ۳: ثبت اتاق‌ها و تقویم قیمتی در جدول RoomDatePrice
    # -------------------------------------------------------------
    for r_item in rooms_list:
        snapp_room_id = r_item.get('id') or r_item.get('room_id') or r_item.get('code')
        if not snapp_room_id:
            continue

        room_title = r_item.get('name') or r_item.get('title') or f"اتاق {snapp_room_id}"
        room_cap = int(r_item.get('capacity', 2) or 2)
        extra_cap = int(r_item.get('extra_capacity', 0) or 0)
        inv_count = int(r_item.get('count', 5) or 5)
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

        # دریافت تقویم قیمت‌های اتاق (تست آدرس با و بدون پارامتر تاریخ)
        cal_candidate_urls = [
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar?from={from_date_str}&to={to_date_str}",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar/",
            f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar",
        ]
        
        for cal_url in cal_candidate_urls:
            try:
                cal_res = requests.get(cal_url, headers=headers, timeout=12)
                if cal_res.status_code == 200:
                    calendar_items = extract_list_from_response(cal_res.json())

                    for day_data in calendar_items:
                        g_date_str = day_data.get('date')
                        if not g_date_str:
                            continue

                        g_dt = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                        j_dt = jdatetime.date.fromgregorian(date=g_dt)

                        raw_price = int(Decimal(day_data.get('price', 0) or 0))
                        raw_original = int(Decimal(day_data.get('original_sell_price', 0) or raw_price))
                        snapp_extra = int(Decimal(day_data.get('extra_bed_price', 0) or 0))

                        if raw_price <= 0:
                            continue

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
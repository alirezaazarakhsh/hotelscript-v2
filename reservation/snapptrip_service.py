import logging
from datetime import datetime
from decimal import Decimal
import requests
import jdatetime
from django.conf import settings
from .models import Hotel, Room, RoomDatePrice, CancellationPenalty, SnappTripSetting

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

def sync_hotel_and_rooms_from_snapp(hotel_id: int):
    """
    ۱. دریافت قوانین و نکات هتل و ذخیره در Hotel
    ۲. دریافت اتاق‌ها به همراه قوانین اختصاصی هر اتاق و ذخیره در Room
    ۳. تفکیک خودکار اتاق‌های آنی (dont_accept_need) و استعلامی (accept_need)
    ۴. محاسبه خودکار تخفیف درصدی و تاریخ انقضا جهت نمایش قیمت خط‌خورده و تایمر معکوس در فرانت‌اند
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

    # -------------------------------------------------------------
    # مرحله ۱: دریافت قوانین کلی، نکات مهم و ساعات ورود/خروج هتل
    # -------------------------------------------------------------
    try:
        hotel_res = requests.get(f"{base_url}/hotels/{snapp_h_id}", headers=headers, timeout=15)
        if hotel_res.status_code == 200:
            h_data = hotel_res.json()
            hotel.rules = h_data.get('rules', hotel.rules) or hotel.rules
            hotel.important_notes = h_data.get('important_note', hotel.important_notes) or hotel.important_notes
            hotel.is_snapptrip = True
            hotel.save(update_fields=['rules', 'important_notes', 'is_snapptrip'])
            CancellationPenalty.objects.get_or_create(hotel=hotel, defaults={'penalty_percentage': 0})
    except Exception as e:
        logger.error(f"Error fetching hotel details from Snapp: {e}")

    # -------------------------------------------------------------
    # مرحله ۲: دریافت اتاق‌ها و قوانین اختصاصی هر اتاق
    # -------------------------------------------------------------
    try:
        rooms_res = requests.get(f"{base_url}/hotels/rooms?hotel_id={snapp_h_id}", headers=headers, timeout=15)
        if rooms_res.status_code != 200:
            return False, f"خطا در دریافت لیست اتاق‌ها از اسنپ (کد {rooms_res.status_code})"

        rooms_payload = rooms_res.json()
        rooms_list = rooms_payload if isinstance(rooms_payload, list) else rooms_payload.get('results', rooms_payload.get('rooms', []))
    except Exception as e:
        return False, f"خطای ارتباط با سرور اسنپ: {str(e)}"

    if not rooms_list:
        return False, "هیچ اتاقی برای این هتل در اسنپ‌تریپ یافت نشد."

    synced_rooms_count = 0
    synced_prices_count = 0

    # -------------------------------------------------------------
    # مرحله ۳: ثبت اتاق‌ها و تقویم قیمتی در جدول RoomDatePrice
    # -------------------------------------------------------------
    for r_item in rooms_list:
        snapp_room_id = r_item.get('id') or r_item.get('room_id')
        if not snapp_room_id:
            continue

        room_title = r_item.get('name') or r_item.get('title') or f"اتاق {snapp_room_id}"
        room_cap = int(r_item.get('capacity', 2) or 2)
        extra_cap = int(r_item.get('extra_capacity', 0) or 0)
        inv_count = int(r_item.get('count', 5) or 5)
        board_type = r_item.get('board_type', 'bed_breakfast')

        # استخراج قوانین و مقررات اختصاصی اتاق
        room_rules = (
            r_item.get('rules') or 
            r_item.get('policy') or 
            r_item.get('cancellation_rules') or 
            r_item.get('cancellation_policy') or 
            ''
        )

        # تشخیص آنلاین (آنی) یا آفلاین (استعلامی) بودن اتاق در اسنپ
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

        # ذخیره یا بروزرسانی اتاق در دیتابیس لوکال
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

        # دریافت تقویم قیمت‌های این اتاق از اسنپ
        try:
            cal_url = f"{base_url}/availability/hotels/{snapp_h_id}/room/{snapp_room_id}/calendar"
            cal_res = requests.get(cal_url, headers=headers, timeout=12)
            
            if cal_res.status_code == 200:
                calendar_items = cal_res.json()
                if isinstance(calendar_items, dict):
                    calendar_items = calendar_items.get('calendar', calendar_items.get('days', []))

                for day_data in calendar_items:
                    g_date_str = day_data.get('date')
                    if not g_date_str:
                        continue

                    # تبدیل میلادی به شمسی
                    g_dt = datetime.strptime(g_date_str, "%Y-%m-%d").date()
                    j_dt = jdatetime.date.fromgregorian(date=g_dt)

                    # استخراج قیمت‌ها
                    raw_price = int(Decimal(day_data.get('price', 0) or 0))
                    raw_original = int(Decimal(day_data.get('original_sell_price', 0) or raw_price))
                    snapp_extra = int(Decimal(day_data.get('extra_bed_price', 0) or 0))

                    if raw_price <= 0:
                        continue

                    # بررسی وجود تخفیف و محاسبه درصد و تاریخ انقضا برای فعال‌سازی تایمر
                    if raw_original > raw_price:
                        calculated_percent = round(((raw_original - raw_price) / raw_original) * 100)
                        
                        base_price = raw_original       # قیمت اصلی (خط‌خورده در فرانت)
                        disc_type = 'percentage'        # نوع تخفیف: درصدی
                        disc_val = calculated_percent   # درصد تخفیف (مثلاً 10)
                        disc_date = j_dt                # تاریخ انقضا: تا پایان روز (فعال‌کننده تایمر معکوس)
                    else:
                        base_price = raw_price
                        disc_type = 'none'
                        disc_val = 0
                        disc_date = None

                    # ذخیره قیمت و تخفیف در RoomDatePrice
                    RoomDatePrice.objects.update_or_create(
                        room=room,
                        start_date=j_dt,
                        end_date=j_dt,
                        user_level=None,  # قیمت عمومی
                        defaults={
                            'purchase_price': raw_price,     # قیمت خرید شما از اسنپ
                            'price': base_price,             # قیمت پایه نمایشی
                            'extra_passenger_price': snapp_extra,
                            'discount_type': disc_type,
                            'discount_value': disc_val,
                            'discount_date': disc_date,
                            'is_fixed_discount_one_time': False,
                        }
                    )
                    synced_prices_count += 1
        except Exception as e:
            logger.error(f"Error fetching calendar for room {snapp_room_id}: {e}")

    return True, f"هماهنگ‌سازی با موفقیت انجام شد: {synced_rooms_count} اتاق (با قوانین) و {synced_prices_count} تاریخ قیمت و تخفیف ذخیره شدند."




def sync_all_snapptrip_hotels_directory():
    """
    دریافت تمام شهرها و هتل‌های اسنپ و ذخیره/بروزرسانی آن‌ها در جدول SnappHotelDirectory
    """
    base_url, headers = get_snapptrip_client_config()

    if not headers.get('api-key'):
        return False, "کلید API اسنپ‌تریپ در تنظیمات وارد نشده است!"

    try:
        cities_res = requests.get(f"{base_url}/cities/", headers=headers, timeout=20)
        if cities_res.status_code != 200:
            return False, f"خطا در دریافت لیست شهرها از اسنپ (کد {cities_res.status_code})"
        
        cities_data = cities_res.json()
        cities_list = cities_data if isinstance(cities_data, list) else cities_data.get('results', cities_data.get('cities', []))
    except Exception as e:
        return False, f"خطای اتصال به سرور اسنپ: {str(e)}"

    total_created = 0
    total_updated = 0

    for city in cities_list:
        city_id = city.get('id') or city.get('city_id')
        city_name = city.get('name') or city.get('title') or f"شهر {city_id}"

        if not city_id:
            continue

        try:
            hotels_url = f"{base_url}/cities/{city_id}/hotels"
            hotels_res = requests.get(hotels_url, headers=headers, timeout=15)

            if hotels_res.status_code == 200:
                hotels_data = hotels_res.json()
                hotels_list = hotels_data if isinstance(hotels_data, list) else hotels_data.get('results', hotels_data.get('hotels', []))

                for h in hotels_list:
                    h_id = h.get('id') or h.get('hotel_id')
                    h_name = h.get('name') or h.get('title') or ''
                    stars = str(h.get('stars') or h.get('star') or '-')

                    if not h_id:
                        continue

                    obj, created = SnappHotelDirectory.objects.update_or_create(
                        snapp_hotel_id=h_id,
                        defaults={
                            'name': h_name,
                            'city_name': city_name,
                            'city_id': city_id,
                            'stars': stars,
                        }
                    )
                    if created:
                        total_created += 1
                    else:
                        total_updated += 1

            time.sleep(0.05)  # مکث کوتاه برای رعایت سقف درخواست‌ها
        except Exception as e:
            logger.error(f"Error fetching hotels for city {city_name}: {e}")

    return True, f"بروزرسانی کامل شد: {total_created} هتل جدید اضافه و {total_updated} هتل بروزرسانی شدند."
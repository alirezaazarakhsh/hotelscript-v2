# hotel_backup/services.py
import json
import os
import shutil
import tempfile
import zipfile
from io import BytesIO, StringIO
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.db import models, transaction

# نام اپلیکیشن اصلی هتل‌ها
APP_NAME = 'reservation'

# مدل‌ها دقیقاً بر اساس اولویت وابستگی
BACKUP_MODELS = [
    'icons.IconShortcut',
    'config.UserLevel',
    f'{APP_NAME}.Province',
    f'{APP_NAME}.City',
    f'{APP_NAME}.HotelType',
    f'{APP_NAME}.HotelTag',
    f'{APP_NAME}.HotelTagPublic',
    f'{APP_NAME}.Facilities',
    f'{APP_NAME}.RoomFacilities',
    f'{APP_NAME}.BestHotels',
    f'{APP_NAME}.Hotel',
    f'{APP_NAME}.SEOMeta',
    f'{APP_NAME}.HotelGallery',
    f'{APP_NAME}.HotelGalleryImage',
    f'{APP_NAME}.NearbyPlace',
    f'{APP_NAME}.HotelFAQ',
    f'{APP_NAME}.CancellationPenalty',
    f'{APP_NAME}.RoomService',
    f'{APP_NAME}.Room',
    f'{APP_NAME}.RoomDatePrice',
    f'{APP_NAME}.ClosedDate',
]

# پوشه‌های تصاویر و آیکون‌ها
MEDIA_SUBDIRS = [
    'icons/svg_icons',
    'images/hotels',
    'room_images',
    'hotel_gallery',
    'images/nearby-places',
    'images/best_hotels',
    'cities',
]

class HotelBackupService:

    @classmethod
    def export_json_string(cls) -> str:
        """استخراج اطلاعات به صورت رشته متنی JSON"""
        string_buf = StringIO()
        call_command(
            'dumpdata',
            *BACKUP_MODELS,
            format='json',
            indent=2,
            stdout=string_buf
        )
        return string_buf.getvalue()

    @classmethod
    def export_json(cls) -> BytesIO:
        json_str = cls.export_json_string()
        return BytesIO(json_str.encode('utf-8'))

    @classmethod
    def export_media_zip(cls) -> BytesIO:
        zip_buffer = BytesIO()
        media_root = settings.MEDIA_ROOT

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for subdir in MEDIA_SUBDIRS:
                folder_path = os.path.join(media_root, subdir)
                if os.path.exists(folder_path):
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, media_root)
                            zf.write(full_path, arcname=rel_path)

        zip_buffer.seek(0)
        return zip_buffer

    @classmethod
    def export_full_backup_zip(cls) -> BytesIO:
        zip_buffer = BytesIO()
        media_root = settings.MEDIA_ROOT
        json_str = cls.export_json_string()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('data.json', json_str.encode('utf-8'))
            for subdir in MEDIA_SUBDIRS:
                folder_path = os.path.join(media_root, subdir)
                if os.path.exists(folder_path):
                    for root, _, files in os.walk(folder_path):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, media_root)
                            archive_path = os.path.join('media', rel_path)
                            zf.write(full_path, arcname=archive_path)

        zip_buffer.seek(0)
        return zip_buffer

    # =========================================================================
    # موتور ادغام هوشمند (Smart Merge & Upsert)
    # =========================================================================
    @classmethod
    def _find_existing_record(cls, model_label: str, model_cls, fields: dict):
        """
        جستجوی رکورد موجود بر اساس فیلدهای یکتا تا داده‌های قبلی حفظ شوند.
        """
        try:
            if model_label == 'icons.iconshortcut':
                return model_cls.objects.filter(title_icon=fields.get('title_icon')).first()

            if model_label == 'config.userlevel':
                return model_cls.objects.filter(title=fields.get('title')).first()

            if model_label == f'{APP_NAME}.province':
                return model_cls.objects.filter(
                    models.Q(slug=fields.get('slug')) | models.Q(name=fields.get('name'))
                ).first()

            if model_label == f'{APP_NAME}.city':
                return model_cls.objects.filter(
                    name=fields.get('name'),
                    province_id=fields.get('province')
                ).first()

            if model_label in [
                f'{APP_NAME}.hoteltype',
                f'{APP_NAME}.hoteltag',
                f'{APP_NAME}.facilities',
                f'{APP_NAME}.roomfacilities',
                f'{APP_NAME}.roomservice',
            ]:
                return model_cls.objects.filter(title=fields.get('title')).first()

            if model_label == f'{APP_NAME}.besthotels':
                return model_cls.objects.filter(title_logo=fields.get('title_logo')).first()

            if model_label == f'{APP_NAME}.hotel':
                slug = fields.get('slug')
                if slug:
                    return model_cls.objects.filter(slug=slug).first()
                return model_cls.objects.filter(
                    name=fields.get('name'),
                    city_id=fields.get('city')
                ).first()

            if model_label in [f'{APP_NAME}.seometa', f'{APP_NAME}.cancellationpenalty']:
                return model_cls.objects.filter(hotel_id=fields.get('hotel')).first()

            if model_label == f'{APP_NAME}.hotelgallery':
                return model_cls.objects.filter(
                    hotel_id=fields.get('hotel'),
                    title=fields.get('title')
                ).first()

            if model_label == f'{APP_NAME}.hotelgalleryimage':
                return model_cls.objects.filter(
                    gallery_id=fields.get('gallery'),
                    image=fields.get('image')
                ).first()

            if model_label == f'{APP_NAME}.nearbyplace':
                return model_cls.objects.filter(
                    hotel_id=fields.get('hotel'),
                    title=fields.get('title')
                ).first()

            if model_label == f'{APP_NAME}.hotelfaq':
                return model_cls.objects.filter(
                    hotel_id=fields.get('hotel'),
                    question=fields.get('question')
                ).first()

            if model_label == f'{APP_NAME}.hoteltagpublic':
                return model_cls.objects.filter(
                    hotel_id=fields.get('hotel'),
                    title=fields.get('title')
                ).first()

            if model_label == f'{APP_NAME}.room':
                return model_cls.objects.filter(
                    hotel_id=fields.get('hotel'),
                    title=fields.get('title')
                ).first()

            if model_label == f'{APP_NAME}.roomdateprice':
                return model_cls.objects.filter(
                    room_id=fields.get('room'),
                    start_date=fields.get('start_date'),
                    end_date=fields.get('end_date'),
                    user_level_id=fields.get('user_level')
                ).first()

            if model_label == f'{APP_NAME}.closeddate':
                return model_cls.objects.filter(
                    room_date_id=fields.get('room_date'),
                    date=fields.get('date'),
                    user_level_id=fields.get('user_level')
                ).first()

        except Exception:
            return None

        return None

    @classmethod
    def smart_restore_data(cls, raw_json_data) -> tuple[bool, str]:
        """
        ادغام بدون خطا:
        - رکوردهای تکراری حفظ می‌شوند
        - رکوردهای جدید اضافه می‌شوند
        - کلیدهای خارجی با نگاشت خودکار به درستی پیوند داده می‌شوند
        """
        if isinstance(raw_json_data, (bytes, str)):
            data_list = json.loads(raw_json_data)
        else:
            data_list = raw_json_data

        # جدول نگاشت: (model_label, old_pk) -> new_pk
        id_map = {}
        added_count = 0
        preserved_count = 0

        # برای اعمال روابط M2M بعد از ایجاد رکوردها
        deferred_m2m = []

        # مرتب‌سازی آیتم‌های JSON مطابق ترتیب دقیق BACKUP_MODELS
        order_index = {label.lower(): i for i, label in enumerate(BACKUP_MODELS)}
        sorted_data = sorted(
            data_list,
            key=lambda item: order_index.get(item.get('model', '').lower(), 999)
        )

        with transaction.atomic():
            for item in sorted_data:
                model_label = item.get('model', '').lower()
                old_pk = item.get('pk')
                fields_data = dict(item.get('fields', {}))

                try:
                    model_cls = apps.get_model(model_label)
                except LookupError:
                    continue

                # ۱. به‌روزرسانی کلیدهای خارجی (Foreign Keys) با شناسه‌های مپ شده
                for field in model_cls._meta.fields:
                    if field.is_relation and (field.many_to_one or field.one_to_one):
                        fk_name = field.name
                        old_fk_val = fields_data.get(fk_name)
                        if old_fk_val is not None:
                            target_label = field.related_model._meta.label_lower
                            new_fk_val = id_map.get((target_label, old_fk_val), old_fk_val)
                            fields_data[fk_name] = new_fk_val

                # ۲. استخراج موقت فیلدهای Many-to-Many
                item_m2m = {}
                for m2m_field in model_cls._meta.many_to_many:
                    if m2m_field.name in fields_data:
                        old_m2m_ids = fields_data.pop(m2m_field.name) or []
                        target_label = m2m_field.related_model._meta.label_lower
                        new_m2m_ids = [id_map.get((target_label, v), v) for v in old_m2m_ids]
                        item_m2m[m2m_field.name] = new_m2m_ids

                # ۳. بررسی وجود رکورد در دیتابیس فعلی
                existing_obj = cls._find_existing_record(model_label, model_cls, fields_data)

                if existing_obj:
                    # رکورد قبلی حفظ می‌شود
                    new_pk = existing_obj.pk
                    preserved_count += 1
                else:
                    # ۴. جلوگیری از تداخل فیلد order در صورت وجود
                    if model_label in ['icons.iconshortcut', f'{APP_NAME}.besthotels']:
                        curr_order = fields_data.get('order')
                        if curr_order is not None and model_cls.objects.filter(order=curr_order).exists():
                            max_order = model_cls.objects.aggregate(models.Max('order'))['order__max'] or 0
                            fields_data['order'] = max_order + 1

                    # ۵. ایجاد رکورد جدید (بدون تحمیل PK قدیمی تا دیتابیس ID تمیز صادر کند)
                    # اگر فیلد ID آزاد بود از همان استفاده می‌شود، در غیر این صورت اتوماتیک صادر می‌شود
                    if model_cls.objects.filter(pk=old_pk).exists():
                        new_instance = model_cls(**fields_data)
                    else:
                        new_instance = model_cls(pk=old_pk, **fields_data)

                    new_instance.save()
                    new_pk = new_instance.pk
                    added_count += 1
                    existing_obj = new_instance

                # ثبت در جدول نگاشت
                id_map[(model_label, old_pk)] = new_pk

                # ذخیره اطلاعات M2M برای اتصال
                if item_m2m and existing_obj:
                    deferred_m2m.append((existing_obj, item_m2m))

            # اعمال روابط ManyToMany
            for instance, m2m_dict in deferred_m2m:
                for m2m_attr, ids in m2m_dict.items():
                    try:
                        getattr(instance, m2m_attr).add(*ids)
                    except Exception:
                        pass

        msg = (
            f"عملیات با موفقیت انجام شد: "
            f"{added_count} مورد جدید به دیتابیس اضافه شد و "
            f"{preserved_count} مورد موجود قبلی بدون تداخل حفظ شدند."
        )
        return True, msg

    @classmethod
    def restore_from_zip(cls, uploaded_file) -> tuple[bool, str]:
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(uploaded_file, 'r') as zf:
                zf.extractall(temp_dir)

            # بازیابی عکس‌ها (فایل‌های جدید رونویسی یا اضافه می‌شوند)
            extracted_media_dir = os.path.join(temp_dir, 'media')
            media_root = settings.MEDIA_ROOT

            if os.path.exists(extracted_media_dir):
                for root, _, files in os.walk(extracted_media_dir):
                    for file in files:
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, extracted_media_dir)
                        dest_file = os.path.join(media_root, rel_path)

                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        shutil.copy2(src_file, dest_file)

            json_file_path = os.path.join(temp_dir, 'data.json')
            if not os.path.exists(json_file_path):
                return False, "فایل data.json در فایل ZIP یافت نشد!"

            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            return cls.smart_restore_data(json_data)

        except Exception as e:
            return False, f"خطا در بازگردانی: {str(e)}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def restore_from_json(cls, uploaded_file) -> tuple[bool, str]:
        try:
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            json_data = json.loads(content)
            return cls.smart_restore_data(json_data)
        except Exception as e:
            return False, f"خطا در تزریق JSON: {str(e)}"
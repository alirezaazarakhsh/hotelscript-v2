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

APP_NAME = 'reservation'

# ۱. مدل‌های پایه و آیکون‌ها
BASE_MODELS = [
    'icons.IconShortcut',
]

# ۲. تمام مدل‌های اپلیکیشن کانفیگ (به ترتیب وابستگی)
CONFIG_MODELS = [
    'config.UserLevel',
    'config.SiteConfig',
    'config.Page',
    'config.HeaderMenu',
    'config.QuickAccess',
    'config.Slide',
    'config.Statistic',
    'config.ChooseReason',
    'config.FAQ',
    'config.Service',
    'config.ContactInfo',
    'config.SocialMedia',
    'config.Banner',
    'config.EnamadLicense',
    'config.License',
    'config.Advantage',
    'config.FakeComment',
    'config.Rule',
    'config.ComingSoon',
    'config.Location',
    'config.LegalProfileSubmissionRule',
]

# ۳. مدل‌های رزرواسیون و هتل‌ها
RESERVATION_MODELS = [
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


class HotelBackupService:

    # =========================================================================
    # تعریف دسته‌بندی‌ها و پوشه‌های اختصاصی هر بخش
    # =========================================================================
    SECTIONS = {
        'hotels': {
            'title': 'هتل‌ها و رزرواسیون',
            'models': RESERVATION_MODELS + BASE_MODELS,
            'media': [
                'cities',
                'hotel_gallery',
                'room_images',
                'images',
                'shopping_centers',
                'signatures',
            ],
        },
        'config': {
            'title': 'تنظیمات و رابط کاربری',
            'models': CONFIG_MODELS + BASE_MODELS,
            'media': [
                'icons',
                'logos',
                'about_us',
                'banners',
                'slides',
                'enamad',
                'licenses',
                'images/config',
            ],
        },
        'blog': {
            'title': 'وبلاگ و مقالات',
            'models': ['blog'],  # به صورت پویا تمام مدل‌های اپلیکیشن blog را دریافت می‌کند
            'media': [
                'blog',
                'blogs',
                'blog_images',
                'articles',
                'posts',
                'images/blog',
            ],
        },
        'finance': {
            'title': 'مدارک و فیش‌های مالی',
            'models': [],
            'media': [
                'legal-profiles',
                'deposit_receipts',
                'subscription_receipts',
            ],
        },
    }

    @classmethod
    def get_all_media_folders(cls) -> list:
        """فهرست تمام پوشه‌های مجاز مدیا روی سرور بدون تکرار"""
        folders = set()
        for sec in cls.SECTIONS.values():
            folders.update(sec.get('media', []))
        return sorted(list(folders))

    @classmethod
    def get_active_models(cls, target_models: list = None) -> list:
        """بررسی و بازگرداندن مدل‌های معتبر و رجیستر شده در دیتابیس"""
        if target_models is None:
            models_to_check = list(BASE_MODELS) + list(CONFIG_MODELS) + list(RESERVATION_MODELS)
        else:
            models_to_check = list(target_models)

        # اگر در لیست، اپلیکیشن 'blog' بود، مدل‌های آن پویا کشف شوند
        if 'blog' in models_to_check or target_models is None:
            if 'blog' in models_to_check:
                models_to_check.remove('blog')
            if apps.is_installed('blog'):
                try:
                    for model in apps.get_app_config('blog').get_models():
                        if not model._meta.proxy:
                            lbl = f'blog.{model.__name__}'
                            if lbl not in models_to_check:
                                models_to_check.append(lbl)
                except Exception:
                    pass

        valid = []
        for m_str in models_to_check:
            try:
                app_label, model_name = m_str.split('.')
                m_cls = apps.get_model(app_label, model_name)
                if m_cls and not m_cls._meta.proxy:
                    valid.append(m_str)
            except (LookupError, ValueError):
                continue
        return valid

    # =========================================================================
    # توابع خروجی گرفتن (Export)
    # =========================================================================
    @classmethod
    def export_json_string(cls, target_models: list = None) -> str:
        """خروجی JSON برای مدل‌های داده‌شده یا همه مدل‌ها"""
        string_buf = StringIO()
        active = cls.get_active_models(target_models)
        if not active:
            return "[]"
        call_command(
            'dumpdata',
            *active,
            format='json',
            indent=2,
            stdout=string_buf
        )
        return string_buf.getvalue()

    @classmethod
    def export_json(cls, target_models: list = None) -> BytesIO:
        json_str = cls.export_json_string(target_models)
        return BytesIO(json_str.encode('utf-8'))

    @classmethod
    def export_media_zip(cls, folder_list: list = None) -> BytesIO:
        """فشرده‌سازی پوشه‌های مشخص‌شده یا تمامی پوشه‌های مدیا به صورت ZIP"""
        zip_buffer = BytesIO()
        media_root = settings.MEDIA_ROOT
        folders = folder_list if folder_list is not None else cls.get_all_media_folders()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for subdir in folders:
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
    def export_full_backup_zip(cls, section_key: str = None) -> BytesIO:
        """
        پکیج کامل شامل data.json و پوشه media
        (اگر section_key خالی باشد، کل سیستم؛ در غیر این صورت فقط آن دسته)
        """
        zip_buffer = BytesIO()
        media_root = settings.MEDIA_ROOT

        if section_key and section_key in cls.SECTIONS:
            sec_info = cls.SECTIONS[section_key]
            json_str = cls.export_json_string(sec_info.get('models', []))
            target_folders = sec_info.get('media', [])
        else:
            json_str = cls.export_json_string()
            target_folders = cls.get_all_media_folders()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('data.json', json_str.encode('utf-8'))
            for subdir in target_folders:
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
    # موتور ادغام هوشمند همگانی (Universal Smart Merge & Upsert)
    # =========================================================================
    @classmethod
    def _find_existing_record(cls, model_label: str, model_cls, fields: dict):
        """
        جستجوی رکورد موجود در دیتابیس بر اساس کلیدهای یکتا تا داده‌های قبلی حفظ شوند
        """
        try:
            # ۱. تطبیق شرط‌های اختصاصی مدل‌های هتل و آیکون‌ها
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

            if model_label == f'{APP_NAME}.hotel':
                slug = fields.get('slug')
                if slug:
                    return model_cls.objects.filter(slug=slug).first()
                return model_cls.objects.filter(name=fields.get('name'), city_id=fields.get('city')).first()

            if model_label in [f'{APP_NAME}.seometa', f'{APP_NAME}.cancellationpenalty']:
                return model_cls.objects.filter(hotel_id=fields.get('hotel')).first()

            if model_label == f'{APP_NAME}.hotelgallery':
                return model_cls.objects.filter(hotel_id=fields.get('hotel'), title=fields.get('title')).first()

            if model_label == f'{APP_NAME}.hotelgalleryimage':
                return model_cls.objects.filter(gallery_id=fields.get('gallery'), image=fields.get('image')).first()

            if model_label == f'{APP_NAME}.nearbyplace':
                return model_cls.objects.filter(hotel_id=fields.get('hotel'), title=fields.get('title')).first()

            if model_label == f'{APP_NAME}.hotelfaq':
                return model_cls.objects.filter(hotel_id=fields.get('hotel'), question=fields.get('question')).first()

            if model_label == f'{APP_NAME}.hoteltagpublic':
                return model_cls.objects.filter(hotel_id=fields.get('hotel'), title=fields.get('title')).first()

            if model_label == f'{APP_NAME}.room':
                return model_cls.objects.filter(hotel_id=fields.get('hotel'), title=fields.get('title')).first()

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

            # ۲. تطبیق هوشمند عمومی بر اساس unique=True (برای blog و config و...)
            unique_fields = [f.name for f in model_cls._meta.fields if f.unique and not f.primary_key]
            for uf in unique_fields:
                val = fields.get(uf)
                if val not in [None, '']:
                    existing = model_cls.objects.filter(**{uf: val}).first()
                    if existing:
                        return existing

            # ۳. بررسی قیود unique_together
            if model_cls._meta.unique_together:
                for ut in model_cls._meta.unique_together:
                    if all(fields.get(f) is not None for f in ut):
                        q_dict = {f: fields.get(f) for f in ut}
                        existing = model_cls.objects.filter(**q_dict).first()
                        if existing:
                            return existing

            # ۴. بررسی UniqueConstraint
            for constraint in model_cls._meta.constraints:
                if isinstance(constraint, models.UniqueConstraint) and constraint.fields:
                    if all(fields.get(f) is not None for f in constraint.fields):
                        q_dict = {f: fields.get(f) for f in constraint.fields}
                        existing = model_cls.objects.filter(**q_dict).first()
                        if existing:
                            return existing

            # ۵. فیلدهای عمومی نام‌گذاری (slug, title, name, path)
            for common_key in ['slug', 'title', 'name', 'path', 'title_logo', 'title_icon', 'code']:
                if common_key in fields and fields.get(common_key) not in [None, '']:
                    if hasattr(model_cls, common_key):
                        try:
                            existing = model_cls.objects.filter(**{common_key: fields[common_key]}).first()
                            if existing:
                                return existing
                        except Exception:
                            pass

        except Exception:
            return None

        return None

    @classmethod
    def smart_restore_data(cls, raw_json_data) -> tuple[bool, str]:
        """
        ادغام و بازگردانی هوشمند داده‌های JSON:
        - رکوردهای تکراری بدون خطا حفظ می‌شوند
        - رکوردهای جدید اضافه می‌شوند
        - کلیدهای خارجی با نگاشت خودکار متصل می‌شوند
        """
        if isinstance(raw_json_data, (bytes, str)):
            data_list = json.loads(raw_json_data)
        else:
            data_list = raw_json_data

        id_map = {}
        added_count = 0
        preserved_count = 0
        deferred_m2m = []

        all_models = cls.get_active_models()
        order_index = {label.lower(): i for i, label in enumerate(all_models)}

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

                # ۱. به‌روزرسانی کلیدهای خارجی با شناسه‌های مپ‌شده
                for field in model_cls._meta.fields:
                    if field.is_relation and (field.many_to_one or field.one_to_one):
                        fk_name = field.name
                        old_fk_val = fields_data.get(fk_name)
                        if old_fk_val is not None:
                            target_label = field.related_model._meta.label_lower
                            new_fk_val = id_map.get((target_label, old_fk_val), old_fk_val)
                            fields_data[fk_name] = new_fk_val

                # ۲. استخراج موقت داده‌های Many-to-Many
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
                    new_pk = existing_obj.pk
                    preserved_count += 1
                else:
                    # رفع تداخل شماره ترتیب (order)
                    curr_order = fields_data.get('order')
                    if curr_order is not None and hasattr(model_cls, 'order'):
                        try:
                            if model_cls.objects.filter(order=curr_order).exists():
                                max_order = model_cls.objects.aggregate(models.Max('order'))['order__max'] or 0
                                fields_data['order'] = max_order + 1
                        except Exception:
                            pass

                    # ایجاد رکورد جدید با شناسه آزاد
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

                if item_m2m and existing_obj:
                    deferred_m2m.append((existing_obj, item_m2m))

            # اعمال روابط Many-to-Many
            for instance, m2m_dict in deferred_m2m:
                for m2m_attr, ids in m2m_dict.items():
                    try:
                        getattr(instance, m2m_attr).add(*ids)
                    except Exception:
                        pass

        msg = (
            f"عملیات با موفقیت انجام شد: "
            f"{added_count} مورد جدید اضافه شد و "
            f"{preserved_count} مورد موجود قبلی بدون تداخل حفظ گردید."
        )
        return True, msg

    @classmethod
    def restore_from_zip(cls, uploaded_file) -> tuple[bool, str]:
        """پشتیبانی از ریستور فایل ZIP سراسری، دسته‌ای یا تک‌پوشه‌ای"""
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(uploaded_file, 'r') as zf:
                zf.extractall(temp_dir)

            media_root = settings.MEDIA_ROOT
            os.makedirs(media_root, exist_ok=True)

            # ۱. استخراج عکس‌ها
            extracted_media_dir = os.path.join(temp_dir, 'media')
            source_dir = extracted_media_dir if os.path.exists(extracted_media_dir) else temp_dir

            for root, _, files in os.walk(source_dir):
                for file in files:
                    if file == 'data.json' and root == source_dir:
                        continue
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, source_dir)
                    dest_file = os.path.join(media_root, rel_path)

                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(src_file, dest_file)

            # ۲. تزریق اطلاعات JSON در صورت وجود data.json
            json_file_path = os.path.join(temp_dir, 'data.json')
            if os.path.exists(json_file_path):
                with open(json_file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                return cls.smart_restore_data(json_data)

            return True, "فایل‌های مدیا با موفقیت در پوشه رسانه سرور جای‌گذاری شدند."

        except Exception as e:
            return False, f"خطا در بازگردانی فایل ZIP: {str(e)}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def restore_from_json(cls, uploaded_file) -> tuple[bool, str]:
        """بازگردانی فقط فایل JSON به دیتابیس"""
        try:
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            json_data = json.loads(content)
            return cls.smart_restore_data(json_data)
        except Exception as e:
            return False, f"خطا در تزریق JSON: {str(e)}"
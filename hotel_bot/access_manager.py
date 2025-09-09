import os
import json
from hotel_bot.config import ADMINS_FILE, SUPER_ADMINS


class AccessManager:
    _cached_data = None

    @staticmethod
    def load_data():
        if AccessManager._cached_data is not None:
            return AccessManager._cached_data.copy()

        try:
            if os.path.exists(ADMINS_FILE):
                with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # تبدیل مقادیر groups به set
                    for gname in data.get('groups', {}):
                        data['groups'][gname] = set(data['groups'].get(gname, []))
                    # اطمینان از وجود profiles
                    data['profiles'] = data.get('profiles', {})
                    AccessManager._cached_data = data.copy()
                    return data.copy()
            else:
                default_data = {'admins': {}, 'groups': {}, 'profiles': {}}
                AccessManager._cached_data = default_data.copy()
                return default_data.copy()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in {ADMINS_FILE}: {str(e)}")
            default_data = {'admins': {}, 'groups': {}, 'profiles': {}}
            AccessManager._cached_data = default_data.copy()
            return default_data.copy()
        except Exception as e:
            print(f"Error loading {ADMINS_FILE}: {str(e)}")
            default_data = {'admins': {}, 'groups': {}, 'profiles': {}}
            AccessManager._cached_data = default_data.copy()
            return default_data.copy()

    @staticmethod
    def save_data(data):
        try:
            # ایجاد کپی برای جلوگیری از تغییر مستقیم داده‌های اصلی
            saveable = {
                'admins': data.get('admins', {}),
                'groups': {gname: list(perms) for gname, perms in data.get('groups', {}).items()},
                'profiles': data.get('profiles', {})
            }
            with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
                json.dump(saveable, f, ensure_ascii=False, indent=4)
            # به‌روزرسانی کش بعد از ذخیره موفق
            AccessManager._cached_data = data.copy()
        except Exception as e:
            print(f"Error saving {ADMINS_FILE}: {str(e)}")

    @staticmethod
    def is_allowed(user_id, permission=None):
        if user_id in SUPER_ADMINS:
            return True
        str_uid = str(user_id)
        data = AccessManager.load_data()
        admins = data.get('admins', {})
        if str_uid not in admins:
            return False
        group = admins.get(str_uid)
        if not group or group not in data.get('groups', {}):
            return False
        if permission is None:
            return True
        return permission in data.get('groups', {}).get(group, set())

    @staticmethod
    def clear_cache():
        AccessManager._cached_data = None

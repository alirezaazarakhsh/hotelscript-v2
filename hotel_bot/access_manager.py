import os
import json
from config import ADMINS_FILE, SUPER_ADMINS

class AccessManager:
    @staticmethod
    def load_data():
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, 'r') as f:
                data = json.load(f)
                # تبدیل لیست‌های مجوزها به مجموعه (set) برای عملکرد بهتر
                for uid in data.get('admins', {}):
                    data['admins'][uid] = set(data['admins'][uid])
                for gname in data.get('groups', {}):
                    data['groups'][gname] = set(data['groups'][gname])
                return data
        return {'admins': {}, 'groups': {}}

    @staticmethod
    def save_data(data):
        # تبدیل مجموعه‌ها به لیست برای ذخیره‌سازی در JSON
        saveable = {
            'admins': {uid: list(perms) for uid, perms in data['admins'].items()},
            'groups': {gname: list(perms) for gname, perms in data['groups'].items()}
        }
        with open(ADMINS_FILE, 'w') as f:
            json.dump(saveable, f)

    @staticmethod
    def is_allowed(user_id, permission=None):
        if user_id in SUPER_ADMINS:
            return True
        str_uid = str(user_id)
        data = AccessManager.load_data()
        admins = data['admins']
        if str_uid not in admins:
            return False
        if permission is None:
            return bool(admins[str_uid])  # اگر حداقل یک مجوز داشته باشد
        return permission in admins[str_uid]
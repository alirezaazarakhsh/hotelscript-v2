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
                for gname in data.get('groups', {}):
                    data['groups'][gname] = set(data['groups'][gname])
                # admins حالا {uid: group_name} است، نیازی به تغییر نیست
                return data
        return {'admins': {}, 'groups': {}}

    @staticmethod
    def save_data(data):
        # تبدیل مجموعه‌ها به لیست برای ذخیره‌سازی در JSON
        saveable = {
            'admins': data['admins'],  # {uid: group_name}
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
        group = admins[str_uid]
        if group not in data['groups']:
            return False
        if permission is None:
            return True  # اگر گروه اختصاص یافته، مجاز است (حتی اگر مجوزها خالی باشد)
        return permission in data['groups'][group]
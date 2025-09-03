import os
import json
from config import ADMINS_FILE, SUPER_ADMINS

class AccessManager:
    @staticmethod
    def load_data():
        try:
            if os.path.exists(ADMINS_FILE):
                with open(ADMINS_FILE, 'r') as f:
                    data = json.load(f)
                    for gname in data.get('groups', {}):
                        data['groups'][gname] = set(data['groups'][gname])
                    return data
            return {'admins': {}, 'groups': {}}
        except Exception as e:
            print(f"Error loading ADMINS_FILE: {str(e)}")
            return {'admins': {}, 'groups': {}}

    @staticmethod
    def save_data(data):
        try:
            saveable = {
                'admins': data['admins'],
                'groups': {gname: list(perms) for gname, perms in data['groups'].items()}
            }
            with open(ADMINS_FILE, 'w') as f:
                json.dump(saveable, f)
        except Exception as e:
            print(f"Error saving ADMINS_FILE: {str(e)}")

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
            return True
        return permission in data['groups'][group]
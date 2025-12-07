import os
import json
from hotel_bot.config import ADMINS_FILE, SUPER_ADMINS


class AccessManager:
    _cached_data = None

    @staticmethod
    def load_data():
        # Clear cache to ensure fresh data loading
        AccessManager._cached_data = None
        
        try:
            if os.path.exists(ADMINS_FILE):
                with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # تبدیل مقادیر groups به set
                    for gname in data.get('groups', {}):
                        group_data = data['groups'][gname]
                        if isinstance(group_data, (list, set)):
                            data['groups'][gname] = set(group_data)
                        elif isinstance(group_data, dict):
                            # If it's a dict, extract permissions
                            perms = group_data.get('permissions', [])
                            if isinstance(perms, (list, set)):
                                data['groups'][gname] = set(perms)
                            else:
                                data['groups'][gname] = set()
                        else:
                            data['groups'][gname] = set()
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
                'admins': {},
                'groups': {gname: list(perms) for gname, perms in data.get('groups', {}).items()},
                'profiles': data.get('profiles', {})
            }
            for uid, admin_info in data.get('admins', {}).items():
                if isinstance(admin_info, str):
                    saveable['admins'][uid] = {'group': admin_info}
                else:
                    saveable['admins'][uid] = admin_info
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
        packages = data.get('subscription_packages', {})
        
        if str_uid not in admins:
            return False
        
        admin_data = admins.get(str_uid, {})
        if isinstance(admin_data, str):
            # Old format, convert to dict
            admin_data = {'group': admin_data}
            admins[str_uid] = admin_data
        
        # Check license expiry
        license_expiry = admin_data.get('license_expiry')
        if license_expiry:
            from datetime import datetime
            try:
                expiry = datetime.fromisoformat(license_expiry)
                if datetime.now() > expiry:
                    return False
            except ValueError:
                pass  # Invalid date, allow access
        
        # Check subscription package permissions
        subscription_package = admin_data.get('subscription_package')
        if subscription_package and subscription_package in packages:
            package = packages[subscription_package]
            package_group = package.get('group')
            if package_group and package_group in data.get('groups', {}):
                # Check if subscription is active
                subscription_expiry = admin_data.get('subscription_expiry')
                if subscription_expiry:
                    from datetime import datetime
                    try:
                        expiry = datetime.fromisoformat(subscription_expiry)
                        if datetime.now() > expiry:
                            # Subscription expired, fall back to regular group
                            pass
                        else:
                            # Subscription active, use package group permissions
                            if permission is None:
                                return True
                            return permission in data.get('groups', {}).get(package_group, set())
                    except ValueError:
                        pass  # Invalid date, fall back to regular group
        
        # Fall back to regular group permissions
        group = admin_data.get('group')
        if not group or group not in data.get('groups', {}):
            return False
        if permission is None:
            return True
        return permission in data.get('groups', {}).get(group, set())

    @staticmethod
    def clear_cache():
        AccessManager._cached_data = None

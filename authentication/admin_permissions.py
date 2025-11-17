from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from authentication.models import Admin, BaseUser


class AdminPermissionManager(admin.ModelAdmin):
    """
    کلاس مدیریت دسترسی‌های ادمین‌ها
    """
    change_list_template = 'admin/authentication/admin_permissions.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'manage-permissions/<int:admin_id>/',
                self.admin_site.admin_view(self.manage_permissions),
                name='manage_admin_permissions',
            ),
            path(
                'assign-group/<int:admin_id>/',
                self.admin_site.admin_view(self.assign_group),
                name='assign_admin_group',
            ),
        ]
        return custom_urls + urls
    
    def changelist_view(self, request, extra_context=None):
        """نمایش لیست ادمین‌ها با دسترسی‌هایشان"""
        admins = Admin.objects.select_related('base_user').prefetch_related(
            'base_user__groups',
            'base_user__user_permissions'
        ).all()
        
        admin_data = []
        for admin in admins:
            admin_data.append({
                'admin': admin,
                'groups': admin.base_user.groups.all(),
                'permissions_count': admin.base_user.user_permissions.count(),
            })
        
        context = {
            'admins': admin_data,
            'title': 'مدیریت دسترسی‌های ادمین‌ها',
            **self.admin_site.each_context(request),
        }
        context.update(extra_context or {})
        return render(request, 'admin/authentication/admin_permissions.html', context)
    
    def manage_permissions(self, request, admin_id):
        """مدیریت دسترسی‌های یک ادمین خاص"""
        admin = get_object_or_404(Admin, id=admin_id)
        
        if request.method == 'POST':
            # دریافت گروه‌ها و دسترسی‌های انتخاب شده
            selected_groups = request.POST.getlist('groups')
            selected_permissions = request.POST.getlist('permissions')
            
            # تنظیم گروه‌ها
            admin.base_user.groups.set(selected_groups)
            
            # تنظیم دسترسی‌ها
            admin.base_user.user_permissions.set(selected_permissions)
            
            messages.success(request, f'دسترسی‌های ادمین {admin} با موفقیت به‌روزرسانی شد.')
            return redirect('admin:authentication_admin_changelist')
        
        # دریافت تمام گروه‌ها و دسترسی‌ها
        all_groups = Group.objects.all()
        
        # گروه‌بندی دسترسی‌ها بر اساس اپلیکیشن
        permissions_by_app = {}
        for permission in Permission.objects.select_related('content_type').all():
            app_label = permission.content_type.app_label
            if app_label not in permissions_by_app:
                permissions_by_app[app_label] = []
            permissions_by_app[app_label].append(permission)
        
        context = {
            'admin': admin,
            'all_groups': all_groups,
            'permissions_by_app': permissions_by_app,
            'admin_groups': admin.base_user.groups.all(),
            'admin_permissions': admin.base_user.user_permissions.all(),
            'title': f'مدیریت دسترسی‌های {admin}',
            **self.admin_site.each_context(request),
        }
        return render(request, 'admin/authentication/manage_permissions.html', context)
    
    def assign_group(self, request, admin_id):
        """اختصاص سریع گروه به ادمین"""
        admin = get_object_or_404(Admin, id=admin_id)
        
        if request.method == 'POST':
            group_id = request.POST.get('group_id')
            if group_id:
                group = get_object_or_404(Group, id=group_id)
                admin.base_user.groups.add(group)
                messages.success(request, f'گروه {group.name} به ادمین {admin} اختصاص داده شد.')
        
        return redirect('admin:authentication_admin_changelist')

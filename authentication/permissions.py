from rest_framework.permissions import BasePermission

class IsJuridicalProfileDocumentOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.profile.natural_profile.base_user == request.user
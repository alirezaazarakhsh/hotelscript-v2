from rest_framework import generics, permissions
from .models import FavoriteCollection, Favorite
from .serializers import FavoriteCollectionSerializer, FavoriteSerializer


# ------------------- FavoriteCollection Views -------------------

class FavoriteCollectionListCreateView(generics.ListCreateAPIView):
    """
    📌 ویو برای مشاهده لیست لیست‌های علاقمندی و ایجاد یک لیست جدید.

    - متد GET: لیست همه لیست‌های علاقمندی کاربر وارد شده را برمی‌گرداند.
    - متد POST: یک لیست علاقمندی جدید برای کاربر ایجاد می‌کند.
    """
    serializer_class = FavoriteCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteCollectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    📌 ویو برای مشاهده، ویرایش و حذف یک لیست علاقمندی خاص.

    - متد GET: نمایش جزئیات یک لیست خاص.
    - متد PUT/PATCH: ویرایش اطلاعات لیست.
    - متد DELETE: حذف لیست.
    """
    serializer_class = FavoriteCollectionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FavoriteCollection.objects.filter(user=self.request.user)


# ------------------- Favorite Views -------------------

class FavoriteListCreateView(generics.ListCreateAPIView):
    """
    📌 ویو برای مشاهده و اضافه کردن آیتم به لیست علاقمندی‌ها.

    - متد GET: نمایش همه آیتم‌های داخل یک لیست علاقمندی مشخص.
    - متد POST: اضافه کردن یک آیتم جدید به لیست علاقمندی.
    """
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        list_id = self.kwargs.get('list_id')
        return Favorite.objects.filter(list__id=list_id, list__user=self.request.user)

    def perform_create(self, serializer):
        list_id = self.kwargs.get('list_id')
        favorite_list = FavoriteCollection.objects.get(id=list_id, user=self.request.user)
        serializer.save(list=favorite_list)


class FavoriteDetailView(generics.RetrieveDestroyAPIView):
    """
    📌 ویو برای مشاهده جزئیات یا حذف یک آیتم علاقمندی.

    - متد GET: نمایش جزئیات آیتم.
    - متد DELETE: حذف آیتم از لیست علاقمندی.
    """
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(list__user=self.request.user)

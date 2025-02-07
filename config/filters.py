from rest_framework.filters import BaseFilterBackend

class PageFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        page = request.query_params.get('page', None)
        if page is not None:
            return queryset.filter(page__page=page)

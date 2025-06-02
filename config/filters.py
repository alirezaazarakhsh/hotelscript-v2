from rest_framework.filters import BaseFilterBackend

class PageFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        page_id = request.query_params.get('page')
        if page_id:
            return queryset.filter(page__id=page_id)
        return queryset

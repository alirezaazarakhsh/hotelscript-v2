from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class Paginator(PageNumberPagination):
    page_query_param = 'p'

    def get_paginated_response(self, data):
        return Response(data)

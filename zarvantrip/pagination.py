from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class Paginator(PageNumberPagination):
    page_query_param = 'p'

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })
        
        
class FacilitiesPaginator(PageNumberPagination):
    page_query_param = 'p'  

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })


class RoomFacilitiesPaginator(PageNumberPagination):
    page_query_param = 'p'  

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'results': data
        })
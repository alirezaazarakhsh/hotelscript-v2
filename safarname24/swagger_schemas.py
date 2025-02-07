from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg import openapi
from .pagination import Paginator

class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_parameters(self):
        parameters = super().get_parameters()
        paginator = self.view.paginator

        if paginator and isinstance(paginator, Paginator):
            page_parameter = openapi.Parameter(
                name='p',
                in_=openapi.IN_QUERY,
                description='Page number',
                type=openapi.TYPE_INTEGER,
                required=False,
            )
            parameters.append(page_parameter)

        return parameters

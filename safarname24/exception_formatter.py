from drf_standardized_errors.formatter import ExceptionFormatter
from drf_standardized_errors.types import ErrorResponse
from django.conf import settings

class ExceptionFormatter(ExceptionFormatter):
    def format_error_response(self, error_response: ErrorResponse):
        error = error_response.errors[0]
        
        if settings.DEBUG:
            return {
                "message": error.detail,
                "errors": [{
                    "field": error["attr"],
                    "message": error["detail"],
                } for error in super().format_error_response(error_response)["errors"]],
                "default_error": super().format_error_response(error_response),
            }

        return {
            "message": error.detail,
        }

from rest_framework.renderers import JSONRenderer


class ResponseRenderer(JSONRenderer):

    def render(
        self,
        data,
        accepted_media_type=None,
        renderer_context=None
    ):
        response = None

        if renderer_context:
            response = renderer_context.get("response")

        response_dict = {
            "message": "",
            "data": {},
            "success": True,
        }

        if response is not None and response.status_code >= 400:
            response_dict["success"] = False

            if isinstance(data, dict):
                payload = data.copy()

                error_message = payload.pop(
                    "detail",
                    "An error occurred."
                )

                response_dict["message"] = error_message
                response_dict["data"] = payload
            else:
                response_dict["message"] = "An error occurred."
                response_dict["data"] = data if data is not None else {}

        else:
            response_dict["data"] = data if data is not None else {}

        # استفاده از Encoder اصلی DRF برای پشتیبانی از Decimal،
        # datetime، date، UUID و سایر انواع داده
        return super().render(
            response_dict,
            accepted_media_type,
            renderer_context
        )

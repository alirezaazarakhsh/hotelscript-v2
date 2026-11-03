from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import renderers
import json

class ResponseRenderer(renderers.JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        json_string = ""

        if renderer_context and 'response' in renderer_context:
            response = renderer_context['response']

            # اگر درخواست با خطا مواجه شده باشد (400 به بالا)، بسته‌بندی پیام خطا انجام شود
            if response.status_code >= 400:
                response_dict = {
                    "message": "An error occurred.",
                    "data": {},
                    "success": False,
                }

                if isinstance(data, dict):
                    error_message = data.get("detail", "An error occurred.")
                    response_dict["message"] = error_message
                    data_copy = data.copy()
                    data_copy.pop("detail", None)
                    response_dict["data"] = data_copy
                else:
                    response_dict["data"] = data

                json_string = json.dumps(response_dict, cls=DjangoJSONEncoder)
            
            # ✅ در حالت موفق (200)، دیتا مستقیماً ارسال می‌شود تا لیست‌ها تبدیل به آبجکت نشوند و e.map کار کند
            else:
                json_string = json.dumps(data, cls=DjangoJSONEncoder)
        else:
            json_string = json.dumps(data, cls=DjangoJSONEncoder)

        if isinstance(json_string, str):
            json_bytes = json_string.encode('utf-8')
        else:
            json_bytes = json_string

        if renderer_context and 'response' in renderer_context:
            renderer_context['response']['Content-Type'] = 'application/json; charset=utf-8'

        return json_bytes
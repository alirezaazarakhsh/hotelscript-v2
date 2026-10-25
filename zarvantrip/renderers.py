from rest_framework import renderers
import json

class ResponseRenderer(renderers.JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response_dict = {
            "message": "",
            "data": {},
            "success": True,
        }

        if renderer_context and 'response' in renderer_context:
            response = renderer_context['response']
            if response.status_code >= 400:
                response_dict["success"] = False

                error_message = data.get("detail", "An error occurred.")
                response_dict["message"] = error_message

                if isinstance(data, dict) and "detail" in data:
                    data.pop("detail")

                response_dict["data"] = data
            else:
                response_dict["data"] = data

        json_string = json.dumps(response_dict)

        if isinstance(json_string, str):
            json_bytes = json_string.encode('utf-8')
        else:
            json_bytes = json_string

        if renderer_context and 'response' in renderer_context:
            renderer_context['response']['Content-Type'] = 'application/json; charset=utf-8'

        return json_bytes

import json
import logging

logger = logging.getLogger(__name__)


class CopilotStudioIDFix:
    """
    ASGI middleware that fixes JSON-RPC ID type mismatches for Microsoft Copilot Studio.
    Copilot Studio may send a string ID but expect an integer ID back in the response,
    or vice-versa. This middleware intercepts the request to check the ID type and
    buffers the response to ensure the response ID type matches the request ID type.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        # Request state
        request_id_is_string = False
        request_id_value = None

        # Buffer the entire request body
        buffered_messages = []
        request_body = b""
        more_body = True

        while more_body:
            message = await receive()
            buffered_messages.append(message)
            if message["type"] == "http.request":
                request_body += message.get("body", b"")
                more_body = message.get("more_body", False)

        # Parse request to check ID type
        if request_body:
            try:
                data = json.loads(request_body)
                request_id = data.get("id")
                if request_id is not None:
                    request_id_value = str(request_id)
                    request_id_is_string = isinstance(request_id, str)
            except json.JSONDecodeError:
                logger.warning("Could not parse request body as JSON.")

        # Replay the request messages for the app
        message_idx = 0

        async def receive_replay():
            nonlocal message_idx
            if message_idx < len(buffered_messages):
                msg = buffered_messages[message_idx]
                message_idx += 1
                return msg
            return await receive()

        # Response state
        response_body_chunks = []
        response_headers = []
        response_status = 200

        async def send_wrapper(message):
            nonlocal response_status, response_headers

            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = list(message.get("headers", []))

            elif message["type"] == "http.response.body":
                response_body_chunks.append(message.get("body", b""))

                if not message.get("more_body", False):
                    # Finalize and send the complete response
                    full_body = b"".join(response_body_chunks)

                    # Fix ID type if needed
                    if request_id_value and full_body:
                        try:
                            data = json.loads(full_body)
                            if "id" in data and str(data["id"]) == request_id_value:
                                if request_id_is_string and not isinstance(
                                    data["id"], str
                                ):
                                    logger.info(
                                        f"Copilot ID Fix: Converting response ID {data['id']} to string."
                                    )
                                    data["id"] = str(data["id"])
                                    full_body = json.dumps(data).encode("utf-8")
                                elif not request_id_is_string and isinstance(
                                    data["id"], str
                                ):
                                    logger.info(
                                        f"Copilot ID Fix: Converting response ID '{data['id']}' to integer."
                                    )
                                    data["id"] = int(data["id"])
                                    full_body = json.dumps(data).encode("utf-8")
                        except (json.JSONDecodeError, ValueError):
                            pass

                    # Update content-length
                    final_headers = []
                    for name, value in response_headers:
                        if name.lower() == b"content-length":
                            value = str(len(full_body)).encode()
                        final_headers.append((name, value))

                    await send(
                        {
                            "type": "http.response.start",
                            "status": response_status,
                            "headers": final_headers,
                        }
                    )
                    await send(
                        {
                            "type": "http.response.body",
                            "body": full_body,
                            "more_body": False,
                        }
                    )
            else:
                await send(message)

        await self.app(scope, receive_replay, send_wrapper)

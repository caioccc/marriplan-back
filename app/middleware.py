class AddKeepAliveHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"connection"] = b"keep-alive"
                message["headers"] = [(k, v) for k, v in headers.items()]
            await send(message)

        await self.app(scope, receive, send_wrapper)
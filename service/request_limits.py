"""Bound JSON request memory before FastAPI parses or authenticates the body."""
from starlette.responses import JSONResponse


class RequestSizeLimit:
    def __init__(self, app, max_bytes=34 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope.get('method') not in {'POST', 'PUT', 'PATCH'}:
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > self.max_bytes:
                return await JSONResponse({'detail':'request body exceeds the supported size'}, status_code=413)(scope, receive, send)
            messages.append(message)
            if not message.get('more_body', False):
                break
        position = 0
        async def replay():
            nonlocal position
            if position < len(messages):
                item = messages[position]
                position += 1
                return item
            return await receive()
        return await self.app(scope, replay, send)

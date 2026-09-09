import asyncio

from service.request_limits import RequestSizeLimit


def test_chunked_body_is_rejected_before_application_parsing():
    reached = []
    sent = []
    chunks = iter([{'type':'http.request','body':b'123','more_body':True},
                   {'type':'http.request','body':b'456','more_body':False}])
    async def receive(): return next(chunks)
    async def send(message): sent.append(message)
    async def app(*args): reached.append(True)
    asyncio.run(RequestSizeLimit(app, max_bytes=5)({'type':'http','method':'POST'}, receive, send))
    assert not reached
    assert sent[0]['status'] == 413


def test_bounded_body_reaches_signature_verification_unchanged():
    bodies = []
    chunks = iter([{'type':'http.request','body':b'{"a":','more_body':True},
                   {'type':'http.request','body':b'1}','more_body':False}])
    async def receive(): return next(chunks)
    async def send(message): pass
    async def app(scope, receive, send):
        while True:
            message = await receive()
            bodies.append(message['body'])
            if not message.get('more_body'): break
    asyncio.run(RequestSizeLimit(app, max_bytes=10)({'type':'http','method':'POST'}, receive, send))
    assert b''.join(bodies) == b'{"a":1}'

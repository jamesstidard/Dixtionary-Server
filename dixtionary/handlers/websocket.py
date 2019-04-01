

async def websocket_handler(request, ws):
    await request.app.subscription_server.handle(ws)
    return ws

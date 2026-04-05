from integrations.grpc.client import grpc_client


async def on_startup():
    from resources.managers.ws.manager import chat_ws_manager
    await grpc_client.connect()
    await chat_ws_manager.start()


async def on_shutdown():
    from resources.managers.ws.manager import chat_ws_manager
    await grpc_client.close()
    await chat_ws_manager.stop()

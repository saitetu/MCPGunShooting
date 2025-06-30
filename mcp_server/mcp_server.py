import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.types import Tool
from ble_control import send_set_command, send_target_and_wait_hit, show_message_window

server = Server("RollerPIDControl", version="0.1")

@server.list_tools()
async def list_tools():
    return [
        # Tool(
        #     name="set",
        #     description="BLEデバイスに'set'コマンドを送信します",
        #     inputSchema={"type": "object", "properties": {}, "required": []},
        #     outputSchema={"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]},
        # ),
        Tool(
            name="target",
            description="BLEデバイスに'target'コマンドを送信し、10秒間notifyでhitを待ち、ヒットIDと秒数を返します",
            inputSchema={"type": "object", "properties": {}, "required": []},
            outputSchema={
                "type": "object",
                "properties": {
                    "hit_id": {"type": "string", "description": "ヒットしたID (例: hit_64, hit_63)"},
                    "elapsed_sec": {"type": "number", "description": "targetモードからヒットまでの秒数"}
                },
                "required": ["hit_id", "elapsed_sec"]
            },
        ),
        Tool(
            name="show_message",
            description="指定した文字列を別ウィンドウで表示します",
            inputSchema={"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]},
            outputSchema={"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]},
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    # if name == "set":
    #     result = await send_set_command()
    #     return {"result": result}
    # el
    if name == "target":
        result = await send_target_and_wait_hit()
        return result
    elif name == "show_message":
        message = arguments.get("message", "")
        status = await show_message_window(message)
        return {"status": status}

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="RollerPIDControl",
                server_version="0.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main()) 
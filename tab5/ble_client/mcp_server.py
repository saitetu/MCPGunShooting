import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.types import Tool
from ble_control import send_set_command, send_target_and_wait_hit

server = Server("RollerPIDControl", version="0.1")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="set",
            description="BLEデバイスに'set'コマンドを送信します",
            inputSchema={"type": "object", "properties": {}, "required": []},
            outputSchema={"type": "object", "properties": {"result": {"type": "string"}}, "required": ["result"]},
        ),
        Tool(
            name="target",
            description="BLEデバイスに'target'コマンドを送信し、10秒間notifyでhitを待ちます",
            inputSchema={"type": "object", "properties": {}, "required": []},
            outputSchema={"type": "object", "properties": {"hit": {"type": "string"}}, "required": ["hit"]},
        ),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "set":
        result = await send_set_command()
        return {"result": result}
    elif name == "target":
        hit = await send_target_and_wait_hit()
        return {"hit": hit}

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
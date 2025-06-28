import asyncio
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "E16CE87C-F8BE-4FC7-89EB-8EF9C55A08D0"
CHARACTERISTIC_UUID = "160A9096-C252-4C4F-A52D-6B013050EF93"

def notification_handler_factory(hit_result_container):
    def handler(sender, data):
        hit_result_container["hit"] = data.decode()
        print(f"\nNotify受信: {data.decode()}")
    return handler

async def async_input(prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

async def find_target_device():
    print("スキャン中...")
    devices = await BleakScanner.discover()
    for d in devices:
        print(f"見つかったデバイス: {d.name}, {d.address}")
        if d.name == "RollerPIDControl":
            return d
    return None

async def send_set_command():
    device = await find_target_device()
    if not device:
        return "デバイスが見つかりません"
    async with BleakClient(device.address) as client:
        await client.write_gatt_char(CHARACTERISTIC_UUID, b"set")
        return "setコマンド送信完了"

async def send_target_and_wait_hit(timeout=10.0):
    device = await find_target_device()
    if not device:
        return "デバイスが見つかりません"
    hit_result = {"hit": None}
    async with BleakClient(device.address) as client:
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler_factory(hit_result))
        await client.write_gatt_char(CHARACTERISTIC_UUID, b"target")
        print("targetコマンド送信、notify待機中...")
        try:
            for _ in range(int(timeout * 10)):
                if hit_result["hit"]:
                    break
                await asyncio.sleep(0.1)
            return hit_result["hit"] or "タイムアウト"
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

# 既存mainはMCPサーバから呼び出すためコメントアウトまたは削除
# if __name__ == "__main__":
#     asyncio.run(main()) 
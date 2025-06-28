import asyncio
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "E16CE87C-F8BE-4FC7-89EB-8EF9C55A08D0"
CHARACTERISTIC_UUID = "160A9096-C252-4C4F-A52D-6B013050EF93"

def notification_handler(sender, data):
    print(f"\nNotify受信: {data.decode()}")

async def async_input(prompt):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

async def main():
    print("スキャン中...")
    devices = await BleakScanner.discover()
    target_device = None
    for d in devices:
        print(f"見つかったデバイス: {d.name}, {d.address}")
        # デバイス名で判別（main.cppのBLEDevice::init(\"RollerPIDControl\")より）
        if d.name == "RollerPIDControl":
            target_device = d
            break

    if not target_device:
        print("デバイスが見つかりません")
        return

    print(f"接続中: {target_device.name} ({target_device.address})")
    async with BleakClient(target_device.address) as client:
        print("接続しました")
        await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
        try:
            while True:
                cmd = await async_input('送信コマンドを入力してください ("target" または "set"、終了は "exit"): ')
                if cmd == "exit":
                    break
                if cmd not in ["target", "set"]:
                    print("無効なコマンドです")
                    continue
                await client.write_gatt_char(CHARACTERISTIC_UUID, cmd.encode())
                print(f"送信: {cmd}")
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    asyncio.run(main()) 
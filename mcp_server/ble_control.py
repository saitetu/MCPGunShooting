import asyncio
from bleak import BleakClient, BleakScanner
import tkinter as tk
import threading
import multiprocessing
from multiprocessing import Process, Queue
from screeninfo import get_monitors
import aiohttp
import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import os
from dotenv import load_dotenv

SERVICE_UUID = "E16CE87C-F8BE-4FC7-89EB-8EF9C55A08D0"
CHARACTERISTIC_UUID = "160A9096-C252-4C4F-A52D-6B013050EF93"

message_queue = None
ui_process = None

# .envの読み込み
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
G2P_URL = os.getenv('G2P_URL', 'http://34.85.1.109/api/g2p')
SYNTHESIS_URL = os.getenv('SYNTHESIS_URL', 'http://34.85.1.109/api/synthesis')

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
        return {"hit_id": None, "elapsed_sec": None}
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
            notify = hit_result["hit"]
            if notify:
                # 例: 'hit_64,1.23' 形式をパース
                try:
                    hit_id, elapsed = notify.split(",")
                    elapsed_sec = float(elapsed)
                except Exception:
                    hit_id = notify
                    elapsed_sec = None
                return {"hit_id": hit_id, "elapsed_sec": elapsed_sec}
            else:
                return {"hit_id": None, "elapsed_sec": None}
        finally:
            await client.stop_notify(CHARACTERISTIC_UUID)

def message_window_loop(queue):
    monitors = get_monitors()
    if len(monitors) > 1:
        monitor = monitors[1]  # サブディスプレイ
    else:
        monitor = monitors[0]  # メイン

    root = tk.Tk()
    root.title("メッセージ表示")
    root.configure(bg="black")  # ウィンドウ全体の背景を黒に
    wrap_len = int(monitor.width * 0.9)
    label = tk.Label(
        root,
        text="",
        font=("Helvetica", 40),
        wraplength=wrap_len,
        justify="center",
        bg="black",   # ラベル背景を黒
        fg="white"    # 文字色を白
    )
    label.pack(padx=30, pady=30, expand=True, fill="both")

    root.geometry(f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")

    def check_queue():
        try:
            while True:
                msg = queue.get_nowait()
                label.config(text=msg)
        except:
            pass
        root.after(100, check_queue)
    check_queue()
    root.mainloop()

def start_message_window():
    global message_queue, ui_process
    if message_queue is None:
        message_queue = Queue()
        ui_process = Process(target=message_window_loop, args=(message_queue,))
        ui_process.start()

async def show_message_window(message: str):
    start_message_window()
    message_queue.put(message)

    # --- ここから音声合成処理 ---
    g2p_url = G2P_URL
    synthesis_url = SYNTHESIS_URL
    mora_tone_list = None
    async with aiohttp.ClientSession() as session:
        # g2p API
        async with session.post(g2p_url, json={"text": message}) as resp:
            if resp.status == 200:
                mora_tone_list = await resp.json()
            else:
                print("g2p APIエラー", resp.status)
                return "g2p APIエラー"
        # synthesis API
        synth_payload = {
            "text": message,
            "model": "kinichiro-asamoto",
            "modelFile": "model_assets/kinichiro-asamoto/kinichiro-asamoto.safetensors",
            "style": "Neutral",
            "speaker": "kinichiro-asamoto",
            "moraToneList": mora_tone_list,
            "accentModified": False,
            "styleWeight": 1,
            "speed": 1,
            "sdpRatio": 0.2,
            "noise": 0.6,
            "noisew": 0.8,
            "pitchScale": 1,
            "intonationScale": 1,
            "silenceAfter": 0.5
        }
        async with session.post(synthesis_url, json=synth_payload) as resp:
            if resp.status == 200:
                wav_bytes = await resp.read()
            else:
                print("synthesis APIエラー", resp.status)
                return "synthesis APIエラー"
    # WAVデータを一時ファイルとして保存せずに再生
    import io
    wav_buf = io.BytesIO(wav_bytes)
    rate, data = wavfile.read(wav_buf)
    # データがint16の場合、float32に変換
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    sd.play(data, rate)
    sd.wait()
    # --- ここまで音声合成処理 ---
    return "表示・再生しました"

def show_message_window_sync(message: str):
    root = tk.Tk()
    root.title("メッセージ表示")
    label = tk.Label(root, text=message, font=("Helvetica", 20))
    label.pack(padx=30, pady=30)
    button = tk.Button(root, text="OK", font=("Helvetica", 14), width=10, command=root.destroy)
    button.pack(pady=(0, 20))
    root.mainloop()

# 既存mainはMCPサーバから呼び出すためコメントアウトまたは削除
# if __name__ == "__main__":
#     asyncio.run(main())

if __name__ == "__main__":
    msg = input("表示したいメッセージを入力してください: ")
    show_message_window_sync(msg)
    input("ウィンドウが表示されたらEnterを押してください（プログラム終了防止用）") 
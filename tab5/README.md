# ロラー制御システム (MQTT版)

ESP32-P4を使用したロラー制御システムです。MQTT経由でリモート制御が可能です。

## 機能

- **Targetモード**: エンコーダーの値を読み取り、変化量を表示
- **Setモード**: モーターを位置制御モードで動作させ、位置0に設定
- **ボタン制御**: ピン41のボタンでモードを切り替え
- **MQTT通信**: 外部からコマンドでモード切替

## セットアップ

### 1. 設定ファイルの編集

`src/config.h`を編集して、WiFiの認証情報を設定してください：

```cpp
const char* ssid = "your_wifi_ssid";        // あなたのWiFiのSSID
const char* password = "your_wifi_password"; // あなたのWiFiのパスワード
```

### 2. ビルドとアップロード

PlatformIOを使用してビルドとアップロードを行います：

```bash
pio run --target upload
```

### 3. MQTTテスト

Pythonスクリプトを使用してMQTT通信をテストできます：

```bash
# 必要なライブラリをインストール
pip install paho-mqtt

# テストスクリプトを実行
python mqtt_test.py
```

## 使用方法

### ボタン操作
- ピン41のボタンを押すとモードが切り替わります

### MQTTコマンド
- `target`: Targetモードに切り替え
- `set`: Setモードに切り替え

### テストスクリプトの使用例

```bash
$ python mqtt_test.py
MQTTブローカーに接続しました
ロラー制御システムのテスト
コマンド:
  'target' - Targetモードに切り替え
  'set'    - Setモードに切り替え
  'quit'   - 終了

コマンドを入力してください: target
'target'コマンドを送信しました
コマンドを入力してください: set
'set'コマンドを送信しました
コマンドを入力してください: quit
プログラムを終了します
```

## ハードウェア接続

- **M5Unit-Roller**: I2C接続 (SDA: 2, SCL: 1)
- **ボタン**: ピン41 (プルアップ抵抗付き)
- **ディスプレイ**: M5GFX対応ディスプレイ

## トラブルシューティング

### WiFi接続エラー
- `config.h`のWiFi設定を確認してください
- ネットワークの範囲内にいることを確認してください

### MQTT接続エラー
- インターネット接続を確認してください
- ファイアウォールでMQTTポート(1883)がブロックされていないか確認してください

### ロラー制御エラー
- I2C接続を確認してください
- M5Unit-Rollerの電源供給を確認してください

## ライブラリ

- M5GFX: ディスプレイ制御
- M5Unit-Roller: ロラーユニット制御
- PubSubClient: MQTT通信
- WiFi: WiFi接続 
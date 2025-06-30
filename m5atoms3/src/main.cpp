#include <Arduino.h>
#include <M5Unified.h>
#include "unit_rolleri2c.hpp"
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <string>
#include <stdio.h>
#include <M5GFX.h>
#include "unit_roller_common.hpp"

UnitRollerI2C RollerI2C_64; // 0x64用
UnitRollerI2C RollerI2C_63; // 0x63用

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// Default PID values
uint32_t p = 500000, i = 0, d = 10000000;

// モード管理用
enum ModeType
{
  MODE_TARGET,
  MODE_SET,
  MODE_SET_TO_TARGET // 追加: set→targetへ遷移待ち用
};
ModeType currentMode = MODE_TARGET;

int32_t prevEncoder = 0;

unsigned long setStartTime = 0;    // setモード開始時刻
unsigned long hitTime = 0;         // ヒット時刻
bool hitOccurred = false;          // どちらかがヒットしたか
unsigned long targetStartTime = 0; // targetモード開始時刻

// The SERVICE_UUID must be unique for each device.
// The last part can be changed for each target (e.g., ...D0, ...D1, ...D2)
#define SERVICE_UUID "E16CE87C-F8BE-4FC7-89EB-8EF9C55A08D0"
// The CHARACTERISTIC_UUID is fixed.
#define CHARACTERISTIC_UUID "160A9096-C252-4C4F-A52D-6B013050EF93"

class MyServerCallbacks : public BLEServerCallbacks
{
  void onConnect(BLEServer *pServer)
  {
    deviceConnected = true;
    M5.Lcd.println("Device connected");
  };

  void onDisconnect(BLEServer *pServer)
  {
    deviceConnected = false;
    M5.Lcd.println("Device disconnected");
    BLEDevice::startAdvertising();
  }
};

class MyCharacteristicCallbacks : public BLECharacteristicCallbacks
{
  void onWrite(BLECharacteristic *pCharacteristic)
  {
    String rxValue = pCharacteristic->getValue();
    if (rxValue.length() > 0)
    {
      if (rxValue == "target")
      {
        // target受信時、まずsetモードに遷移し、2秒後にtargetモードへ
        currentMode = MODE_SET_TO_TARGET;
        setStartTime = millis();
        M5.Lcd.fillScreen(BLUE);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println("Mode: set (auto→target)");
      }
      else if (rxValue == "set")
      {
        currentMode = MODE_SET;
        M5.Lcd.fillScreen(BLUE);
        M5.Lcd.setCursor(0, 0);
        M5.Lcd.println("Mode: set");
      }
      else
      {
        M5.Lcd.fillScreen(BLACK);
      }
      M5.Lcd.setCursor(0, 0);
      M5.Lcd.printf("Received: %s\n", rxValue.c_str());
    }
  }
};

void setup()
{
  M5.begin();
  M5.Lcd.setTextSize(2);
  RollerI2C_64.begin(&Wire, 0x64, 2, 1, 400000);
  RollerI2C_63.begin(&Wire, 0x63, 2, 1, 400000);
  pinMode(41, INPUT_PULLUP); // ボタン用

  RollerI2C_64.setPosPID(p, i, d);
  RollerI2C_63.setPosPID(p, i, d);

  BLEDevice::init("RollerPIDControl");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ |
          BLECharacteristic::PROPERTY_WRITE |
          BLECharacteristic::PROPERTY_WRITE_NR |
          BLECharacteristic::PROPERTY_NOTIFY);

  pCharacteristic->setCallbacks(new MyCharacteristicCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());

  // char buffer[50];
  // sprintf(buffer, "%u,%u,%u", p, i, d);
  // pCharacteristic->setValue(buffer);

  pService->start();

  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();

  M5.Lcd.clear();
  M5.Lcd.println("BLE Server started.");
  M5.Lcd.println("Waiting for connection...");
}

void loop()
{
  static int32_t baseEncoder_64 = 0;
  static int32_t baseEncoder_63 = 0;
  static bool hit_64 = false;
  static bool hit_63 = false;
  static ModeType prevMode = MODE_TARGET;

  // --- ボタンでモード切替 ---
  static int lastBtn = HIGH;
  static unsigned long lastBtnTime = 0;
  int btn = digitalRead(41);
  if (lastBtn == HIGH && btn == LOW && millis() - lastBtnTime > 300)
  { // 押した瞬間
    // モードトグル
    if (currentMode == MODE_TARGET)
    {
      currentMode = MODE_SET;
    }
    else
    {
      currentMode = MODE_TARGET;
    }
    lastBtnTime = millis();
  }
  lastBtn = btn;

  // set→target自動遷移処理
  if (currentMode == MODE_SET_TO_TARGET)
  {
    // setモードの処理（MODE_SETと同じ）
    if (prevMode != MODE_SET_TO_TARGET)
    {
      RollerI2C_64.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_64.setRGB(0xFFE0); // 黄色
      RollerI2C_63.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_63.setRGB(0xFFE0); // 黄色
      hit_64 = false;
      hit_63 = false;
      prevMode = MODE_SET_TO_TARGET;
      M5.Lcd.fillScreen(BLUE);
    }
    RollerI2C_64.setMode(ROLLER_MODE_POSITION);
    RollerI2C_64.setPosMaxCurrent(200000);
    RollerI2C_64.setPos(18890);
    RollerI2C_64.setOutput(1);
    RollerI2C_63.setMode(ROLLER_MODE_POSITION);
    RollerI2C_63.setPosMaxCurrent(200000);
    RollerI2C_63.setPos(-21700);
    RollerI2C_63.setOutput(1);
    // 2秒経過したらtargetモードへ
    if (millis() - setStartTime >= 2000)
    {
      currentMode = MODE_TARGET;
      prevMode = MODE_SET_TO_TARGET; // すぐにMODE_TARGETの初期化が走るように
    }
    delay(10);
    return;
  }

  if (currentMode == MODE_TARGET)
  {
    // targetモードに入った瞬間、基準値を保存
    if (prevMode != MODE_TARGET)
    {
      baseEncoder_64 = RollerI2C_64.getPosReadback();
      baseEncoder_63 = RollerI2C_63.getPosReadback();
      hit_64 = false;
      hit_63 = false;
      hitOccurred = false;
      prevMode = MODE_TARGET;
      M5.Lcd.fillScreen(BLACK);
      RollerI2C_64.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_64.setRGB(0x07E0); // 緑
      RollerI2C_63.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_63.setRGB(0x07E0); // 緑
      targetStartTime = millis();
    }
    RollerI2C_64.setOutput(0);
    RollerI2C_63.setOutput(0);
    int32_t delta_64 = RollerI2C_64.getPosReadback() - baseEncoder_64;
    int32_t delta_63 = RollerI2C_63.getPosReadback() - baseEncoder_63;
    if (!hit_64 && abs(delta_64) >= 3000)
    {
      RollerI2C_64.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_64.setRGB(0xF800); // 赤
      hit_64 = true;
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(0, 0);
      M5.Lcd.println("HIT! 64");
      // Notify送信（経過秒数付き）
      float elapsed = (millis() - targetStartTime) / 1000.0f;
      char buf[32];
      snprintf(buf, sizeof(buf), "hit_64,%.2f", elapsed);
      pCharacteristic->setValue(buf);
      pCharacteristic->notify();
      if (!hitOccurred)
      {
        hitTime = millis();
        hitOccurred = true;
      }
    }
    if (!hit_63 && abs(delta_63) >= 3000)
    {
      RollerI2C_63.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_63.setRGB(0xF800); // 赤
      hit_63 = true;
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(0, 0);
      M5.Lcd.println("HIT! 63");
      // Notify送信（経過秒数付き）
      float elapsed = (millis() - targetStartTime) / 1000.0f;
      char buf[32];
      snprintf(buf, sizeof(buf), "hit_63,%.2f", elapsed);
      pCharacteristic->setValue(buf);
      pCharacteristic->notify();
      if (!hitOccurred)
      {
        hitTime = millis();
        hitOccurred = true;
      }
    }
    // どちらかヒット後5秒で両方赤
    if (hitOccurred && millis() - hitTime >= 5000)
    {
      RollerI2C_64.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_64.setRGB(0xFFFF); // 白
      RollerI2C_63.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_63.setRGB(0xFFFF); // 白
      hitOccurred = false;         // 一度だけ実行
    }
    delay(10);
  }
  else if (currentMode == MODE_SET)
  {
    // setモードに入った瞬間だけLEDとヒット判定をリセット
    if (prevMode != MODE_SET)
    {
      RollerI2C_64.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_64.setRGB(0xFFE0); // 黄色
      RollerI2C_63.setRGBMode(ROLLER_RGB_MODE_USER_DEFINED);
      RollerI2C_63.setRGB(0xFFE0); // 黄色
      hit_64 = false;
      hit_63 = false;
      prevMode = MODE_SET;
      M5.Lcd.fillScreen(BLUE);
    }
    RollerI2C_64.setMode(ROLLER_MODE_POSITION);
    RollerI2C_64.setPosMaxCurrent(200000);
    RollerI2C_64.setPos(18890);
    RollerI2C_64.setOutput(1);
    RollerI2C_63.setMode(ROLLER_MODE_POSITION);
    RollerI2C_63.setPosMaxCurrent(200000);
    RollerI2C_63.setPos(-21700);
    RollerI2C_63.setOutput(1);
    delay(10);
  }
}

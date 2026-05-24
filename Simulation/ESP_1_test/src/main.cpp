#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>

#define WIFI_SSID    "Wokwi-GUEST"
#define WIFI_PASSWORD ""
#define MQTT_BROKER  "10.200.64.195"
#define MQTT_PORT    1883

#define ROOM_ID      "A1.01"
#define DEVICE_ID    "ESP-SIM-1"
#define BUILDING_ID  "Gedung-A"
#define FLOOR        1

#define PIN_DHT1          5
#define PIN_DHT2          4
#define PIN_PIR1          26
#define PIN_PIR2          25
#define PIN_GAS1          32
#define PIN_GAS2          33
#define PIN_POT           35
#define PIN_RELAY_MASTER  17
#define PIN_RELAY_LIGHTS  21
#define PIN_RELAY_AC      23

#define TOPIC_TELEMETRY "tekra/wokwi/" ROOM_ID "/telemetry"
#define TOPIC_COMMANDS  "tekra/wokwi/" ROOM_ID "/commands"
#define PUBLISH_INTERVAL_MS 10000

struct SensorReadings {
    float temperature;
    float humidity;
    float heatIndex;
    float airQuality;
    float lux;
    float comfortScore;
    float voltage;
    float current;
    float powerW;
    float energy;
    bool  pirTriggered;
    int   estimatedPeople;
    float activityScore;
    String occupancyState;
};

struct ActuatorState {
    bool masterRelay;
    bool lights;
    bool ac;
    float acSetpoint;
    String mode;
};

SensorReadings readings;
ActuatorState  actuators = {false, false, false, 24.0, "AUTO"};
float          cumulativeEnergy = 0.0;
SemaphoreHandle_t stateMutex;

WiFiClient   wifiClient;
PubSubClient mqtt(wifiClient);
DHT          dht1(PIN_DHT1, DHT22);
DHT          dht2(PIN_DHT2, DHT22);

float computeComfortScore(float temp, float hum, float airPpm, float lux) {
    float tScore = constrain(100.0f - abs(temp - 22.5f) * 6.0f, 0, 100);
    float hScore = constrain(100.0f - abs(hum - 50.0f) * 2.0f, 0, 100);
    float aScore = constrain(map((int)airPpm, 400, 1500, 100, 0), 0, 100);
    float lScore = (lux >= 200.0f && lux <= 600.0f) ? 100.0f : 50.0f;
    return tScore * 0.35f + hScore * 0.25f + aScore * 0.25f + lScore * 0.15f;
}

String getTimestamp() {
    time_t now = time(nullptr);
    if (now < 1000000) return "2026-01-01T00:00:00Z";
    struct tm* t = gmtime(&now);
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", t);
    return String(buf);
}

void applyRelays() {
    if (actuators.masterRelay) {
        digitalWrite(PIN_RELAY_MASTER, HIGH);
        digitalWrite(PIN_RELAY_LIGHTS, LOW);
        digitalWrite(PIN_RELAY_AC,     LOW);
    } else {
        digitalWrite(PIN_RELAY_MASTER, LOW);
        digitalWrite(PIN_RELAY_LIGHTS, actuators.lights ? HIGH : LOW);
        digitalWrite(PIN_RELAY_AC,     actuators.ac     ? HIGH : LOW);
    }
}

void onCommand(char* topic, byte* payload, unsigned int length) {
    String msg;
    for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
    Serial.println("[CMD] Received: " + msg);

    JsonDocument doc;
    if (deserializeJson(doc, msg) != DeserializationError::Ok) {
        Serial.println("[CMD] Bad JSON, ignoring.");
        return;
    }

    xSemaphoreTake(stateMutex, portMAX_DELAY);

    actuators.acSetpoint = doc["ac_setpoint"] | actuators.acSetpoint;

    if (!doc["mode"].isNull()) {
        actuators.mode = doc["mode"].as<String>();
        Serial.printf("[CMD] Mode → %s\n", actuators.mode.c_str());
    }

    if (!doc["actuators"]["master_relay"].isNull()) {
        actuators.masterRelay = doc["actuators"]["master_relay"].as<bool>();
    }

    if (actuators.masterRelay) {
        Serial.println("[CMD] ⚠️  MASTER RELAY ON");
    } else if (actuators.mode == "OVERRIDE") {
        if (!doc["actuators"]["lights"].isNull())
            actuators.lights = doc["actuators"]["lights"].as<bool>();
        if (!doc["actuators"]["ac"].isNull())
            actuators.ac = doc["actuators"]["ac"].as<bool>();
    }

    applyRelays();
    Serial.printf("[CMD] lights=%d ac=%d setpoint=%.1f master=%d mode=%s\n",
        actuators.lights, actuators.ac, actuators.acSetpoint,
        actuators.masterRelay, actuators.mode.c_str());

    xSemaphoreGive(stateMutex);
}

void taskReadSensors(void* param) {
    while (true) {
        float t1 = dht1.readTemperature();
        float h1 = dht1.readHumidity();
        float t2 = dht2.readTemperature();
        float h2 = dht2.readHumidity();

        float temp = (!isnan(t1) && !isnan(t2)) ? (t1 + t2) / 2.0f
                   : (!isnan(t1) ? t1 : 25.0f);
        float hum  = (!isnan(h1) && !isnan(h2)) ? (h1 + h2) / 2.0f
                   : (!isnan(h1) ? h1 : 60.0f);
        float heatIdx = dht1.computeHeatIndex(temp, hum, false);

        float gas1   = analogRead(PIN_GAS1);
        float gas2   = analogRead(PIN_GAS2);
        float airPpm = ((gas1 + gas2) / 2.0f / 4095.0f) * 1600.0f + 400.0f;

        float lux = 350.0f + sin(millis() / 30000.0f) * 120.0f + random(-15, 15);
        lux = max(0.0f, lux);

        float comfort = computeComfortScore(temp, hum, airPpm, lux);

        float current = (analogRead(PIN_POT) / 4095.0f) * 15.0f;
        float voltage = 220.0f;
        float power   = voltage * current * 0.95f;
        cumulativeEnergy += power * (PUBLISH_INTERVAL_MS / 3600000.0f) / 1000.0f;

        bool pir1 = digitalRead(PIN_PIR1);
        bool pir2 = digitalRead(PIN_PIR2);
        bool triggered = pir1 || pir2;
        float activity = (pir1 ? 0.5f : 0.0f) + (pir2 ? 0.5f : 0.0f);

        int    people = 0;
        String state  = "EMPTY";
        if (pir1 && pir2)   { people = random(15, 35); state = "OCCUPIED"; }
        else if (triggered) { people = random(1, 10);  state = "TRANSITIONING"; }

        xSemaphoreTake(stateMutex, portMAX_DELAY);

        if (!actuators.masterRelay && actuators.mode == "AUTO") {
            bool shouldLight = (lux < 300.0f);
            bool shouldAC    = (state == "OCCUPIED" || state == "TRANSITIONING")
                            || (temp >= 28.0f)
                            || (airPpm >= 900.0f);

            bool changed = false;
            if (actuators.lights != shouldLight) {
                actuators.lights = shouldLight;
                changed = true;
                Serial.printf("[AUTO] Lights %s (lux=%.0f)\n", shouldLight ? "ON" : "OFF", lux);
            }
            if (actuators.ac != shouldAC) {
                actuators.ac = shouldAC;
                changed = true;
                Serial.printf("[AUTO] AC %s (temp=%.1f ppm=%.0f state=%s)\n",
                    shouldAC ? "ON" : "OFF", temp, airPpm, state.c_str());
            }
            if (changed) applyRelays();
        }

        readings = { temp, hum, heatIdx, airPpm, lux, comfort,
                     voltage, current, power, cumulativeEnergy,
                     triggered, people, activity, state };

        xSemaphoreGive(stateMutex);

        Serial.printf("[SENSOR] T=%.1f H=%.0f%% AQ=%.0fppm Lux=%.0f Score=%.1f PIR=%d/%d %s\n",
            temp, hum, airPpm, lux, comfort, pir1, pir2, state.c_str());

        vTaskDelay(pdMS_TO_TICKS(PUBLISH_INTERVAL_MS));
    }
}

void connectMQTT() {
    while (!mqtt.connected()) {
        Serial.printf("[MQTT] Connecting to %s:%d...\n", MQTT_BROKER, MQTT_PORT);
        if (mqtt.connect(DEVICE_ID)) {
            mqtt.subscribe(TOPIC_COMMANDS);
            Serial.println("[MQTT] Connected. Subscribed to " TOPIC_COMMANDS);
        } else {
            Serial.printf("[MQTT] Failed (rc=%d), retry in 3s\n", mqtt.state());
            vTaskDelay(pdMS_TO_TICKS(3000));
        }
    }
}

void taskMQTT(void* param) {
    connectMQTT();
    unsigned long lastPublish = 0;

    while (true) {
        if (!mqtt.connected()) connectMQTT();
        mqtt.loop();

        unsigned long now = millis();
        if (now - lastPublish >= PUBLISH_INTERVAL_MS) {
            lastPublish = now;

            xSemaphoreTake(stateMutex, portMAX_DELAY);
            SensorReadings r = readings;
            ActuatorState  a = actuators;
            xSemaphoreGive(stateMutex);

            JsonDocument doc;
            doc["device_id"]   = DEVICE_ID;
            doc["building_id"] = BUILDING_ID;
            doc["floor"]       = FLOOR;
            doc["room_id"]     = ROOM_ID;
            doc["timestamp"]   = getTimestamp();
            doc["mode"]        = a.mode;

            JsonObject env = doc["environment"].to<JsonObject>();
            env["temperature"]   = round(r.temperature * 10) / 10.0;
            env["humidity"]      = round(r.humidity * 10) / 10.0;
            env["heat_index"]    = round(r.heatIndex * 10) / 10.0;
            env["air_quality"]   = round(r.airQuality);
            env["lux"]           = round(r.lux);
            env["comfort_score"] = round(r.comfortScore * 10) / 10.0;

            JsonObject pwr = doc["power"].to<JsonObject>();
            pwr["voltage"]   = r.voltage;
            pwr["current"]   = round(r.current * 10) / 10.0;
            pwr["power"]     = round(r.powerW);
            pwr["energy"]    = round(r.energy * 1000) / 1000.0;
            pwr["frequency"] = 50.0;
            pwr["pf"]        = 0.95;

            JsonObject occ = doc["occupancy"].to<JsonObject>();
            occ["pir_triggered"]    = r.pirTriggered;
            occ["estimated_people"] = r.estimatedPeople;
            occ["activity_score"]   = r.activityScore;
            occ["state"]            = r.occupancyState;

            String payload;
            serializeJson(doc, payload);

            if (mqtt.publish(TOPIC_TELEMETRY, payload.c_str()))
                Serial.println("[MQTT] Published ✓");
            else
                Serial.println("[MQTT] Publish failed!");
        }

        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("\n=== TEKRA ESP32 Simulation | Room: " ROOM_ID " ===");

    pinMode(PIN_RELAY_MASTER, OUTPUT); digitalWrite(PIN_RELAY_MASTER, LOW);
    pinMode(PIN_RELAY_LIGHTS, OUTPUT); digitalWrite(PIN_RELAY_LIGHTS, LOW);
    pinMode(PIN_RELAY_AC,     OUTPUT); digitalWrite(PIN_RELAY_AC,     LOW);
    pinMode(PIN_PIR1, INPUT);
    pinMode(PIN_PIR2, INPUT);

    dht1.begin();
    dht2.begin();

    Serial.print("Connecting to WiFi");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.println("\nWiFi: " + WiFi.localIP().toString());

    configTime(7 * 3600, 0, "pool.ntp.org", "time.nist.gov");
    time_t now = time(nullptr);
    int tries = 0;
    while (now < 1000000 && tries++ < 20) { delay(500); now = time(nullptr); }
    Serial.println("Time: " + getTimestamp());

    mqtt.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt.setCallback(onCommand);
    mqtt.setBufferSize(512);

    stateMutex = xSemaphoreCreateMutex();
    readings   = {25.0, 60.0, 26.0, 600.0, 350.0, 70.0, 220.0, 0, 0, 0, false, 0, 0.0, "EMPTY"};

    xTaskCreate(taskReadSensors, "Sensors", 4096, NULL, 1, NULL);
    xTaskCreate(taskMQTT,        "MQTT",    8192, NULL, 2, NULL);

    Serial.println("System running.");
}

void loop() {
    vTaskDelay(pdMS_TO_TICKS(1000));
}

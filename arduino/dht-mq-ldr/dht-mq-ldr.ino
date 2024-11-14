#include <WiFi.h>
#include <DHT.h>
#include "credentials.h"  // Include your WiFi credentials

// DHT Sensor setup
#define DHTPIN 14  // Pin connected to the DHT22 sensor
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);

// Other sensor pins
#define MQ2_PIN 34   // Analog pin for MQ2
#define MQ135_PIN 35 // Analog pin for MQ135
#define LDR_PIN 32   // Analog pin for LDR

const int port = 5000;
const String url = "/insert_data";

void setup() {
  Serial.begin(115200);
  delay(10);

  dht.begin();

  // Connect to WiFi
  Serial.println();
  Serial.println("Connecting to WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.println("WiFi connected");
}

void loop() {
  // Read from DHT22
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  // Check if DHT read failed
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  // Read from MQ2, MQ135, and LDR sensors
  int mq2ValueRaw = analogRead(MQ2_PIN);
  int mq135ValueRaw = analogRead(MQ135_PIN);
  int ldrValueRaw = analogRead(LDR_PIN);

  // Scale analog readings to 0–100
  int mq2Value = map(mq2ValueRaw, 0, 4095, 0, 100);
  int mq135Value = map(mq135ValueRaw, 0, 4095, 0, 100);
  int ldrValue = map(ldrValueRaw, 0, 4095, 0, 100);

  // Prepare data in URL-encoded format
  String data = "temperature=" + String(temperature) + 
                "&humidity=" + String(humidity) + 
                "&mq2Value=" + String(mq2Value) + 
                "&mq135Value=" + String(mq135Value) + 
                "&ldrValue=" + String(ldrValue);

  // Check WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Attempting to reconnect...");
    WiFi.begin(ssid, password); // Try to reconnect
  }

  WiFiClient client;

  // Connect to the server
  if (client.connect(server, port)) {
    Serial.println("Connected to server. Sending data...");

    // Send HTTP POST request
    client.println("POST " + url + " HTTP/1.1");
    client.println("Host: " + String(server));
    client.println("Content-Type: application/x-www-form-urlencoded");
    client.println("Connection: close");
    client.print("Content-Length: ");
    client.println(data.length());
    client.println();
    client.print(data);

    // Wait for server response with a timeout
    String response = "";
    unsigned long startTime = millis(); // Start timing
    bool responseReceived = false;

    while (client.connected() && (millis() - startTime < 30000)) {
      if (client.available()) {
        String line = client.readStringUntil('\n');
        if (line == "\r") {
          break; // End of headers
        }
        responseReceived = true; // We received some data
      }
    }

    // Check if a response was received within the timeout
    if (!responseReceived) {
      Serial.println("No response from server.");
    } else {
      // Read the response body
      while (client.available()) {
        response += client.readStringUntil('\n');
      }

      Serial.println("Response from server: " + response);
      
      // Check for success in the response
      if (response.indexOf("Data inserted successfully") >= 0) {
        Serial.println("Data inserted successfully.");
      } else {
        Serial.println("Failed to insert data.");
      }
    }
  } else {
    Serial.println("Failed to connect to server.");
  }

  // Delay before the next reading
  delay(30000);  // 30 seconds delay (adjust as needed)
}

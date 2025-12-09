#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_Fingerprint.h>
#include <ArduinoJson.h>


const char* ssid = "CLARO1_818E77";      
const char* password = "248K2UEUVY";  
const char* serverUrl = "http://192.168.1.24:5000"; 
const char* apiKey = "puestito_seguro_2025";

#define RX_PIN 18 
#define TX_PIN 19

HardwareSerial mySerial(2);
Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);

bool sensorConectado = true;
unsigned long lastServerCheck = 0;
const long serverInterval = 1500; 

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n\n--- INICIANDO SISTEMA DE ASISTENCIA ---");

  mySerial.begin(57600, SERIAL_8N1, RX_PIN, TX_PIN); 
  
  if (finger.verifyPassword()) {
    Serial.println("✅ Sensor biométrico encontrado!");
    sensorConectado = true;
  } else {
    Serial.println("❌ ERROR: No se encuentra el sensor biométrico.");
    sensorConectado = false;
  }

  WiFi.mode(WIFI_STA); 
  WiFi.setSleep(false); 
  WiFi.begin(ssid, password);
  
  Serial.print("Conectando a WiFi");
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    delay(500);
    Serial.print(".");
    intentos++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi Conectado.");
    Serial.print("IP: "); Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ Fallo al conectar WiFi (Se reintentará automáticamente).");
  }
}

void loop() {
  if(WiFi.status() != WL_CONNECTED) {
     Serial.println("⚠️ WiFi perdido, reconectando...");
     WiFi.disconnect();
     WiFi.reconnect();
     delay(1000); 
     return;
  }

  verificarEstadoSensor();

  if (!sensorConectado) {
    delay(100); 
    return; 
  }

  unsigned long currentMillis = millis();
  
  if (currentMillis - lastServerCheck >= serverInterval) {
    lastServerCheck = currentMillis;
    
    String mode = checkServerMode();
    
    if (mode == "enroll") {
      handleEnrollment();
    } 
    else if (mode == "clear") {
      handleClearSensor();
    }
  }
}

void verificarEstadoSensor() {
  int p = finger.getImage();

  if (p == FINGERPRINT_PACKETRECIEVEERR) {
    if (sensorConectado) {
       Serial.println("\n🚨 ¡ALERTA! SENSOR DESCONECTADO 🚨");
       sensorConectado = false;
    }
  } 
  else {
    if (!sensorConectado) {
       Serial.println("\n✨ SENSOR RECONECTADO ✨");
       sensorConectado = true;
       mySerial.flush();
    }
    if (p == FINGERPRINT_OK) {
       procesarHuellaDetectada();
    }
  }
}

void procesarHuellaDetectada() {
  // Convertir imagen a plantilla
  int p = finger.image2Tz(1);
  if (p != FINGERPRINT_OK) return;

  p = finger.fingerSearch(); 
  
  if (p != FINGERPRINT_OK) {
    Serial.println("⛔ Huella no reconocida (Intenta limpiar el dedo o hidratarlo)");
    return;
  }

  // ¡Encontrado!
  Serial.print("ID Detectado #"); Serial.print(finger.fingerID); 
  Serial.println(". Enviando asistencia...");
  
  sendAttendance(finger.fingerID);

  delay(1500); 
}

String checkServerMode() {
    HTTPClient http;
    http.begin(String(serverUrl) + "/api/biometric/status");
    http.setTimeout(1500); 
    
    int httpCode = http.GET();
    String resultado = "scan"; 

    if (httpCode == 200) {
      String payload = http.getString();
      if (payload.indexOf("enroll") > 0) resultado = "enroll";
      if (payload.indexOf("clear") > 0) resultado = "clear";
    } 
    http.end(); 
    return resultado;
}

void sendAttendance(int id) {
  for (int intento = 0; intento < 2; intento++) {
    
    if (WiFi.status() != WL_CONNECTED) {
       WiFi.reconnect();
       delay(500);
    }

    HTTPClient http;
    http.begin(String(serverUrl) + "/api/biometric/attendance");
    http.addHeader("Content-Type", "application/json");
    
    http.addHeader("Connection", "close"); 
    
    http.setTimeout(5000); 
    
    String json = "{\"finger_id\": " + String(id) + "}";
    int httpCode = http.POST(json);
    
    if(httpCode == 200 || httpCode == 201) {
      Serial.println("Asistencia registrada correctamente.");
      http.end();
      return; 
    } 
    else if (httpCode == 200 && intento == 0) {
       Serial.println("ℹ️ Servidor recibió, pero indicó espera.");
       http.end();
       return;
    }
    else {
      Serial.print("Intento "); Serial.print(intento + 1);
      Serial.print(" falló (Code "); Serial.print(httpCode); Serial.println(").");
      http.end(); 
      delay(500); 
    }
  }
  Serial.println("Error definitivo enviando asistencia.");
}

void handleEnrollment() {
  Serial.println("\n🔵 MODO ENROLAMIENTO");
  int id = getNextFreeID();
  if (id == -1) return;

  sendStatusUpdate(0, "Pon el dedo ahora");
  
  unsigned long startWait = millis();
  while (true) {
    if (millis() - startWait > 30000) { 
        sendStatusUpdate(0, "Tiempo agotado"); 
        return; 
    }
    int p = finger.getImage();
    if (p == FINGERPRINT_OK) break;
    delay(50);
  }

  finger.image2Tz(1);
  Serial.println("👆 LEVANTA EL DEDO");
  
  sendStatusUpdate(1, "¡Leído! Levanta el dedo");
  delay(1000); 
  
  startWait = millis();
  while (finger.getImage() != FINGERPRINT_NOFINGER) {
     if (millis() - startWait > 10000) return;
  }
  
  Serial.println("👉 PON EL MISMO DEDO OTRA VEZ");
  
  sendStatusUpdate(2, "Pon el mismo dedo otra vez");
  
  startWait = millis();
  while (finger.getImage() != FINGERPRINT_OK) {
    if (millis() - startWait > 30000) return;
  }
  
  finger.image2Tz(2);
  
  if (finger.createModel() == FINGERPRINT_OK) {
    if (finger.storeModel(id) == FINGERPRINT_OK) {
      reportActionSuccess("enroll-success", id);
      delay(1000); 
    }
  }
}

// --- MODO LIMPIEZA (BORRAR TODO) ---
void handleClearSensor() {
  Serial.println("\n🧹 MODO LIMPIEZA RECIBIDO");
  Serial.println("⚠️ Borrando base de datos del sensor...");
  
  finger.emptyDatabase();
  
  Serial.println("✨ Sensor totalmente limpio (0 huellas).");
  
  // Avisamos al servidor para que quite el modo alerta
  reportActionSuccess("clear-success", 0);
  delay(2000);
}

// --- UTILIDADES ---
int getNextFreeID() {
  for (int i = 1; i < 127; i++) {
    uint8_t p = finger.loadModel(i);
    if (p != FINGERPRINT_OK) return i; 
  }
  return -1;
}

void reportActionSuccess(String endpoint, int id) {
  HTTPClient http;
  http.begin(String(serverUrl) + "/api/biometric/" + endpoint);
  http.addHeader("Content-Type", "application/json");
  String json = "{\"finger_id\": " + String(id) + "}";
  http.POST(json);
  http.end();
}

void sendStatusUpdate(int step, String msg) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(String(serverUrl) + "/api/biometric/update-progress");
    http.addHeader("Content-Type", "application/json");
    String json = "{\"step\": " + String(step) + ", \"message\": \"" + msg + "\"}";
    http.POST(json);
    http.end();
  }
}
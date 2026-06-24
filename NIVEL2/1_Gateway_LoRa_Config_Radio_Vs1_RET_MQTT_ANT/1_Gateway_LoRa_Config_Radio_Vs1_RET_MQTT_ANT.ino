/*
  MoT LoRa Site Survey Versão Zero | WissTek IoT
  Última versão: Branquinho / Felipe / Anderson
  Hardware: PKLoRa ESP32
*/

//=======================================================================
//                     1 - Bibliotecas
//=======================================================================
#include "Bibliotecas.h"  // Arquivo contendo declaração de bibliotecas e variáveis

//=======================================================================
// ------- 3 - Setup de inicialização ---------
//=======================================================================
// Inicializa as camadas
void setup() {
  //================= INICIALIZA SERIAL E MÓDULO RF95

  Serial.begin(115200);
  // Aguarda para estabilização da Serial
  delay(20);

  // declara Leds como saídas digital do ESP32
  pinMode(PIN_LED_VERMELHO, OUTPUT);
//  pinMode(PIN_LED_VERDE, OUTPUT);


  // ---------- Inicia Wi-Fi ----------
  conectar_wifi();
  // Aguarda para estabilização da Serial
  delay(20);
  CLIENT_ID = "esp32_gateway+lora_" + String(WiFi.macAddress());
  CLIENT_ID.replace(":", "");


  // ---------- Inicia MQTT ----------
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqtt_callback);
  mqttClient.setBufferSize(256);   // garante buffer para 20 bytes + overhead
  conectar_mqtt();


  // --- Inicialização da Comunicação SPI entre o ESP32 e o Módulo LoRa RFM95 ---
  SPI.begin(SCK, MISO, MOSI, SS);
  delay(20);
  LoRa.setSPI(SPI);
  delay(20);
  // --- Inicialização da Comunicação LoRa em 915Mhz---
  LoRa.setPins(SS, RST, DIO0);
  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("[Nó Sensor] Falha ao iniciar LoRa. Verifique conexões.");
    while (true); // Trava se o LoRa falhar
  }

  //  --- Atua Led vermelho  --- 
  digitalWrite(PIN_LED_VERMELHO, LOW); // LIGA LED VERMELHO - INDIFERENTE PARA O BOOT

  //  --- Atua Led verde  --- 
//  digitalWrite(PIN_LED_VERDE, LOW);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT

  // Aguarda 1 segundo para estabilização
  delay(1000);

  #ifdef loraCRC   // Habilitação do CRC do chip lora  (Configurado em bibliotecas.h)
    LoRa.enableCrc();
  #endif

} // FIM DO SETUP


//=======================================================================
//                     4 - Loop de repetição
//=======================================================================
// A função loop irá executar repetidamente
void loop() {


//MILLIS OUTTTTTTT
/*
  // --- Controle de timeout: aguardando confirmação UL do sensor ---
  if (aguardando_confirmacao_UL) {
    unsigned long tempo_limite_ms = (unsigned long)tempo_radio * 10UL * 1000UL;  // 10x o tempo recebido em MAC3_TEMPO

    if (millis() - millis_inicio_aguarda_UL >= tempo_limite_ms) {
      reset_gateway_para_setup_inicial();  // Timeout → sensor não respondeu → volta ao SETUP
    }
  }

*/

  // Mantém conexões ativas
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Reconectando...");
    conectar_wifi();
  }
  if (!mqttClient.connected()) {
    conectar_mqtt();
  }
  mqttClient.loop();   // processa mensagens MQTT pendentes

  // Verifica se chegou pacote DL via MQTT e o envia pelo rádio LoRa
  Phy_mqtt_receive_DL();


  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
  
}

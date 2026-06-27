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
  pinMode(PIN_LED_VERDE, OUTPUT);


  // ---------- Inicia Wi-Fi ----------
  //conectar_wifi();

  // Cadastre quantas redes você quiser (SSID, Senha)
  wifiMulti.addAP("MJCA_FUNDOS", "21092429MJC@");
  wifiMulti.addAP("COLETTI_ADV_CRIS", "45384609");
	wifiMulti.addAP("aafwifi", "aaf12345678");
	wifiMulti.addAP("CHACARA BBC", "Ailton1960#");
	wifiMulti.addAP("Claro-EB66", "54b80a7deb66");

  // O wifiMulti.run() tenta conectar a uma das redes cadastradas
  // Ele retorna WL_CONNECTED quando consegue se conectar com sucesso
  while (wifiMulti.run() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Wi-Fi conectado com sucesso!");
  Serial.print("Conectado na rede: ");
  Serial.println(WiFi.SSID());
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());


  CLIENT_ID = "esp32_gateway+lora_" + String(WiFi.macAddress());
  CLIENT_ID.replace(":", "");


  // ---------- Inicia MQTT ----------
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqtt_callback);
  mqttClient.setBufferSize(128);   // era 256 garante buffer para 20 bytes + overhead
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
  digitalWrite(PIN_LED_VERDE, LOW);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT

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
  // No loop, você pode monitorar a conexão.
  // Se a rede cair, o wifiMulti.run() tenta reconectar automaticamente à melhor rede disponível.
  if (wifiMulti.run() != WL_CONNECTED) {
    Serial.println("Conexão perdida! Tentando reconectar...");
    delay(1000);
  }

/*
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Reconectando...");
    conectar_wifi();
  }

*/

  if (!mqttClient.connected()) {
    conectar_mqtt();
  }
  mqttClient.loop();   // processa mensagens MQTT pendentes

  // Verifica se chegou pacote DL via MQTT e o envia pelo rádio LoRa
  Phy_mqtt_receive_DL();


  // Verifica se chegou pacote UL via rádio LoRa e o publica no broker
  Phy_radio_receive_UL();
  
}

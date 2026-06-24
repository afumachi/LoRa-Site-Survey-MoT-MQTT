/*
  MoT LoRa Site Survey Versão Configra Rádio | WissTek IoT
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

  Serial.begin(TAXA_SERIAL);
  // Aguarda para estabilização da Serial
  delay(200);

  // declara Leds como saídas digital do ESP32
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  pinMode(PIN_LED_AMARELO, OUTPUT);  
  pinMode(PIN_LED_VERDE, OUTPUT);

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

  // --- Aplica as Configurações de Rádio LoRa ---
//  LoRa.setTxPower(txPower);
//  LoRa.setSpreadingFactor(spreadingFactor);
//  LoRa.setSignalBandwidth(signalBandwidth);
//  LoRa.setCodingRate4(codingRateDenominator);

  //  --- Atua Led vermelho  --- 
  digitalWrite(PIN_LED_VERMELHO, HIGH); // LIGA LED VERMELHO - INDIFERENTE PARA O BOOT

  //  --- Atua Led amarelo  --- 
  digitalWrite(PIN_LED_AMARELO, HIGH); // LIGA O LED AMARELO - DEVE SER HIGH DURANTE BOOT

  //  --- Atua Led verde  --- 
  digitalWrite(PIN_LED_VERDE, LOW);  // DESLIGA O LED VERDE - DEVE SER LOW DURANTE BOOT

  // Escreve no Serial Monitor que o Nó Sensor iniciou com sucesso
  Serial.println("[Nó Sensor LoRa Iniciado]");
  
  // Aguarda 1 segundo para estabilização
  delay(1000);

  //  --- Atua Led vermelho  --- 
  digitalWrite(PIN_LED_VERMELHO, LOW); // DESLIGA LED VERMELHO

  //  --- Atua Led amarelo  --- 
  digitalWrite(PIN_LED_AMARELO, LOW); // DESLIGA O LED AMARELO

  //  --- Atua Led verde  --- 
  digitalWrite(PIN_LED_VERDE, LOW);  // DESLIGA O LED VERDE

  #ifdef loraCRC   // Habilitação do CRC do chip lora  (Configurado em bibliotecas.h)
    LoRa.enableCrc();
  #endif

} // FIM DO SETUP

//=======================================================================
//  ------------ 4 - Loop de repetição ------------
//=======================================================================
// A função loop irá executar repetidamente
void loop() {
  
  // --- Controle de timeout do Comando 4 ---
  // Executado a cada iteração do loop, independente de novo pacote chegar
  if (controle_ativo) {
    unsigned long tempo_limite_ms = (unsigned long)tempo_radio * 10UL * 1000UL; // 10x o valor recebido em MAC3_TEMPO

    if (millis() - millis_inicio_controle >= tempo_limite_ms) {
      reset_para_setup_inicial(); // Timeout atingido → volta ao SETUP
    }
  }
   
  unsigned long tempo_standby_ms = 10UL * time_out_lora; // 1 min. sem Pacotes DL sobe para MAX  

  if (millis() - millis_standby_controle >= tempo_standby_ms) {
    Serial.println("TEMPO SEM RECEBER PACOTES - Time-Out");
    Serial.println("Voltando a Configuração LoRa BDC");

    millis_standby_controle = millis();
    reset_para_setup_inicial(); // Timeout atingido → volta ao SETUP

  }  
  
  Phy_radio_receive_DL(); // Função que recebe os pacotes pelo rádio
  //delay(2); // Para preservar o processamento do ESP32
}

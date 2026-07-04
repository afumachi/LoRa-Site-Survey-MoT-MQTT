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

  // Configuração ADC para o LDR
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  pinMode(PIN_LDR, INPUT);

  // GPS Serial: Baud 9600, Pins: RX=16, TX=17
  SerialGPS.begin(9600, SERIAL_8N1, 16, 17);

  // Initialize I2C with your specific pins (SDA = 21, SCL = 22)
  Wire.begin(21, 22);
  delay(100);

  // Initialize OLED display
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // 0x3C is common I2C address
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); 
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  delay(100);

  dht.begin();
  delay(200);


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

  // Limpa o Display
  display.clearDisplay();
    
  // Escreve o Título Display
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("PKLoRa Site Survey");
  display.drawLine(0, 12, 128, 12, SSD1306_WHITE);    

  // Escreve valor do LDR
  display.setTextSize(1);
  display.setCursor(0, 17);
  display.println("PKLoRa Inicializado");
  display.println("");  
  display.setTextSize(2);
  display.println("SUCESSO!"); 

  // Escreve o buffer na tela Oled
  display.display();

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


    // Lê os caracteres do GPS a cada 200 [ms]
    unsigned long tempo_sensores_ms = 200UL; // 200 ms

    if (millis() - millis_gps_controle >= tempo_sensores_ms) {        
        updateGPS(); // Atualiza / Lê GPS
        //Serial.println("FUNÇÃO UPDATE GPS");  
        // Zera contagem do tempo de controle GPS para tempo de ESP32 rodando
        millis_gps_controle = millis(); 
    }

    if (millis() - millis_dht22_controle >= tempo_sensores_ms) {        
        LE_DHT(temperatura, umidade);
        // Zera contagem do tempo de controle GPS para tempo de ESP32 rodando
        millis_dht22_controle = millis(); 
    }

  if ((confirma_novo_radio_base != 4) & (confirma_novo_radio_base != 5)){ 
    millis_contador_DL = millis();
  }

  Phy_radio_receive_DL(); // Função que recebe os pacotes pelo rádio


}

//==================================================================================================================
//======================= PACOTE DOWN LINK - PACOTE VINDO DO PYTHON PARA SER ENVIADO AO NÓ SENSOR ===========================
//==================================================================================================================
// Pacote proveniente do Python pela serial deve ser enviado para o nó sensor. Primeiro o pacote é recebido pela serial USB e depois é encaminhado para o RF95
// ----------------------LEITURA DO BUFFER RX DA SERIAL PACOTE VINDO DA MAC DO PYTHON PARA DL----------------------------------------------------------------------------------------------------//

// ============================================================
// RECEBE PACOTE DL DA SERIAL E ENVIA PELO RÁDIO
// ============================================================

// ========================= PACOTE DOWN LINK ==========================
// Recebe pacote DL do broker MQTT (publicado pelo Python)
void Phy_mqtt_receive_DL() {

  // Parâmetros do LoRa caso primeira energização do módulo NodeMCU/ESP32
  if (primeiro_setup == 1) {
    LoRa.sleep();
    LoRa.setTxPower(txPower);
    LoRa.setSpreadingFactor(spreadingFactor);
    LoRa.setSignalBandwidth(signalBandwidth);
    LoRa.setCodingRate4(codingRateDenominator);
    LoRa.idle();  // Retorna ao modo standby/recepção

    Serial.println("SETUP INICIAL - Gateway LoRa Best Distance Configuration");
    // Zera flags e variáveis de controle
    aguardando_confirmacao_UL    = false;
    millis_inicio_aguarda_UL     = 0;
    tempo_radio                  = 0;
    recebe_comando_nova_radio    = 0;
    confirma_novo_radio_sensor   = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    contadorDL = 0;
    contadorSS = 0;
    primeiro_setup = 0;
  }



  if (mqtt_dl_disponivel) {          // Flag setada no callback MQTT
    mqtt_dl_disponivel = false;

    // Copia payload recebido para PacoteDL
    for (int i = 0; i < TAMANHO_PACOTE; i++) {
      PacoteDL[i] = mqtt_dl_payload[i];
    }

    // ADICIONADO Variáveis de recebimento do valores de rádio LoRa
    valor_novo_spreadingfactor = PacoteDL[0];  // Byte DL[0] valor de rádio LoRa de Spreading Spectrum
    valor_novo_bandwidth = PacoteDL[1];        // Byte DL[1] valor de rádio LoRa de Bandwidth

    // Configura Valor de Bandwidth de acordo com o valor recebido no Byte[1]
    if (valor_novo_bandwidth == 3) {
      valor_novo_bandwidth = 500E3;
    } else if (valor_novo_bandwidth == 2) {
      valor_novo_bandwidth = 250E3;
    } else if (valor_novo_bandwidth == 1) {
      valor_novo_bandwidth = 125E3;
    }

    valor_novo_codingrate = PacoteDL[2];         // Byte DL[2] valor de rádio LoRa de CodingRate
    valor_novo_potencia_radio = PacoteDL[3];     // Byte DL[3] valor de rádio LoRa de Potência de Rádio LoRa
    tempo_radio = PacoteDL[MAC3_TEMPO];                // Byte DL[6] Recebe tempo de radio tx rx
    recebe_comando_nova_radio = PacoteDL[MAC4_COMANDO];  // Byte DL[7] Recebe comando de reconfiguração de Rádio LoRa
    contadorSS = (((PacoteDL[MAC_COUNTER_MSB])*256) + (PacoteDL[MAC_COUNTER_LSB]));

    // Nivel 3 manda voltar para PRIMEIRO SETUP
    if (recebe_comando_nova_radio == 10){
      confirma_novo_radio_base = 10;
      Phy_mqtt_send_UL();
    }

    if (confirma_novo_radio_base != 10){
      // ----------------------ENVIO DO PACOTE DE DOWN LINK ATRAVÉS DO RF95----------------------------------------------------------------------------------------------------//
      Phy_radio_send_DL();  // chama a funcao de recepcao da camada de controle de acesso ao meio
    }
  }
}

//========================= ENVIA PACOTE DL PARA NÓ SENSOR ATRAVÉS DO RF95
//O pacote DL recebido pela serial proveniente do Nível 3 é enviado para o RF95
void Phy_radio_send_DL() {

  // Pisca o LED de transmissão de pacote DL
  digitalWrite(PIN_LED_VERMELHO, HIGH);  // Início da Transmissão

  LoRa.beginPacket();  // start packet
  for (int i = 0; i < TAMANHO_PACOTE; i++) {
    LoRa.write(PacoteDL[i]);  // add data to packet
  }
  LoRa.endPacket();  // finish packet and send it

  // Pisca o LED de transmissão de pacote DL
  digitalWrite(PIN_LED_VERMELHO, LOW);  // FIM da Transmissão

}

//==================================================================================================================
//======================= PACOTE UL LINK - PACODE VINDO NÓ SENSOR ENCAMINHADO PARA PYTHON===========================
//==================================================================================================================
// Pacote que chega no RF95 vindo do nó sensor e é passado para o buffer de TX da serial
//--------------------------- RECEBE PACOTE UL VINDO DO NÓ SENSOR ATRAVÉS DO MÓDULO RF95

void Phy_radio_receive_UL() {
  

  // Escuta o Rádio LoRa se identificou algum Pacote
  uint8_t packetSize = LoRa.parsePacket();

  // Caso positivo, identifica o tamanho do Payload do Pacote
  if (packetSize) {

    digitalWrite(PIN_LED_VERDE, HIGH);  // Apaga Led Verde Indicando Inicio da leitura do Pacote

    // Realiza a leitura caso Payload do Pacote seja compatível com o Pacote de 52 Bytes
    if (packetSize >= TAMANHO_PACOTE) {

      for (int i = 0; i < TAMANHO_PACOTE; i++) {
        PacoteUL[i] = LoRa.read();
      }

      RSSI_dBm_UL = LoRa.packetRssi();
      SNR_UL_bruto = LoRa.packetSnr();

      //===================================== IMPORTANTE - OPÇÃO VERIFICAÇÃO DE ENDEREÇO OU MODO PROMÍSCUO========================
      // Quando recebe o pacote a base pode verificar o endereço de destino ou trabalhar em modo promíscuo.
      //===================== QUANDO A BASE  VERIFICA O ENDENREÇO DE DESTINO O PACOTE SÓ É ENVIADO PARA A SERIAL CASO A BASE SEJA O DESTINATÁRIO - nesse caso descomentar o bloco abaixo
      // Esta é uma função originalmente da camada de rede, mas existe um cross-layer para verificação do endereço de destino, recebendo somente os pacotes que são destinados para a base

      //delay(100);
      digitalWrite(PIN_LED_VERDE, LOW);  // Fim da leitura do Pacote
      Serial.println("Pacote UPLINK Recebido");
      if (PacoteUL[RECEIVER_ID] == MY_ID) {
        // Garante que Nó Sensor também recebeu comando de alteração de rádio e confirmou
        confirma_novo_radio_sensor = PacoteUL[MAC4_COMANDO];  // PacoteUL[7] recebe confirmação do nó sensor do recebimento


        // --- Confirmação UL recebida: cancela o timeout ---
        if (aguardando_confirmacao_UL) {
          aguardando_confirmacao_UL = false;
          millis_inicio_aguarda_UL  = 0;

//          //Serial.print("[GATEWAY] Confirmação UL recebida do sensor. MAC4_COMANDO=");
//          //Serial.println(confirma_novo_radio_sensor);
        }

        Mac_radio_receive_DL();
        //Phy_serial_send_UL();  //Chama a função de envio da Camada Física
      }
    }
  }
}


// ==================== PUBLICA PACOTE UL NO BROKER MQTT ==============
// Substitui Phy_serial_send_UL(): envia o pacote UL ao Python via MQTT
void Phy_mqtt_send_UL() {

  // Calcula RSSI linear e aloca em 1 Byte conforme Documentação RFM95 de -10,5 dBm a -138dBm

  // Determina o offset baseado na frequência usada
  // (Ajuste para 164 se estiver usando 433MHz)
  int offset = 157; // Offset 157 para Frequência de 915MHz

  // Recupera o valor bruto (PacketRssi) para aplicar a nova fórmula
  int Rssi_UL_bruto = RSSI_dBm_UL + offset;

  if (SNR_UL_bruto >= 0) {
    // Sua fórmula com correção de linearidade (16/15)
    RSSI_dBm_UL = ((1.0666 * Rssi_UL_bruto) - offset); // 16/15 * RSSI - 157
  } else {
    // Fórmula para sinal abaixo do ruído (SNR < 0)
    RSSI_dBm_UL = ((Rssi_UL_bruto - offset) + (SNR_UL_bruto));
  }  



  //--- Bloco que faz adequação da leitura de RSSI para um byte ---
  if (RSSI_dBm_UL > -10.5)   // Caso a RSSI medida esteja acima do valor superior -10,5 dBm
  {
    RSSI_UL = 127;  // equivalente a -10,5 dBm
  }

  if (RSSI_dBm_UL <= -10.5 && RSSI_dBm_UL >= -74)  // Caso a RSSI medida esteja no intervalo [-10,5 dBm e -74 dBm]
  {
    RSSI_UL = ((RSSI_dBm_UL + 74) * 2);
  }

  if (RSSI_dBm_UL < -74)  // Caso a RSSI medida esteja no intervalo ]-74 dBm e -138 dBm]
  {
    RSSI_UL = (((RSSI_dBm_UL + 74) * 2) + 256);
  }


  // Insere (sobrescreve) o valor em 1 byte do pacote com o valor calculado de SNR (de -20dB a + 20dB)
  // Processa SNR no range de -20.0 dB a +20.0 dB com offset de 30 para um valor inteiro alocando em 1 Bytes

  //20,5+30 = 50,5
  //50,5*4 = 202

  //-20,5+30 = 9,5
  //9,5 * 4 = 38

  SNR_UL = int((SNR_UL_bruto + 30) * 4);

  if (SNR_UL >= 255){
    SNR_UL = 255;
  }

  if (SNR_UL <= 0){
    SNR_UL = 0;
  }
  
  // =================Informações de gerência do pacote
  PacoteUL[2] = RSSI_UL;  // aloca RSSI_UL
  PacoteUL[3] = SNR_UL;

  if (confirma_novo_radio == 1) {
    AplicarConfiguracoesRadio();
  }

  if (confirma_novo_radio_base == 10){
    //RetornaConfiguracoesRadioMAX();
    Serial.println("Perda Enlace Nó Sensor - Retorna Configuracoes Radio MAX");
    // Para limpar:
    memset(PacoteUL, 0, sizeof(PacoteUL));
    //delay(200);
    PacoteUL[RECEIVER_ID] = 0;
    PacoteUL[MAC4_COMANDO] = 10;
    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    contadorDL = 0;
    contadorSS = 0;

    reset_gateway_para_setup_inicial();
 
  }


  // --- Publica os 20 bytes no tópico UL ---
  if (mqttClient.connected()) {
    mqttClient.publish(TOPIC_UL, PacoteUL, TAMANHO_PACOTE);
    //Serial.println("[PHY] Pacote UL publicado via MQTT.");
  } else {
    Serial.println("[PHY] MQTT desconectado – pacote UL descartado.");
  }


  if (confirma_novo_radio == 5){
    contadorDL = 0;
  } 

}

void AplicarConfiguracoesRadio() {

  if (confirma_novo_radio == 1) {

    LoRa.sleep();                                         // Coloca em sleep para garantir a mudança de parâmetros
    LoRa.setTxPower(valor_novo_potencia_radio);           // Potência de Transmissão (Configurado em bibliotecas.h)
    LoRa.setSpreadingFactor(valor_novo_spreadingfactor);  // Fator de Espalhamento  (Configurado em bibliotecas.h)
    LoRa.setSignalBandwidth(valor_novo_bandwidth);        // Banda do Sinal (Configurado em bibliotecas.h)
    LoRa.setCodingRate4(valor_novo_codingrate);           // Coding Rate  (Configurado em bibliotecas.h)
    LoRa.idle(); 
    //delay(2);                                         // Retorna ao modo standby/recepção

    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    primeiro_setup = 0;
  }
}


// ============================================================
// FUNÇÃO AUXILIAR - Reseta estado para aguardar novo downlink serial
// ============================================================

void reset_gateway_para_setup_inicial() {

  // Zera flags e variáveis de controle
  aguardando_confirmacao_UL    = false;
  millis_inicio_aguarda_UL     = 0;
  tempo_radio                  = 0;
  recebe_comando_nova_radio    = 0;
  confirma_novo_radio_sensor   = 0;
  confirma_novo_radio_base = 0;
  confirma_novo_radio = 0;
  contadorDL = 0;
  contadorSS = 0;

  // Retorna rádio aos parâmetros de SETUP
  primeiro_setup = 1;
  PacoteUL[MAC4_COMANDO] = 10; // Gateway Resetou para Máxima
}



// =====================================================================
//                     9 - Callback MQTT (recepção de mensagens)
// =====================================================================
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  if (strcmp(topic, TOPIC_DL) == 0) {
    if (length >= TAMANHO_PACOTE) {
      for (int i = 0; i < TAMANHO_PACOTE; i++) {
        mqtt_dl_payload[i] = payload[i];
      }
      mqtt_dl_disponivel = true;   // sinaliza para o loop principal
    }
  }
}

// =====================================================================
//                    10 - Funções auxiliares de conexão
// =====================================================================

/*
void conectar_wifi() {
  Serial.print("[WiFi] Conectando à rede: ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int tentativas = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    tentativas++;
    if (tentativas > 40) {   // 20 segundos
      Serial.println("\n[WiFi] Timeout. Reiniciando...");
      ESP.restart();
    }
  }
  Serial.println();
  Serial.print("[WiFi] Conectado! IP: ");
  Serial.println(WiFi.localIP());
}
*/
void conectar_mqtt() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Conectando ao broker...");
    if (mqttClient.connect(CLIENT_ID.c_str())) {
      Serial.println(" conectado!");
      mqttClient.subscribe(TOPIC_DL);
      Serial.print("[MQTT] Inscrito em: ");
      Serial.println(TOPIC_DL);
    } else {
      Serial.print(" falhou (rc=");
      Serial.print(mqttClient.state());
      Serial.println("). Tentando em 3s...");
      delay(3000);
    }
  }
}



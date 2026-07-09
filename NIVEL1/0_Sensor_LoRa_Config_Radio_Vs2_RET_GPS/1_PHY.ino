void Phy_radio_receive_DL() {

  // Parâmetros do LoRa caso primeira energização do módulo NodeMCU/ESP32
  if (primeiro_setup == 1){
    //Serial.println("Primeiro SETUP");
    LoRa.sleep();
    LoRa.setTxPower(txPower);
    LoRa.setSpreadingFactor(spreadingFactor);
    LoRa.setSignalBandwidth(signalBandwidth);
    LoRa.setCodingRate4(codingRateDenominator);
    LoRa.idle(); // Retorna ao modo standby/recepção

    primeiro_setup = 0;
    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;

    Serial.println("SETUP INICIAL - Rádio LoRa Best Distance Configuration");

  }

  // Neste ponto zeramos o pacote de DL para garantir que ele não está carregando nenhuma informação de comunicação anterior.
  for (int i = 0; i < TAMANHO_PACOTE; i++) {
    PacoteDL[i] = 0;    
  }
  
  
  // Escuta o Rádio LoRa se identificou algum preâmbulo de Pacote
  uint8_t packetSize = LoRa.parsePacket();

  // Caso positivo, identifica o tamanho do Payload do Pacote
  if (packetSize) {
    
    digitalWrite(PIN_LED_VERDE, HIGH); // Liga Led Verde Indicando Inicio da leitura do Pacote
    //Serial.println("Pacote DL IDENTIFICADO");
    // Realiza a leitura caso Payload do Pacote seja compatível com o Pacote de 6 Bytes
    if (packetSize >= TAMANHO_PACOTE) {
      //Serial.println("Pacote DL >= TAMANHO_PACOTE");

      millis_standby_controle = millis();

      for (int i = 0; i < TAMANHO_PACOTE; i++) {
        PacoteDL[i] = LoRa.read();  // Aloca no Pacote de DL os 6 bytes que vieram do RFM95
      }

      RSSI_dBm_DL = LoRa.packetRssi();
      SNR_DL_bruto = LoRa.packetSnr();

      //delay(10);
      // ADICIONADO Variáveis de recebimento do valores de rádio LoRa
      valor_novo_spreadingfactor = PacoteDL[0]; // Byte DL[0] valor de rádio LoRa de Spreading Spectrum
      valor_novo_bandwidth = PacoteDL[1]; // Byte DL[1] valor de rádio LoRa de Bandwidth

      // Configura Valor de Bandwidth de acordo com o valor recebido no Byte[1]
      if (valor_novo_bandwidth == 3){
        valor_novo_bandwidth = 500E3;
      }
      else if (valor_novo_bandwidth == 2){
        valor_novo_bandwidth = 250E3;
      }
      else if (valor_novo_bandwidth == 1){
        valor_novo_bandwidth = 125E3;
      }

      valor_novo_codingrate = PacoteDL[2]; // Byte DL[2] valor de rádio LoRa de CodingRate
      valor_novo_potencia_radio = PacoteDL[3]; // Byte DL[3] valor de rádio LoRa de Potência de Rádio LoRa

      // Leitura dos bytes MAC de tempo e comando
      tempo_radio               = PacoteDL[MAC3_TEMPO];
      recebe_comando_nova_radio = PacoteDL[MAC4_COMANDO];


      // --- Lógica de inicio da contagem para MAC4_COMANDO == 4 ---
      if (recebe_comando_nova_radio != 0) {

        if (!controle_ativo) {
          // Primeira vez que recebe o comando 4: inicia a contagem
          millis_inicio_controle = millis();
          controle_ativo         = true;

          Serial.print("[CONTROLE] Contagem iniciada. Tempo limite: ");
          //Serial.print((unsigned long)tempo_radio * 10UL * 1000UL);
          //Serial.println(" ms");

        } else {
          // Pacote com comando chegou novamente enquanto contagem ativa:
          // Reinicia a contagem com o novo tempo recebido
          millis_inicio_controle = millis();

          Serial.print("[CONTROLE] Contagem reiniciada. Novo tempo limite: ");
          //Serial.print((unsigned long)tempo_radio * 10UL * 1000UL);
          //Serial.println(" ms");
        }

      } else {
        // Chegou um pacote com comando diferente de 4: cancela contagem ativa
        if (controle_ativo) {
          Serial.println("[CONTROLE != 0] Contagem cancelada.");
          controle_ativo = false;
          millis_inicio_controle = 0;
        }
      }

      digitalWrite(PIN_LED_VERDE, LOW); // Fim da leitura do Pacote

      // Caso Pacote direcionado a este sensor, chama função MAC
      Mac_radio_receive_DL();

    }
  }
}  

//================ ENVIA O PACOTE UL ========
void Phy_radio_send_UL() {


  RSSI_dBm_DL = LoRa.packetRssi();
  SNR_DL_bruto = LoRa.packetSnr();

  // Determina o offset baseado na frequência usada
  // (Ajuste para 164 se estiver usando 433MHz)
  int offset = 157; // Offset 157 para Frequência de 915MHz

  // Recupera o valor bruto (PacketRssi) para aplicar a nova fórmula
  int Rssi_DL_bruto = RSSI_dBm_DL + offset;

  if (SNR_DL_bruto >= 0) {
    // Sua fórmula com correção de linearidade (16/15)
    RSSI_dBm_DL = ((1.0666 * Rssi_DL_bruto) - offset); // 16/15 * RSSI - 157
  } else {
    // Fórmula para sinal abaixo do ruído (SNR < 0)
    RSSI_dBm_DL = ((Rssi_DL_bruto - offset) + (SNR_DL_bruto));
  }  


  //--- Bloco que faz adequação da leitura de RSSI para um byte ---

  if(RSSI_dBm_DL > -10.5)  // Caso a RSSI medida esteja acima do valor superior -10,5 dBm
  {
   RSSI_DL = 127; // equivalente a -10,5 dBm 
  }

  if(RSSI_dBm_DL <= -10.5 && RSSI_dBm_DL >= -74) // Caso a RSSI medida esteja no intervalo [-10,5 dBm e -74 dBm]
  {
   RSSI_DL = ((RSSI_dBm_DL +74)*2) ;
  }

  if(RSSI_dBm_DL < -74) // Caso a RSSI medida esteja no intervalo ]-74 dBm e -138 dBm]
  {
   RSSI_DL = (((RSSI_dBm_DL +74)*2)+256) ;
  }

  // 1. Trava o valor entre -30 e +30 para evitar que o byte estoure
  if (SNR_DL_bruto < -30.0) SNR_DL_bruto = -30.0;
  if (SNR_DL_bruto > 30.0) SNR_DL_bruto = 30.0;

  // Usamos uint8_t (byte) para ocupar apenas 1 byte na memória.
  // Usamos a função round() para garantir que o número float seja 
  // arredondado corretamente antes de virar inteiro.
  SNR_DL = (uint8_t)round((SNR_DL_bruto + 30.0) * 4.0); // Offset de 30.0dB e passo de 0.25dB (* 4.0)

  // =================Informações de gerência do pacote Início da montagem do pacote de UL
  PacoteUL[0] = RSSI_DL;
  PacoteUL[1] = SNR_DL;

  // Pisca o LED de transmissão de pacote UL
  digitalWrite(PIN_LED_VERMELHO, HIGH); // Início da Transmissão

  LoRa.beginPacket();                 // Inicia o envio do pacote ao rádio
  for (int i = 0; i < TAMANHO_PACOTE; i++) {
    LoRa.write(PacoteUL[i]);          // Envia byte a byte as informações para o Rádio
  }
  LoRa.endPacket();                   // Finaliza o envio do pacote

  digitalWrite(PIN_LED_VERMELHO, LOW); // Fim da Transmissão

  display.setTextSize(1);
  display.setCursor(0, 48);
  display.print("RSSI_DL: ");
  display.setTextSize(1);
  display.print(RSSI_dBm_DL); // 1 decimal place
  display.println(" dBm"); // 1 decimal place
  display.setTextSize(1);
  display.print("SNR_DL : ");
  display.setTextSize(1);
  display.print(SNR_DL_bruto); // 1 decimal place
  display.println(" dB"); // 1 decimal place
  // Escreve o buffer na tela Oled
  display.display();

  // Realiza a alteração das config. da Rádio LoRa apenas após o envio do segundo Pacote UL, 
  // e prepara o Nó Sensor para o terceiro ciclo já com as alterações realizadas
  if (confirma_novo_radio == 1){
    AplicarConfiguracoesRadio();
  }

}

// ============================================================
// FUNÇÃO AUXILIAR - Reseta estado para aguardar novo downlink
// ============================================================

void reset_para_setup_inicial() {
  Serial.println("[TIMEOUT] Tempo expirado! Resetando para SETUP inicial...");

  // Zera flag de contagem e variáveis de controle
  controle_ativo          = false;
  millis_inicio_controle  = 0;
  tempo_radio             = 0;
  recebe_comando_nova_radio = 0;
  confirma_novo_radio_sensor = 0;
  confirma_novo_radio_base = 0;
  confirma_novo_radio = 0;
  contador_perda_DL = 0;
  //contadorUL = 0;
  //contadorDL = 0;

  // Retorna rádio aos parâmetros de SETUP (primeiro_setup = 1 dispara o bloco de SETUP em Phy_radio_receive_DL)
  primeiro_setup = 1;
}


void RetornaConfiguracoesRadioMAX(){
  
  if (confirma_novo_radio == 5){
    primeiro_setup = 0;
    LoRa.sleep(); // Coloca em sleep para garantir a mudança de parâmetros
    LoRa.setTxPower(valor_novo_potencia_radio);                       // Potência de Transmissão (Configurado em bibliotecas.h)
    LoRa.setSpreadingFactor(valor_novo_spreadingfactor);       // Fator de Espalhamento  (Configurado em bibliotecas.h)
    LoRa.setSignalBandwidth(valor_novo_bandwidth);       // Banda do Sinal (Configurado em bibliotecas.h)
    LoRa.setCodingRate4(valor_novo_codingrate);     // Coding Rate  (Configurado em bibliotecas.h)
    LoRa.idle(); // Retorna ao modo standby/recepção


    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    primeiro_setup = 0;

    //Serial.println("Configurações de rádio atualizadas para MÁXIMO.");

  }  
}




void AplicarConfiguracoesRadio() {

  if (confirma_novo_radio == 1){

    LoRa.sleep(); // Coloca em sleep para garantir a mudança de parâmetros
    LoRa.setTxPower(valor_novo_potencia_radio);                       // Potência de Transmissão (Configurado em bibliotecas.h)
    LoRa.setSpreadingFactor(valor_novo_spreadingfactor);       // Fator de Espalhamento  (Configurado em bibliotecas.h)
    LoRa.setSignalBandwidth(valor_novo_bandwidth);       // Banda do Sinal (Configurado em bibliotecas.h)
    LoRa.setCodingRate4(valor_novo_codingrate);     // Coding Rate  (Configurado em bibliotecas.h)
    LoRa.idle(); // Retorna ao modo standby/recepção

    confirma_novo_radio_sensor = 0;
    confirma_novo_radio_base = 0;
    confirma_novo_radio = 0;
    recebe_comando_nova_radio = 0;
    primeiro_setup = 0;
    //contadorUL = 0;
    //contadorSS = 0;

    Serial.println("APLICADA - Modificação de rádio");

  }  

}



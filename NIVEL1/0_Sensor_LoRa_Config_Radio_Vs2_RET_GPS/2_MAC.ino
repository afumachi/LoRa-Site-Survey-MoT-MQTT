//================ RECEBE O PACOTE DA CAMADA FÍSICA ========
void Mac_radio_receive_DL() { 
  // Aqui pode ser adicionado o Sleep Mode

  //tempo_radio = PacoteDL[MAC3_TEMPO]; // Byte DL[6] Recebe tempo de radio tx rx
  //recebe_comando_nova_radio = PacoteDL[MAC4_COMANDO]; // Byte DL[7] Recebe comando de reconfiguração de Rádio LoRa
  contadorSS = (((PacoteDL[MAC_COUNTER_MSB])*256) + (PacoteDL[MAC_COUNTER_LSB]));

  // Primeiro ciclo
    /*
    if (recebe_comando_nova_radio == 1){
      confirma_novo_radio_sensor = 1;
     // Serial.print("MAC Sensor - Confirma CICLO 1");
    }
    */
    if ((recebe_comando_nova_radio == 1)){
      //& ((valor_novo_spreadingfactor != valor_atual_spreadingfactor) || (valor_novo_bandwidth != valor_atual_bandwidth) || (valor_novo_codingrate != valor_atual_codingrate) || (valor_novo_potencia_radio != valor_atual_potencia_radio))){
        Serial.println("[RECONFIGURACAO DE RADIO RECEBIDO]");
        confirma_novo_radio_sensor = 2;
        
        valor_anterior_spreadingfactor = valor_atual_spreadingfactor;
        valor_anterior_bandwidth = valor_atual_bandwidth;
        valor_anterior_codingrate = valor_atual_codingrate;
        valor_anterior_potencia_radio = valor_atual_potencia_radio;

        valor_atual_spreadingfactor = valor_novo_spreadingfactor;
        valor_atual_bandwidth = valor_novo_bandwidth;
        valor_atual_codingrate = valor_novo_codingrate;
        valor_atual_potencia_radio = valor_novo_potencia_radio;

        //Serial.print("MAC Sensor - Confirma CICLO 2");
    }
    //era 3
    if (recebe_comando_nova_radio == 3){
      Serial.println("[TESTE ENLACE RECEBIDO]");
      confirma_novo_radio_sensor = 3;
      //Serial.print("MAC Sensor - Confirma CICLO SITE SURVEY");
    }
    if (recebe_comando_nova_radio == 4){
      Serial.println("[LSS EM ANDAMENTO]");
      confirma_novo_radio_base = 4;
    }    
    if (recebe_comando_nova_radio == 5){
      Serial.println("[LSS - ÚLTIMO PACOTE]");
      confirma_novo_radio_sensor = 5;
     // Serial.print("MAC Sensor - Confirma ÚLTIMO PACCOTE CICLO SITE SURVEY");
    }
    
    Net_radio_receive_DL();

}

//================ ENVIA O PACOTE À CAMADA FÍSICA ========
void Mac_radio_send_UL() {
  // Aqui pode ser adicionado o Sleep Mode

  // Caso Nó Sensor Devices recebeu comando de alteração de config. de rádio escreve no Byte[11] para a Base LoRa
  // confirmação do primeiro ciclo  
  if (confirma_novo_radio_sensor == 1){
    PacoteUL[MAC4_COMANDO] = 1;
    Serial.println("MAC - PacoteUL[7] - CICLO : ");
    Serial.println(confirma_novo_radio_sensor);
    confirma_novo_radio = 0;
  
  }
  else if (confirma_novo_radio_sensor == 2){
    // Confirmação do segundo ciclo para alteração das config. de rádio do Nó Sensor
    PacoteUL[MAC4_COMANDO] = 2;
    Serial.println("MAC - PacoteUL[7] - RECONFIGURA RADIO : ");
    Serial.println(confirma_novo_radio_sensor);
    confirma_novo_radio = 1; // Habilita Nó Sensor a alterar as configurações de Rádio
    
  }
  else if (confirma_novo_radio_sensor == 3){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[MAC4_COMANDO] = 3;
    Serial.println("MAC - PacoteUL[7] - TESTE ENLACE: ");
    //Serial.println(confirma_novo_radio_sensor);
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 0;
  }
  else if (confirma_novo_radio_sensor == 4){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[MAC4_COMANDO] = 4;
    Serial.println("MAC - PacoteUL[7] - CICLO SITE SURVEY: ");
    //Serial.println(confirma_novo_radio_sensor);
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 0;
  }
  else if (confirma_novo_radio_sensor == 5){
    //  Confirmação do terceiro ciclo confirmando a alteração das config. de rádio do Nó Sensor
    PacoteUL[MAC4_COMANDO] = 5;
    Serial.print("MAC - PacoteUL[7] - ÚLTIMO CICLO SITE SURVEY: ");
    //Serial.println(confirma_novo_radio_sensor);
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 0;
      // Zera flag de contagem e variáveis de controle
    controle_ativo          = false;
    millis_inicio_controle  = 0;
    tempo_radio             = 0;

    confirma_novo_radio_base = 0;

    contadorDL = 0;
    contadorSS = 0;
    contadorUL = 0;
    contador_perda_DL = 0;
  }
  else {
    // Sem necessidade de alteração, ou confirmação de alteração
    PacoteUL[MAC4_COMANDO] = 0;
    recebe_comando_nova_radio = 0;
    confirma_novo_radio = 0;
    confirma_novo_radio_sensor = 0;
    //Serial.print("MAC - PacoteUL[7] - SEM CICLO : ");
    //Serial.println(confirma_novo_radio_sensor);
  }

  //Serial.print("Contador Site Survey: ");
  //Serial.println(contadorSS);
  //Serial.print("Contador Pacotes UL: ");
  //Serial.println(contadorUL);

/*
  if (contadorUL == contadorSS){
    confirma_novo_radio = 5;
  }

*/

  Phy_radio_send_UL();
}

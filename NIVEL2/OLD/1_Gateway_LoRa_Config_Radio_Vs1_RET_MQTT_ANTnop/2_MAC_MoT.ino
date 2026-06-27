//================ RECEBE O PACOTE DA CAMADA FÍSICA ========
void Mac_radio_receive_DL() { 
  // Aqui pode ser adicionado o Sleep Mode
 
    
    if (recebe_comando_nova_radio == 1){
      confirma_novo_radio_base = 1;
    }
    if ((recebe_comando_nova_radio == 2) ){
      //& ((valor_novo_spreadingfactor != valor_atual_spreadingfactor) || (valor_novo_bandwidth != valor_atual_bandwidth) || (valor_novo_codingrate != valor_atual_codingrate) || (valor_novo_potencia_radio != valor_atual_potencia_radio))){
        confirma_novo_radio_base = 2;
        
        valor_anterior_spreadingfactor = valor_atual_spreadingfactor;
        valor_anterior_bandwidth = valor_atual_bandwidth;
        valor_anterior_codingrate = valor_atual_codingrate;
        valor_anterior_potencia_radio = valor_atual_potencia_radio;

        valor_atual_spreadingfactor = valor_novo_spreadingfactor;
        valor_atual_bandwidth = valor_novo_bandwidth;
        valor_atual_codingrate = valor_novo_codingrate;
        valor_atual_potencia_radio = valor_novo_potencia_radio;
    }
    if (recebe_comando_nova_radio == 3){
      confirma_novo_radio_base = 3;
    }
    if (recebe_comando_nova_radio == 5){
      // site survey status
      confirma_novo_radio_base = 5;
    }

    Mac_radio_send_UL();

}

//================ ENVIA O PACOTE À CAMADA FÍSICA ========
void Mac_radio_send_UL() {
  // Aqui pode ser adicionado o Sleep Mode

 // Caso ambos Devices receberam comando de alteração de config. de rádio escreve no Byte[11] para Nível 3
  // confirmação do primeiro ciclo
  if ((confirma_novo_radio_base == 1) & (confirma_novo_radio_sensor == 1)){
    PacoteUL[MAC4_COMANDO] = 2;
    confirma_novo_radio = 0;
  }
  else if ((confirma_novo_radio_base == 2) & (confirma_novo_radio_sensor == 2)){
    // Confirmação do segundo ciclo de ambos devices
    primeiro_setup = 0;
    PacoteUL[MAC4_COMANDO] = 3;
    confirma_novo_radio = 1;
  }
  else if ((confirma_novo_radio_base == 3) & (confirma_novo_radio_sensor == 3)){
    // Confirmação do terceiro ciclo de ambos devices já com Nova Configuração de Rádio
    PacoteUL[MAC4_COMANDO] = 4;
    confirma_novo_radio = 0;    
  }
  else if ((confirma_novo_radio_base == 1) & (confirma_novo_radio_sensor == 0)){
    // Indica ao Nível 3 que apenas um dos Devices LoRa (Base) recebeu/processou o Comando de alteração
    PacoteUL[MAC4_COMANDO] = 1;
    confirma_novo_radio = 0;    
  }
  else if ((confirma_novo_radio_base == 0) & (confirma_novo_radio_sensor == 1)){
    // Indica ao Nível 3 que apenas um dos Devices LoRa (Nó Sensor) recebeu/processou o Comando de alteração
    PacoteUL[MAC4_COMANDO] = 1;
    confirma_novo_radio = 0;    
  }
  else if (confirma_novo_radio_base == 5){
    PacoteUL[MAC4_COMANDO] = 5;
    confirma_novo_radio = 5;
  }
  else {
    // Sem necessidade de alteração de Rádio
    PacoteUL[MAC4_COMANDO] = 0;
    confirma_novo_radio = 0;    
  }

  
  Phy_mqtt_send_UL();
}

void App_radio_receive_DL() {
  //Nesta camada são feitos os acionamentos ou ajustes enviados pela base no pacote de DL

  if (PacoteDL[34] == 1){
    digitalWrite(PIN_LED_AMARELO, HIGH);
    feedback_led_amarelo = 1;
  }
  else{
    digitalWrite(PIN_LED_AMARELO, LOW);
    feedback_led_amarelo = 0;
  }

  App_radio_send_UL();  // Chama a função da camada de Aplicação de UL

}

void App_radio_send_UL() {
  // Neste ponto zeramos o pacote de UL para garantir que ele não está carregando nenhuma informação de comunicação anterior.
  for (int i = 0; i < TAMANHO_PACOTE; i++) {
    PacoteUL[i] = 0;
  }

  // Armazene as informações no PacoteUL[] ele é que será enviado

      // Lê o sensor LDR
  uint16_t luminosidade = readLDR();
  //luminosidade = analogRead(PIN_LDR); // trocar para o App_radio_send
  
  PacoteUL[16] = 44; // Aqui está o tipo de sensor, no caso 44 é um LDR
  PacoteUL[17] = (luminosidade/256);
  PacoteUL[18] = (luminosidade%256);

  // Feedback do estado do Led Amarelo
  if (feedback_led_amarelo == 1){
    PacoteUL[34] = 1;
  }
  else{
    PacoteUL[34] = 0;
  }
/*
  Serial.println(lum);
  Serial.println(PacoteUL[17]);
  Serial.println(PacoteUL[18]);
*/  
  
  Transp_radio_send_UL();
}

// -----------------------------------------------------------------
//  LÊ SENSOR — LDR (ADC 12-bits, Média de 8 amostras)
// -----------------------------------------------------------------
uint16_t readLDR() {
    uint32_t soma = 0;
    for (int i = 0; i < NUM_LEITURA_LDR; i++) {
        soma += analogRead(PIN_LDR);
        //delay(2);
    }
    return (uint16_t)(soma / NUM_LEITURA_LDR);
}



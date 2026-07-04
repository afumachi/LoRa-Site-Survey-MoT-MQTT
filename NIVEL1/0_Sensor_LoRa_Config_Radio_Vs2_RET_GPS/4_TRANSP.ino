//================ RECEBE O PACOTE DE DL DA CAMADA DE REDE ========
void Transp_radio_receive_DL() { 

  //neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL
  psr_geral = ((PacoteDL[14]*256)+(PacoteDL[15]))/10;
  
  unsigned long tempo_pacoteDL_ms = (unsigned long)tempo_radio * 1UL * 1500UL; // 1.5x o valor recebido em MAC3_TEMPO

  if ((confirma_novo_radio_base == 4) || (confirma_novo_radio_base == 5)){ 

    if ((millis() - millis_contador_DL) >= tempo_pacoteDL_ms) {
      contador_perda_DL = contador_perda_DL + 1;  // Incrementa o contador de perda de pacote de DL
      Serial.println("[TRANSPORTE] PACOTES DL PERDIDOS: ");
      Serial.println(contador_perda_DL);
      millis_contador_DL = millis();
    }
    else{
      millis_contador_DL = millis();
    }
  }    
 
  App_radio_receive_DL();
}


//================ ENVIA O PACOTE DE UL À CAMADA DE REDE ========
void Transp_radio_send_UL() { 
  if (confirma_novo_radio_base == 4){ 
    contadorUL = contadorUL + 1;  // Incrementa o contador de pacote de UL
  }

  PacoteUL[DL_COUNTER_MSB] = contador_perda_DL/256; //PacoteDL[DL_COUNTER_MSB];
  PacoteUL[DL_COUNTER_LSB] = contador_perda_DL%256; //PacoteDL[DL_COUNTER_LSB];

  PacoteUL[UL_COUNTER_MSB] = contadorUL/256; // = (contadorUL >> 8) & 0xFF; 
  PacoteUL[UL_COUNTER_LSB] = contadorUL%256; // = contadorUL & 0xFF;
  // neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL

  display.setTextSize(1);
  display.setCursor(0, 40);
  display.print("PSR : ");
  display.setTextSize(1);
  display.print(psr_geral, 1); 
  display.println(" %");
  // Escreve o buffer na tela Oled
  display.display();  

  Net_radio_send_UL();
    if (confirma_novo_radio_base == 5){ 
    contadorDL = 0;
    contadorUL = 0;  // Incrementa o contador de pacote de UL
  }
}

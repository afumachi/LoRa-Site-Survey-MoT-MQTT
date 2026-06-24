//================ RECEBE O PACOTE DE DL DA CAMADA DE REDE ========
void Transp_radio_receive_DL() { 

  //neste ponto pode ser implementado um controle relacionado ao recebimento não sequencial de pacotes de DL
  psr_geral = ((PacoteDL[14]*256)+(PacoteDL[15]))/10;

  App_radio_receive_DL();
}


//================ ENVIA O PACOTE DE UL À CAMADA DE REDE ========
void Transp_radio_send_UL() { 

  contadorUL = contadorUL + 1;  // Incrementa o contador de pacote de UL

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
}

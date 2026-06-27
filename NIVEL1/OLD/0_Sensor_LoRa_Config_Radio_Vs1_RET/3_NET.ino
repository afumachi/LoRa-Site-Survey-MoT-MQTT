// ====== FUNÇÃO RECEBE PAOCTE DA CAMDA DE REDE
void Net_radio_receive_DL() {
  if(PacoteDL[8] == MY_ID) {  // Só passa para a camada superior se for o destino final do pacote
    //Serial.println("Pacote DL é para este Nó Sensor");
    Transp_radio_receive_DL();
  }
}

// ====== ENVIA PACOTE CAMADA REDE

void Net_radio_send_UL() {

  PacoteUL[RECEIVER_ID] = PacoteDL[TRANSMITTER_ID];   // Inverte os endereços de Origem e Destino no pacote de UL
  PacoteUL[TRANSMITTER_ID] = MY_ID;                   // Inverte os endereços de Origem e Destino no pacote de UL

  Mac_radio_send_UL();
}
void App_radio_receive_DL() {
  //Nesta camada são feitos os acionamentos ou ajustes enviados pela base no pacote de DL

  if (PacoteDL[39] == 1){
    digitalWrite(PIN_LED_AMARELO, HIGH);
    feedback_led_amarelo = 1;
  }
  if (PacoteDL[39] == 0){
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


  // Temperatura
  int16_t tempInt = temperatura * 100;
  //PacoteUL[19] = TIPO_SENSOR_TEMP;    
  PacoteUL[20] = (tempInt >> 8) & 0xFF;
  PacoteUL[21] =  tempInt       & 0xFF;

  // Umidade
  uint16_t umidInt = umidade * 100;
  //PacoteUL[22] = TIPO_SENSOR_UMID;    
  PacoteUL[23] = (umidInt >> 8) & 0xFF;
  PacoteUL[24] =  umidInt       & 0xFF;

  if (gps.location.isValid()) {
    // Latitude
    Serial.println("GPS VALIDO");    
    int32_t lat =  (gps.location.lat()) * 1e6;
    //PacoteUL[25] = TIPO_SENSOR_GPS;
    PacoteUL[26] = (lat >> 24) & 0xFF;
    PacoteUL[27] = (lat >> 16) & 0xFF;
    PacoteUL[28] = (lat >> 8)  & 0xFF;
    PacoteUL[29] =  lat        & 0xFF;

    // Longitude
    int32_t lon = (gps.location.lng()) * 1e6;
    PacoteUL[30] = (lon >> 24) & 0xFF;
    PacoteUL[31] = (lon >> 16) & 0xFF;
    PacoteUL[32] = (lon >> 8)  & 0xFF;
    PacoteUL[33] =  lon        & 0xFF;

    // Altitude (metros com 2 casas decimais)
    int32_t alt = (gps.altitude.meters()) * 100;

    PacoteUL[34] = (alt >> 24) & 0xFF;
    PacoteUL[35] = (alt >> 16) & 0xFF;
    PacoteUL[36] = (alt >> 8)  & 0xFF;
    PacoteUL[37] =  alt        & 0xFF;    
  }

  // Feedback do estado do Led Amarelo
  if (feedback_led_amarelo == 1){
    PacoteUL[39] = 1;
  }
  else{
    PacoteUL[39] = 0;
  }

  // Limapa os dados do Display
  display.clearDisplay();
    
  // Escreve o Título Display
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("PKLoRa - Sensor GPS");
  //display.drawLine(0, 12, 128, 12, SSD1306_WHITE);
  display.drawLine(0, 11, 128, 11, SSD1306_WHITE);

  // Escreve valor LATITUDE e LONGITUDE GPS
  display.setTextSize(1);
  display.setCursor(0, 16);

  if (gps.location.isValid()) {
    display.print("LAT: "); display.println(gps.location.lat(), 5);
    display.print("LON: "); display.println(gps.location.lng(), 5);
    display.print("ALT: "); display.println(gps.altitude.meters(), 2);
  }
  else{
    display.println("GPS buscando...");
    display.println("Satelites......");

  }
  // Escreve o buffer na tela Oled
  //display.display();
 
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

// -----------------------------------------------------------------
//  LÊ SENSOR — DHT22 (DATA PIN GPIO13, Média de 4 amostras)
// -----------------------------------------------------------------
bool LE_DHT(float &temperature, float &humidity) {
  float sumTemp = 0.0f;
  float sumHum  = 0.0f;
  uint8_t valid = 0;

  for (uint8_t i = 0; i < NUM_LEITURA_DHT; i++) {
    float t = dht.readTemperature();
    float h = dht.readHumidity();

    if (!isnan(t) && !isnan(h)) {
      sumTemp += t;
      sumHum  += h;
      valid++;
    }
    //delay(2);
  }

  if (valid == 0) return false;
  temperature = sumTemp / valid;
  humidity    = sumHum  / valid;
  return true;

}


// --- FUNÇÃO GPS ---
void updateGPS() {
  // While there is data in the serial buffer, feed it to TinyGPS++
  while (SerialGPS.available() > 0) {
    gps.encode(SerialGPS.read());
  }
  // Verifica se o GPS já tem uma leitura válida de localização
  if (!gps.location.isValid()) {
    //Serial.println("GPS conectado, mas aguardando sinal dos satélites...");
    //Serial.println("GPS DESCONHECIDO");  
    gps_satelite = false;
  }
  else{
    //Serial.println("GPS conectado, satélites encontrados...");          
    gps_satelite = true;
  }
}

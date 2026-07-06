
//=======================================================================
//                     1 - Bibliotecas
//=======================================================================

//#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>

#include <Wire.h>           // Inclui a Biblioteca Wire para Oled
#include <Adafruit_GFX.h>   // Inclui a Biblioteca GFX para Oled 
#include <Adafruit_SSD1306.h> // Inclui a Biblioteca OLED SSD1306
#include <DHT.h>            // Inclui a Biblioteca DHT
#include <TinyGPS++.h>      // Inclui a Biblioteca GPS

//=======================================================================
//                     2 - Variáveis
//=======================================================================
// Identificação do Nó Sensor e Tamanho de Pacote

#define MY_ID 1 
#define TAMANHO_PACOTE 40
#define NUM_LEITURA_LDR 4
#define NUM_LEITURA_DHT 4

byte PacoteDL[TAMANHO_PACOTE];
byte PacoteUL[TAMANHO_PACOTE];

// Taxa de comunicação Serial/USB para Debug
#define TAXA_SERIAL 115200

// Identificação de Leitura do Comando do LED AMARELO
#define CMD_LED_AMARELO 39 // BYTE de Controle de Comandar/Ligar CMD_LED_AMARELO

// --- 2. Definição de Pinos (Hardware) ---
#define PIN_LED_VERMELHO 15 // Status ENVIO por RF
#define PIN_LED_AMARELO 2   // ATUADOR (Controlado remotamente)
#define PIN_LED_VERDE 4     // Status de RECEBIMENTO por RF
#define PIN_LDR 36          // Sensor (APP)
#define PIN_BOTAO 39        // Botão do Nó Sensor

// ---- DECLARAÇÃO DIAGRAMA DE PINOS DO PROJETO ----
// Pinos utilizados para comunicação SPI entre ESP32 e RFM95 - Módulo LoRa
#define SCK 5
#define MISO 19			
#define MOSI 27		

// Pinos do RFM95 - Módulo LoRa
#define SS 18
#define RST 14			
#define DIO0 26

// --- Configuração Rádio LoRa ---
#define FREQUENCY_IN_HZ 915E6    // Frequência do Canal LoRa (ex: 915MHz)
#define txPower 20               // Potência de Transmissão (dBm) [2 a 20 - padrão 14]
#define spreadingFactor 12       // Fator de Espalhamento - range de [6-12, padrão 7]
#define signalBandwidth 125E3    // Banda do Sinal [125E3 | 250E3 | 500E3]
#define codingRateDenominator 8  // Coding Rate (4/5) [4/6 | 4/7 | 4/8 | 4/5 |]
//#define loraCRC                // Habilita ou disabilita o uso CRC, por padrão o CRC não é usado.


// OLED configuration
#define SCREEN_WIDTH 128 
#define SCREEN_HEIGHT 64 
#define OLED_RESET    -1 // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Pinos sensor de temperatura e umidade DHT22 AM2302
#define DHTPIN 13     // Define o pino de dados para o sensor DHT
#define DHTTYPE DHT22   // Especifica o tipo do sensor como DHT22

// Inicializa o sensor DHT
DHT dht(DHTPIN, DHTTYPE);
unsigned long millis_dht22_controle = 0;
float temperatura, umidade;

// GPS Setup (UART2)
TinyGPSPlus gps;
HardwareSerial SerialGPS(2); // Use UART2

// Controle de leitura do GPS no Void Loop
unsigned long millis_gps_controle = 0;
bool gps_satelite = false;

// Váriáveis utilizadas no código

uint16_t contadorUL = 0;
uint16_t contadorDL = 0;
uint16_t contadorSS = 0; //uint16_t
int LQI_DL;
int tipo, saltos, saltosTotal, dataInitAddress; // Variáveis utilizadas para o roteamento

float psr_geral;

float RSSI_dBm_DL;    // Variável com a potência rádio recebida (RSSI) em dBm
int RSSI_DL;          // Variável de mapeamento da RSSI em um valor de 0 a 255 para colocar no pacote

float SNR_DL_bruto;   // Variável com a relação sinal ruído
uint8_t SNR_DL;           // Variável inteira para enviar a SNR, que será convertida para a SNR original no Python

int luminosidade;
uint8_t feedback_led_amarelo = 0;

// # Configuração Atual Rádio LoRa
int valor_atual_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_atual_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_atual_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_atual_potencia_radio = 20; // # TX Power = 1 a 17???

// # Configuração Nova Rádio LoRa
int valor_novo_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_novo_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_novo_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_novo_potencia_radio = 20; // # TX Power = 1 a 17???

// # Configuração Anterior Rádio LoRa
int valor_anterior_spreadingfactor = 12; // # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
int valor_anterior_bandwidth = 125E3; // # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
int valor_anterior_codingrate = 8; // # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
int valor_anterior_potencia_radio = 20; // # TX Power = 1 a 17???
int recebe_comando_anterior_radio = 0; // # Comando de Downlink de mudança de configuração de rádio LoRa

uint8_t inicia_lora_site_survey = 0;
uint8_t confirma_novo_radio = 0;
uint8_t confirma_novo_radio_base = 0;
uint8_t confirma_novo_radio_sensor = 0;
//int recebe_comando_nova_radio = 0; // # Comando de Downlink de mudança de configuração de rádio LoRa

unsigned int primeiro_setup = 1; // Indica o Startup do Módulo pela primeira vez

//unsigned int tempo_radio = 8;

unsigned long lastPacketMillis = 0; 
unsigned long lastPacketTime = 0; // Timestamp local do último pacote recebido
int lostPacketCounter = 0;        // Contador de falhas
bool communicationLost = false;

unsigned long time_out_lora = 12000UL;

// ============================================================
// VARIÁVEIS GLOBAIS - adicionar junto às demais declarações
// ============================================================

unsigned long millis_standby_controle = 0;   // Marca o instante em que pacote foi recebido
unsigned long millis_inicio_controle = 0;   // Marca o instante em que MAC4_COMANDO == foi recebido

unsigned long millis_contador_DL = 0;   // Marca o instante em que pacote foi recebido


bool controle_ativo = false;                 // Flag que indica se a contagem está em andamento
uint8_t tempo_radio = 0;                     // Tempo recebido em MAC3_TEMPO (em ms ou unidade definida pelo protocolo)
uint8_t recebe_comando_nova_radio = 0;       // Comando recebido em MAC4_COMANDO
uint8_t contador_perda_DL = 0;



  // adicionar um conjunto de variáveis PKT_UL e PKT_DL para deixar os pacotes independentes

  // --- Physical Layer ---
#define RSSI_DOWNLINK 0
#define LQI_DOWNLINK  1
#define RSSI_UPLINK   2
#define LQI_UPLINK    3

  // --- MAC Layer ---
#define MAC_COUNTER_MSB 4 
#define MAC_COUNTER_LSB 5
#define MAC3_TEMPO 6
#define MAC4_COMANDO 7

  // --- Network Layer ---
#define  RECEIVER_ID     8
#define  NET2            9
#define  TRANSMITTER_ID  10
#define  NET4            11

  // --- Transport Layer ---
#define DL_COUNTER_MSB 12
#define DL_COUNTER_LSB 13
#define UL_COUNTER_MSB 14
#define UL_COUNTER_LSB 15


/*

enum bytes_do_pacote{

  // adicionar um conjunto de variáveis PKT_UL e PKT_DL para deixar os pacotes independentes

  // --- Physical Layer ---
  RSSI_DOWNLINK   = 0,
  LQI_DOWNLINK    = 1,
  RSSI_UPLINK     = 2,
  LQI_UPLINK      = 3,

  // --- MAC Layer ---
  MAC_COUNTER_MSB = 4, 
  MAC_COUNTER_LSB = 5,
  MAC3 = 6,
  MAC4 = 7,

  // --- Network Layer ---
  RECEIVER_ID     = 8,
  NET2            = 9,
  TRANSMITTER_ID  = 10,
  NET4            = 11,

  // --- Transport Layer ---
  DL_COUNTER_MSB = 12,
  DL_COUNTER_LSB = 13,
  UL_COUNTER_MSB = 14,
  UL_COUNTER_LSB = 15,

  // --- Application Layer ---
  APP1 = 16,  // Tipo de sensor - no caso da PK-LoRa é um LDR
  APP2 = 17,  // Valor inteiro da luminosidade da conta de divisão por 256
  APP3 = 18,  // Valor de resto da conta de divisão por 256
  APP4 = 19,
  APP5 = 20,
  APP6 = 21,
  APP7 = 22,
  APP8 = 23,
  APP9 = 24,
  APP10 = 25,
  APP11 = 26,
  APP12 = 27,
  APP13 = 28, 
  APP14 = 29,
  APP15 = 30,
  APP16 = 31,
  APP17 = 32,
  APP18 = 33,
  APP19 = 34,
  APP20 = 35,
  APP21 = 36,
  APP22 = 37,
  APP23 = 38,
  APP24 = 39,
  APP25 = 40,
  APP26 = 41,
  APP27 = 42,
  APP28 = 43,
  APP29 = 44,
  APP30 = 45,
  APP31 = 46,
  APP32 = 47,
  APP33 = 48,
  APP34 = 49,
  APP35 = 50,
  APP36 = 51,
};

*/

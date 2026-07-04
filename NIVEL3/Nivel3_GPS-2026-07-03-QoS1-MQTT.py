# N3 LoRa Site Survey - Versão 06/04/2026 - WissTek-IoT UNICAMP
# Versão Final - Modo Real + Aplicação (Comentários Originais Restaurados)
# Versão sem millis() - Adição do Envio Configurações de Rádio LoRa para devices LoRa - Anderson Fumachi
# Versão com millis() EM DESENVOLVIMENTO - Adição contagemd e tempo, caso muitas perdas de pacote
#                                          Caso PER > 10% Restaurar LoRa SF12/BW125/CR8/PWTx20
# Versão com INPUT Operador IoT do Tempo Entre Pacotes (2x ToA - Time on Air) Manualmente
# 
# MODIFICAÇÃO: A porta serial agora é lida automaticamente do arquivo NIVEL4/serial_config.txt
#              gerado pelo Nível 6 (Aba "Conexão Serial"). Não é mais necessário digitar no terminal.
# 
# ####### MÁQUINAS DE ESTADO DE GESTÃO E COMANDO DA REDE LORA #######
# 
# PacoteDL[Byte_7] <= comanda_mudar_radio => Pacote Downlink recebe no Byte 7 [MAC] este COMANDO
# 
# comanda_mudar_radio = 0
#         Sem reação dos Devices LoRa (Gateway ou Nó Sensor)
#         Nivel 3 ou Gateway não esperam nenhum feedback do Nó Sensor
#
# comanda_mudar_radio = 1 
#         Comando aos Devices LoRa para modificação de Rádio para o próximo pacote
#         Gateway espera receber no Pacote Uplink Byte 7 = 2 => Nó Sensor confirma 2
#         Nivel 3 espera receber no Pacote Uplink Byte 7 = 3 => Gateway + Nó Sensor (confirmação)
#
# comanda_mudar_radio = 2
#         A Ser Definido (TBD)
#
# comanda_mudar_radio = 3
#         Teste de Enlace - Controle do N2_N3 de que o Nó Sensor está "online"
#         Nó Sensor não contabiliza (sem incremento) do Contador de Uplink
#
# comanda_mudar_radio = 4
#         LSS em funcionamento
#         Incrementos do Contador de Uplink
#
# comanda_mudar_radio = 5
#         Último Pacote do LSS
#         Nó Sensor é informado do final do LSS
#         ( Pode retornar ao [LBDC] LoRa Best Distance Configuration)
#
# comanda_mudar_radio = 10
#         Perda de Enlace com o Nó Sensor
#         Apenas Gateway retorna ao [LBDC] LoRa Best Distance Configuration - SF12)
#
# ========= Bibliotecas =================================
#26-06-2026 - 
# modificações mudança rádio para => 1
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
import serial
import math
import time
import struct
from time import localtime, strftime
import os
import random
import pandas as pd
import threading

#========== Criação de Variáveis =========================
global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL, air_quality_indicator
global valor_inicial_spreadingfactor, valor_inicial_bandwidth, valor_inicial_codingrate, valor_inicial_potencia_radio
global valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio
global valor_novo_spreadingfactor, valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio
global tamanho_do_pacote, taxa_canal_teorica, taxa_canal_calculada, bitrate, perda_geral, st_cmd_led_amarelo
global medida_atual, numero_de_medidas, condicao_start, tempo_entre_medidas, perda_total, enlace_testado
global recebe_valor_spreadingfactor, recebe_valor_bandwidth, recebe_valor_codingrate, recebe_valor_potencia_radio
global comanda_mudar_radio, contador_pacote_DL, LSS_status, psr_geral, contador_reconfigura, confirma_mudar_radio
global psrDL_geral, contador_perda_DL

 # definições de teste: configurações importantes para a bateria de testes extraídas do arquivo de parâmetros

numero_de_medidas = 0
rota = [] # neste momento é um enlace ponto a ponto, que futuramente poderá ser usada para roteamento
condicao_start = 0
medida_atual = 0 # Variáveis Auxiliares
recebe_valor_spreadingfactor = 12
recebe_valor_bandwidth = 125
recebe_valor_codingrate = 8
recebe_valor_potencia_radio = 20

# variáveis para cálculo Taxa de Transmissão
bitrate = 0
taxa_canal_teorica = 0
taxa_canal_calculada = 0

 # Camada Física
tamanho_do_pacote = 40
rssi_DL = 0
rssi_UL = 0 
snr_DL = 0
snr_UL = 0

 # Configuração Inicial/Atual Rádio LoRa
valor_inicial_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_inicial_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_inicial_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_inicial_potencia_radio = 20 # TX Power = 1 a 17 ?

 # Configuração Inicial/Atual Rádio LoRa
valor_atual_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_atual_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_atual_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_atual_potencia_radio = 20 # TX Power = 1 a 17 ?

 # Configuração Anterior - Rádio LoRa
valor_anterior_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_anterior_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_anterior_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_anterior_potencia_radio = 20 # TX Power = 1 a 17 ?

 # Configuração Nova Rádio LoRa recebida pelo Nível 6
valor_novo_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_novo_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_novo_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_novo_potencia_radio = 20 # TX Power = 1 a 17 ?

 # Camada MAC
valor_tempo = 8
tempo_entre_medidas = 8 # original = 1 # alterado para 8 pior caso SF12/vw125k/cr8/pw20
 
# variáveis de controle de enlace
perda_total = 0
contador_perda_DL = 0
enlace_testado = 0
LSS_status = 0
contador_reconfigura = 0

 # Camada de Rede
ID_base = 0
ID_sensor = 1

 # Camada de Transporte
contador_DL = 0
ultimo_pacote_DL = 0
contador_UL = 0
ultimo_pacote_UL = 0
contador_pacote_DL = 0

 # Camada de Aplicação
luminosidade = 0 # Nova variável para leitura do LDR
temperatura = 0
umidade = 0
latitude = 0
longitude = 0
altitude = 0

# Adição variáveis de controle do ciclo de modif. configuração rádio LoRa
inicia_lora_site_survey = 0
comanda_mudar_radio = 0 # Comando de Downlink de mudança de configuração de rádio LoRa
confirma_mudar_radio = 0 # Recebe Uplink da Confirmação da mudança de rádio


 # Contabilização de PSR
psr_DL = 0
psr_UL = 0
psr_geral = 0 #Utilizada temporariamente, antes de implementar a 'separação' da PSR de Downlink e Uplink
psrDL_geral = 0
perdas_DL = 0
perdas_UL = 0
perda_geral = 0

# Variáveis para Máximo e Mínimo (Novas)
rssi_max_dl = -200
rssi_min_dl = 200
rssi_max_ul = -200
rssi_min_ul = 200

# Aplicação
st_cmd_led_amarelo = 0

#========== Criação de Pacotes
Pacote_UL = [0] * tamanho_do_pacote
Pacote_DL = [0] * tamanho_do_pacote


#================ INÍCIO BROKER ================

# ===== Configurações MQTT =====
BROKER        = "broker.hivemq.com"
PORTA_MQTT    = 1883
TOPIC_DL      = "mot_lora_gps/gateway/downlink"   # N2_N3 publica → Gateway PKLoRa assina
TOPIC_UL      = "mot_lora_gps/gateway/uplink"     # Gateway PKLoRa assina  → N2_N3 assina


# QoS usado nos dois sentidos (DL e UL). QoS1 = "at least once": o broker
# confirma (PUBACK) e há retransmissão se a confirmação não chegar.
# Importante para o dado de luminosidade, que é a peça central do framework.
MQTT_QOS      = 1


# Evento para sinalizar chegada de Pacote UL
Pacote_UL_status = threading.Event()
Pacote_UL_payload = bytearray(tamanho_do_pacote)

# ===== Callback MQTT =====
def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[PKLoRa MQTT] Conectado ao broker HiveMQ com sucesso.")
        client.subscribe(TOPIC_UL)
        print(f"[PKLoRa MQTT] Inscrito no tópico: {TOPIC_UL}")
    else:
        print(f"[PKLoRa MQTT] Falha na conexão. Código: {reason_code}")


def on_publish(client, userdata, mid, reason_code, properties):
    """Confirmação de entrega (PUBACK) do pacote DL publicado em QoS1."""
    print(f"[MQTT] PUBACK recebido para mid={mid} (pacote DL confirmado pelo broker).")


def on_message(client, userdata, msg):
    """Callback disparado ao receber pacote UL vindo do Gateway."""
    global Pacote_UL_payload
    payload = msg.payload
    if len(payload) >= tamanho_do_pacote:
        Pacote_UL_payload = bytearray(payload[:tamanho_do_pacote])
        Pacote_UL_status.set()   # Sinaliza que chegou um pacote válido

def on_disconnect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        print(f"[PKLoRa MQTT] Desconectado inesperadamente (rc={reason_code}). Tentando se reconectar...")

# ===== Inicialização do cliente MQTT =====
client = mqtt.Client(CallbackAPIVersion.VERSION2)
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect
client.on_publish    = on_publish


print("[PKLoRa MQTT] N2_N3 Conectando ao broker.hivemq.com via porta 1883")
client.connect(BROKER, PORTA_MQTT, keepalive=60)
client.loop_start()   # Thread de fundo para receber mensagens

# Aguarda conexão ser estabelecida com o Broker MQTT
time.sleep(2)
#================ FIM BROKER ================


#========== Criação de Arquivos de Gerência ===============
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')

#========== Criação do arquivo de CMD LED AMARELO
CMD_LED_FILE = os.path.join(dir_nivel4, 'cmd_led_amarelo.txt')
if not os.path.exists(CMD_LED_FILE):
    with open(CMD_LED_FILE, "w") as f:
        f.write("0")


def ler_cmd_led_amarelo():
    try:
        with open(CMD_LED_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val in ("0", "1") else 0
    except Exception as e:
        print(f"[AVISO] Não foi possível ler {CMD_LED_FILE}: {e}. Usando LED=0.")
        return 0


#========== Criação do arquivo de CONFIRMA CMD LED AMARELO
CONF_CMD_LED_FILE = os.path.join(dir_nivel4, 'conf_cmd_led_amarelo.txt')
if not os.path.exists(CONF_CMD_LED_FILE):
    with open(CONF_CMD_LED_FILE, "w") as f:
        f.write("0")

# FUNÇÃO DE COMANDO DO BOTÃO AMARELO DO NÓ DEVICE
def conf_ler_cmd_led_amarelo():
    try:
        with open(CONF_CMD_LED_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val in ("0", "1") else 0
    except Exception as e:
        print(f"[AVISO] Não foi possível escrever {CONF_CMD_LED_FILE}: {e}. Usando LED=0.")
        return 0


def conf_escrever_cmd_led_amarelo(estado):
    """Escreve o feedback do LED Amarelo (UL Byte 39) para o Nível 6 ler."""
    try:
        with open(CONF_CMD_LED_FILE, "w") as f:
            f.write(str(estado))
    except Exception as e:
        print(f"[AVISO] Não foi possível escrever {CONF_CMD_LED_FILE}: {e}.")


#========== ARQUIVO DE CONFIGURAÇÃO DA PORTA SERIAL =======================
# Gerado pelo Nível 6 (Aba "Conexão Serial")
SERIAL_CONFIG_FILE = os.path.join(dir_nivel4, 'serial_config.txt')


def ler_porta_serial_do_arquivo():
    """
    Lê a porta serial configurada pelo Nível 6.
    Retorna a string da porta (ex: 'COM3', '/dev/ttyUSB0') ou None se não configurada.
    """
    if not os.path.exists(SERIAL_CONFIG_FILE):
        return None
    try:
        with open(SERIAL_CONFIG_FILE, "r") as f:
            porta = f.read().strip()
            return porta if porta else None
    except Exception as e:
        print(f"[AVISO] Erro ao ler serial_config.txt: {e}")
        return None


if os.path.exists(os.path.join(dir_nivel4, 'dados_gerencia.tmp')): # Procura no Nível 4 se há um arquivo de gerência
   os.remove(os.path.join(dir_nivel4, 'dados_gerencia.tmp')) # Se há um arquivo de gerência, ele é deletado

if os.path.exists(os.path.join(dir_nivel4, 'dados_aplicacao.tmp')):# Procura no Nível 4 se há um arquivo de aplicação
   os.remove(os.path.join(dir_nivel4, 'dados_aplicacao.tmp')) # Se há um arquivo de aplicação, ele é deletado

# Cria o arquivo de parâmetros zerado para garantir estado inicial
arquivo_parametros = os.path.join(dir_nivel4, 'PARAMETROS.txt')
Parametros = open(arquivo_parametros, 'w')
Parametros.write("0\n0\n12\n125\n8\n14\n8\n0\n") # Adicionadas as linhas n12\n125000\n5\n17 no arquivo temporário de SF\BW\CR\PW
Parametros.close()

# Variáveis de Arquivo (serão definidas no loop ao iniciar o teste)
arquivo_LOG_pacoteUL = ""
arquivo_LOG_pacoteDL = ""
arquivo_LOG_gerencia = ""
arquivo_LOG_aplicacao = ""

# FUNÇÃO DE CÁLCULO AUTOMÁTICO DA JANELA DE TRANSMISSÃO DO TIME ON AIR DO RÁDIO LORA
def calculo_toa_radio_lora(n_preambulo=8, header_impl=False, crc_on=True, low_dr_opt=None):
    global tempo_entre_medidas, bitrate
    # 1. Parâmetros de tempo dos símbolos LoRa
    BANDWIDTH_Hz = valor_atual_bandwidth * 1000 #calcula Bandwidth em Hz
    tempo_simbolo = (2**valor_atual_spreadingfactor) / BANDWIDTH_Hz #calcula o tempo de símbolos de acordo com Spreading Factor e Bandwidth
    
    # 2. Tempo do Preâmbulo
    tempo_preambulo = (n_preambulo + 4.25) * tempo_simbolo
    
    # 3. Determinação automática do Low Data Rate Optimization
    if low_dr_opt is None:
        low_dr_opt = 1 if tempo_simbolo > 0.016 else 0
        
    # 4. Cálculo do número de símbolos do Payload (n_payload)
    if (valor_atual_codingrate == 5):
        valor_CR = 1
    elif (valor_atual_codingrate == 6):
        valor_CR = 2
    elif (valor_atual_codingrate == 7):
        valor_CR = 3
    elif (valor_atual_codingrate == 8):
        valor_CR = 4
    
    IH = 1 if header_impl else 0
    CRC = 1 if crc_on else 0
    DE = 1 if low_dr_opt else 0
    
    n_pacote = (8 * tamanho_do_pacote - 4 * valor_atual_spreadingfactor + 28 + 16 * CRC - 20 * IH) / (4 * (valor_atual_spreadingfactor - 2 * DE))
    n_payload_simbolo = 8 + max(math.ceil(n_pacote) * (valor_CR + 4), 0)
    
    tempo_pacote = n_payload_simbolo * tempo_simbolo
    
    # Retorna ToA em ms e bitrate em bps
    ToA_ms = (tempo_preambulo + tempo_pacote) * 1000
    bitrate = (tamanho_do_pacote * 8) / (ToA_ms / 1000)
    

    print("### Cálculo Time On Air (ToA [ms]): ", ToA_ms)
    valor_tempo = (2*(ToA_ms + (((10*tamanho_do_pacote)/115200))))/1000
    tempo_entre_medidas = max(math.ceil(valor_tempo), 0) #arredonda em segundos o tempo entre medidas
    print("### Valor Calculado do Tempo Entre Medidas [s]: ", tempo_entre_medidas)

    return round(tempo_entre_medidas, 2), round(bitrate, 2)

'''
#========== FUNÇÃO QUE RECONFIGURA RÁDIO LORA ================
def muda_radio_lora():
   global comanda_mudar_radio, inicia_lora_site_survey, valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
   global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio, valor_novo_spreadingfactor
   global valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status

   LSS_status = 3
   if (confirma_mudar_radio == 3):
      comanda_mudar_radio = 3
      inicia_lora_site_survey = 1

   while ((confirma_mudar_radio > 0) and (confirma_mudar_radio < 2)):

      if confirma_mudar_radio <2:
         comanda_mudar_radio = 1
         cmd_lora()

      if (confirma_mudar_radio == 2):
         comanda_mudar_radio = 2
         cmd_lora()
         
         valor_anterior_spreadingfactor = valor_atual_spreadingfactor
         valor_anterior_bandwidth = valor_atual_bandwidth
         valor_anterior_codingrate = valor_atual_codingrate
         valor_anterior_potencia_radio = valor_atual_potencia_radio
         valor_atual_spreadingfactor = valor_novo_spreadingfactor
         valor_atual_bandwidth = valor_novo_bandwidth
         valor_atual_codingrate = valor_novo_codingrate
         valor_atual_potencia_radio = valor_novo_potencia_radio

      print("### MUDANÇA DE RÁDIO LORA ### ESTADO DA CONFIRMAÇÃO DOS DEVICES : ", confirma_mudar_radio)

'''
#========== FUNÇÃO QUE RECONFIGURA RÁDIO LORA ================
def muda_radio_lora():
   global comanda_mudar_radio, inicia_lora_site_survey, valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
   global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio, valor_novo_spreadingfactor
   global valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status, contador_reconfigura, confirma_mudar_radio

   LSS_status = 3 # Status de mudança de rádio
   contador_reconfigura = 0

   while (confirma_mudar_radio < 3):
       comanda_mudar_radio = 1
       cmd_lora()
       
       contador_reconfigura = contador_reconfigura + 1
       if contador_reconfigura >= 3:
           contador_reconfigura = 0
           perda_enlace()

   if (confirma_mudar_radio == 3):
       inicia_lora_site_survey = 1
       valor_anterior_spreadingfactor = valor_atual_spreadingfactor
       valor_anterior_bandwidth = valor_atual_bandwidth
       valor_anterior_codingrate = valor_atual_codingrate
       valor_anterior_potencia_radio = valor_atual_potencia_radio
       valor_atual_spreadingfactor = valor_novo_spreadingfactor
       valor_atual_bandwidth = valor_novo_bandwidth
       valor_atual_codingrate = valor_novo_codingrate
       valor_atual_potencia_radio = valor_novo_potencia_radio 
       LSS_status = 0


#========== INICIA ENVIOS DE PACOTES VIA RÁDIO LORA ================
def cmd_lora():

   downlink()
   time.sleep(8)
   uplink()

#========== DOWNLINK ================
def downlink():
   global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL
   global air_quality_indicator, Pacote_DL, medida_atual, comanda_mudar_radio

   # Limpa o pacote para garantir que não tem lixo
   for i in range(tamanho_do_pacote):
       Pacote_DL[i] = 0

   # Camada de Aplicação
   Pacote_DL[39] = ler_cmd_led_amarelo()
   if (Pacote_DL[39] == 1):
       print("### DOWNLINK ### COMANDO LED AMARELO: LIGA")

   # Camada de Transporte
   Pacote_DL[12] = int(medida_atual/256)
   Pacote_DL[13] = int(medida_atual%256)

   psr_ul = psr_geral * 10
   Pacote_DL[14] = int(psr_ul/256)
   Pacote_DL[15] = int(psr_ul%256)

   # Camada de Rede
   Pacote_DL[8] = ID_sensor
   Pacote_DL[10] = ID_base

   # Camada MAC
   Pacote_DL[4] = (numero_de_medidas >> 8) & 0xFF  # MSB
   Pacote_DL[5] = numero_de_medidas & 0xFF         # LSB
   Pacote_DL[6] = tempo_entre_medidas
   Pacote_DL[7] = comanda_mudar_radio
   print("### DOWNLINK ### COMANDO RADIO", comanda_mudar_radio)

   # Camada PHY Física

   # converte Bandwidth para envio em Byte [0-255]
   if (valor_novo_bandwidth == 125):
      valor_BW = 1
   elif (valor_novo_bandwidth == 250):
      valor_BW = 2
   elif (valor_novo_bandwidth == 500):
      valor_BW = 3
      
   Pacote_DL[0] = valor_novo_spreadingfactor
   Pacote_DL[1] = valor_BW
   Pacote_DL[2] = valor_novo_codingrate
   Pacote_DL[3] = valor_novo_potencia_radio

   # -------- Publica pacote DL no broker MQTT --------
   Pacote_UL_status.clear()
   result = client.publish(TOPIC_DL, bytes(Pacote_DL), qos=MQTT_QOS)
   result.wait_for_publish()
   #print(f"Pacote [DL] {j:03d} publicado no broker | LED={Comando_LED_amarelo}")


#========== UPLINK ==================
def uplink():
   global perda_geral, rssi_DL, rssi_UL, contador_UL, ultimo_pacote_DL
   global Pacote_UL, luminosidade, confirma_mudar_radio, snr_UL, snr_DL, st_cmd_led_amarelo
   global perda_total, contador_pacote_DL, contador_DL, medida_atual, numero_de_medidas
   global temperatura, umidade, latitude, longitude, altitude, contador_perda_DL


   # -------- Aguarda novo pacote UL (timeout = Tempo_entre_pacotes) --------
   Pacote_UL_novo = Pacote_UL_status.wait(timeout=tempo_entre_medidas)

   if Pacote_UL_novo:
       
       Pacote_UL = Pacote_UL_payload
       
       if(len(Pacote_UL)==tamanho_do_pacote):

          val_dl = Pacote_UL[0]
          #snr_DL = Pacote_UL[1]
          snr_DL = round((Pacote_UL[1] / 4) - 30, 2)
          val_ul = Pacote_UL[2]
          #snr_UL = Pacote_UL[3]
          snr_UL = round((Pacote_UL[3] / 4) - 30, 2)
                      
          # Conversão de Byte para RSSI
          if val_dl > 127:
              rssi_DL = ((val_dl - 256) / 2.0) - 74.0
          else:
              rssi_DL = (val_dl / 2.0) - 74.0

          # Conversão de Byte para SNR
          #snr_DL = ((snr_DL /4) - 30)


          # Conversão de Byte para RSSI
          if val_ul > 127:
              rssi_UL = ((val_ul - 256) / 2.0) - 74.0
          else:
              rssi_UL = (val_ul / 2.0) - 74.0

          # Conversão de Byte para SNR
          #snr_UL = ((snr_UL /4) - 30)
          

          # Camada MAC
          confirma_mudar_radio = Pacote_UL[7]
          if (confirma_mudar_radio > 0):
              print("### UPLINK ### ESTADO RADIO LORA ### [ 6 ] LSS EM FUNCIONAMENTO : ", confirma_mudar_radio)
              print("")

          # Camada de Rede
          if(Pacote_UL[8]== 0 and Pacote_UL[10] ==1):

             # Camada de Transporte
             contador_UL = int(Pacote_UL[14]*256) + Pacote_UL[15]
             contador_perda_DL = int(Pacote_UL[12]*256) + Pacote_UL[13]
             print("### UPLINK ### PACOTE RECEBIDO UPLINK: ", contador_UL)
             print("### UPLINK ### PACOTE PERDIDO DOWNLINK: ", contador_perda_DL)
             print("")


             # Camada de Aplicação      
             luminosidade = int(Pacote_UL[17] * 256) + Pacote_UL[18]
             print("### UPLINK ### LUMINOSIDADE: ", luminosidade)

             temperatura = ((Pacote_UL[20] * 256) + Pacote_UL[21])/100
             print("### UPLINK ### TEMPERATURA: ", temperatura)

             umidade = ((Pacote_UL[23] * 256) + Pacote_UL[24])/100
             print("### UPLINK ### UMIDADE: ", umidade)

             # Extract longitude bytes (positions 26–29)
             lat_bytes = Pacote_UL[26:30]

             # Convert bytes → int32 (big-endian)
             lat = struct.unpack('>i', lat_bytes)[0]

             # Convert back to float GPS
             latitude = lat / 1e6
             print("### UPLINK ### LATITUDE: ", latitude)

             # Extract longitude bytes (positions 30–33)
             lon_bytes = Pacote_UL[30:34]

             # Convert bytes → int32 (big-endian)
             lon = struct.unpack('>i', lon_bytes)[0]

             # Convert back to float GPS
             longitude = lon / 1e6
             print("### UPLINK ### LONGITUDE: ", longitude)

             # Extract altitude bytes (positions 34–37)
             alt_bytes = Pacote_UL[34:38]

             # Convert bytes → int32 (big-endian)
             alt = struct.unpack('>i', alt_bytes)[0]

             # Convert back to float GPS
             altitude = alt / 100
             print("### UPLINK ### ALTITUDE: ", altitude)
             print("")
                                

          # -----------------------------------------------------------------------
          # FEEDBACK DO LED AMARELO: lê Byte 34 do Pacote Uplink
          # Se o nó confirma LED ON (byte 34 == 1), escreve no arquivo de feedback
          # para o Nível 6 atualizar visualmente o botão com fundo amarelo
          # -----------------------------------------------------------------------
          st_cmd_led_amarelo = Pacote_UL[39]
          conf_escrever_cmd_led_amarelo(st_cmd_led_amarelo)
          if st_cmd_led_amarelo == 1:
              print("### UPLINK ### FEEDBACK LED AMARELO: CONFIRMADO LIGADO pelo Nó Sensor")
             
   else:
       perda_geral += 1
       perda_total += 1
       print("### UPLINK ### FALHA - Pacotes perdidos: ", perda_total) 

       # EM DESENVOLVIMENTO - [LBDC] Caso PER >= 20% 
       if ((perda_geral >= (numero_de_medidas * 0.25)) and (LSS_status == 1)): 
           print("")
           print("### UPLINK ### FALHA DE ENLACE ### Pacotes não recebidos : ", perda_geral)
           perda_geral = 0
           perda_enlace()


#============================================================================================================================
       
def teste_enlace():
    global confirma_mudar_radio, comanda_mudar_radio, medida_atual, numero_de_medidas, condicao_start, LSS_status
    LSS_status = 2
    comanda_mudar_radio = 3
    time.sleep(0.5)
    cmd_lora()
    comanda_mudar_radio = 0

def perda_enlace():
    global confirma_mudar_radio, comanda_mudar_radio, medida_atual, numero_de_medidas, condicao_start, perda_geral
    global valor_novo_spreadingfactor, valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status

    perda_geral = 0
    print("### PERDA DE ENLACE LORA ### SET GATEWAY LORA TO BEST DISTANCE CONFIGURATION")
    comanda_mudar_radio = 10
    cmd_lora()
    time.sleep(0.5)
    if (confirma_mudar_radio == 10):
        print("")
        print("### RECUPERAÇÃO DE ENLACE LORA ### GATEWAY LORA ON BEST DISTANCE CONFIGURATION")
        teste_enlace()
        time.sleep(0.5)

        if (confirma_mudar_radio == 4):
            perda_geral = 0
            print("### PERDA DE ENLACE LORA ### ENLACE OK")
            valor_novo_spreadingfactor = recebe_valor_spreadingfactor
            valor_novo_bandwidth = recebe_valor_bandwidth
            valor_novo_codingrate = recebe_valor_codingrate
            valor_novo_potencia_radio = recebe_valor_potencia_radio     

            print("### PERDA DE ENLACE LORA ### APLICANDO MUDANÇA DE CONFIG RADIO LORA ###", comanda_mudar_radio)
            comanda_mudar_radio = 1
            confirma_mudar_radio = 1
            muda_radio_lora()

            comanda_mudar_radio = 0
            confirma_mudar_radio = 0
            LSS_status = 1

        else:
            print("################## Medições LoRa Site Survey finalizadas ##################")
            condicao_start = 0
            medida_atual = 0
            comanda_mudar_radio = 0
            confirma_mudar_radio = 0
            perda_geral = 0
            LSS_status = 0                   


#========== Armazenamento de Dados no LOG de pacote
def gravaLOG_Pacote():
   log = open(arquivo_LOG_pacoteUL, 'a')
   print(strftime("%d/%m/%Y %H:%M:%S"),";",Pacote_UL, file=log)
   log.close()
   log2 = open(arquivo_LOG_pacoteDL, 'a')
   print(strftime("%d/%m/%Y %H:%M:%S"),";",Pacote_DL, file=log2)
   log2.close()

#========== Armazenamento de Dados para Exibição
def gravaLOG_Gerencia():
     global rssi_max_dl, rssi_min_dl, rssi_max_ul, rssi_min_ul, snr_UL, snr_DL

     # 1. Grava no arquivo temporário (.tmp) para o Nível 6 Rede ler
     gerencia = open(os.path.join(dir_nivel4, 'dados_gerencia.tmp'), 'a')
     print(medida_atual, ";", rssi_DL, ";", round(psr_geral, 2), ";", round(psrDL_geral, 2), ";", rssi_UL, ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, ";", valor_atual_spreadingfactor, ";", valor_atual_bandwidth, ";", valor_atual_codingrate, ";", valor_atual_potencia_radio, ";", round(taxa_canal_teorica, 2), ";", round(taxa_canal_calculada, 2), ";", round(snr_DL, 2), ";", round(snr_UL, 2), ";", round(contador_DL, 2), ";", round(contador_UL, 2), ";", round(perda_total, 0), ";", round(LSS_status, 0), file=gerencia, sep='')
     gerencia.close()
     
     # 2. Grava no arquivo de LOG definitivo
     log_def = open(arquivo_LOG_gerencia, 'a')
     print(strftime("%d/%m/%Y %H:%M:%S"), ";", medida_atual, ";", rssi_DL, ";", rssi_UL, ";", perda_geral, ";", round(psrDL_geral, 2), ";", round(psr_geral, 2), ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, ";", valor_atual_spreadingfactor, ";", valor_atual_bandwidth, ";", valor_atual_codingrate, ";", valor_atual_potencia_radio, ";", taxa_canal_teorica, ";", taxa_canal_calculada, ";", snr_DL, ";", snr_UL, ";", contador_DL, ";",contador_UL, ";",perda_total, ";", LSS_status, file=log_def, sep='')
     log_def.close()


def gravaLOG_Aplicacao():
     # 1. Grava no arquivo temporário (.tmp) para o Nível 6 Aplicação ler
     app_tmp = open(os.path.join(dir_nivel4, 'dados_aplicacao.tmp'), 'a')
     print(medida_atual, ";", luminosidade, file=app_tmp, sep='')
     app_tmp.close()
     
     # 2. Grava no Log Definitivo de Aplicação
     app_def = open(arquivo_LOG_aplicacao, 'a')
     print(strftime("%d/%m/%Y %H:%M:%S"), ";", medida_atual, ";", luminosidade, ";", temperatura, ";", umidade, ";", latitude, ";", longitude, ";", altitude, file=app_def, sep='')
     app_def.close()


#=========== Calculo da PSR geral
def calculaPSR():
    global medida_atual, psr_geral, perda_total
    if medida_atual > 0:
        pacotes_recebidos = medida_atual - perda_total
        psr_geral = (pacotes_recebidos / medida_atual) * 100
        if psr_geral < 0:
            psr_geral = 0.0
    else:
        psr_geral = 0.0


#=========== Calculo da PSR geral
def calculaPSRDL():
    global medida_atual, psrDL_geral, contador_perda_DL
    if medida_atual > 0:
        psrDL_geral = 100 - ((contador_perda_DL / medida_atual) * 100)
        if psrDL_geral < 0:
            psrDL_geral = 0.0
    else:
        psrDL_geral = 0.0


#=========== Calculo da taxa de Canal
def calculaTaxaCanal():
    global taxa_canal_teorica, taxa_canal_calculada, psr_geral, valor_novo_bandwidth, valor_novo_spreadingfactor, valor_novo_codingrate

    if (valor_atual_codingrate == 5):
        valor_CR = 1
    elif (valor_atual_codingrate == 6):
        valor_CR = 2
    elif (valor_atual_codingrate == 7):
        valor_CR = 3
    elif (valor_atual_codingrate == 8):
        valor_CR = 4

    taxa_canal_teorica = 1000*(valor_novo_spreadingfactor*((valor_novo_bandwidth*1000)/(2**valor_novo_spreadingfactor))*(4/(4+valor_CR)))/1000
    taxa_canal_calculada = (taxa_canal_teorica * psr_geral)/100
    
    return round(taxa_canal_teorica, 2), round(taxa_canal_calculada, 2)


#=========== Calculo de Máximos e Mínimos RSSI
def calculaMaxMinRSSI():
    global rssi_DL, rssi_UL, rssi_max_dl, rssi_min_dl, rssi_max_ul, rssi_min_ul
    if rssi_DL > rssi_max_dl: rssi_max_dl = rssi_DL
    if rssi_DL < rssi_min_dl: rssi_min_dl = rssi_DL
    if rssi_UL > rssi_max_ul: rssi_max_ul = rssi_UL
    if rssi_UL < rssi_min_ul: rssi_min_ul = rssi_UL


#========== Leitura de Parâmetros =============
while True:

   # Leitura constante do arquivo de parâmetros do Usuário Nível 6
   if os.path.exists(arquivo_parametros):
       Parametros = open(arquivo_parametros, 'r')
       line = Parametros.readline()
       if len(line) > 0: condicao_start = int(line)
       line = Parametros.readline()
       if len(line) > 0: numero_de_medidas = int(line)
       line = Parametros.readline()
       if len(line) > 0: recebe_valor_spreadingfactor = int(line)
       line = Parametros.readline()
       if len(line) > 0: recebe_valor_bandwidth = int(line)
       line = Parametros.readline()
       if len(line) > 0: recebe_valor_codingrate = int(line)
       line = Parametros.readline()
       if len(line) > 0: recebe_valor_potencia_radio = int(line)
       line = Parametros.readline()
       if len(line) > 0: valor_tempo = int(line)
       Parametros.close()

   valor_novo_spreadingfactor = recebe_valor_spreadingfactor
   valor_novo_bandwidth = recebe_valor_bandwidth
   valor_novo_codingrate = recebe_valor_codingrate
   valor_novo_potencia_radio = recebe_valor_potencia_radio     
   
   if (condicao_start == 1):
      if (enlace_testado == 0):
         print("### LSS - TESTE ENLACE LORA ###")
         teste_enlace()
         enlace_testado = 1
         time.sleep(0.5)
         
         if (confirma_mudar_radio == 4):
             print("### LSS - TESTE ENLACE LORA REALIZADO COM SUCESSO ###")
             comanda_mudar_radio = 0
             confirma_mudar_radio = 0
             LSS_status = 1
             perda_total = 0
             perda_geral = 0             
         else:
             print("### LSS - FALHA TESTE ENLACE LORA - REFAZENDO TESTE... ###")
             teste_enlace()
             enlace_testado = 1
             time.sleep(0.5)
             if (confirma_mudar_radio == 4):
                 print("### LSS - TESTE ENLACE LORA REALIZADO COM SUCESSO ###")
                 comanda_mudar_radio = 0
                 confirma_mudar_radio = 0
                 LSS_status = 1
                 perda_total = 0
                 perda_geral = 0
             else:
                 print("### LSS - ENLACE LORA PERDIDO - FUNÇÃO PERDA DE ENLACE ###")
                 perda_enlace()
                 comanda_mudar_radio = 0
                 confirma_mudar_radio = 0
                 perda_total = 0
                 perda_geral = 0

      tempo_entre_medidas = valor_tempo
      
      if ((valor_novo_spreadingfactor != valor_atual_spreadingfactor) or (valor_novo_bandwidth != valor_atual_bandwidth) or (valor_novo_codingrate != valor_atual_codingrate) or (valor_novo_potencia_radio != valor_atual_potencia_radio)):
         LSS_status = 3
         comanda_mudar_radio = 1
         confirma_mudar_radio = 1
         print("### LSS - Mudança de Configuração de Rádio Detectada")
         print("### LSS - Entrando em Modo Muda Config. Rádio LoRa ### ", comanda_mudar_radio)
         muda_radio_lora()

         inicia_lora_site_survey = 1
         comanda_mudar_radio = 4
         confirma_mudar_radio = 0
         LSS_status = 1
         time.sleep(0.5)
      else:
         comanda_mudar_radio = 4 
         confirma_mudar_radio = 0
         LSS_status = 1

      if (medida_atual == 0):
         print("################## LSS - Iniciando Medições LoRa #################")

         # Reset de variáveis
         contador_DL = 0; contador_UL = 0; psr_geral = 0; perda_geral = 0
         rssi_DL = 0; rssi_UL = 0; luminosidade = 0
         rssi_max_dl = -200; rssi_min_dl = 200; rssi_max_ul = -200; rssi_min_ul = 200
         
         # Criação do arquivo de LOG
         arquivo_LOG_pacoteUL = os.path.join(dir_nivel4, strftime("LOG_pacote_UL_%Y_%m_%d_%H-%M-%S.txt"))
         arquivo_LOG_pacoteDL = os.path.join(dir_nivel4, strftime("LOG_pacote_DL_%Y_%m_%d_%H-%M-%S.txt"))
         arquivo_LOG_gerencia = os.path.join(dir_nivel4, strftime("LOG_gerencia_%Y_%m_%d_%H-%M-%S.txt"))
         arquivo_LOG_aplicacao = os.path.join(dir_nivel4, strftime("LOG_aplicacao_%Y_%m_%d_%H-%M-%S.txt"))
         
         print ("Arquivo de LOG de pacote UL: %s" % arquivo_LOG_pacoteUL)
         print ("Arquivo de LOG de pacote DL: %s" % arquivo_LOG_pacoteDL)
         print ("Arquivo de LOG de gerencia: %s" % arquivo_LOG_gerencia)
         
         # Inicializa arquivos físicos
         open(arquivo_LOG_pacoteUL, 'w').close()
         open(arquivo_LOG_pacoteDL, 'w').close()         
         f = open(arquivo_LOG_gerencia, 'w')
         print ('Time stamp;medida_atual;RSSI_DL;RSSI_UL;Perdas;PSR_DL;PSR_UL;Max_DL;Min_DL;Max_UL;Min_UL;valor_atual_spreadingfactor;valor_atual_bandwidth;valor_atual_codingrate;valor_atual_potencia_radio;taxa_canal_teorica;taxa_canal_calculada;snr_DL;snr_UL;contador_DL;contador_UL;perda_total;LSS_status', file=f)
         f.close()
         
         f = open(arquivo_LOG_aplicacao, 'w')
         print ('Time stamp;Medida;Luminosidade;Temperatura;Umidade;Latitude;Longitude;Altitude', file=f)
         f.close()
         
         # Limpa temporários
         open(os.path.join(dir_nivel4, 'dados_gerencia.tmp'), 'w').close()
         open(os.path.join(dir_nivel4, 'dados_aplicacao.tmp'), 'w').close()
      
      if (medida_atual < numero_de_medidas):
         LSS_status = 1
         tempo_entre_medidas = valor_tempo
         
         medida_atual = medida_atual + 1
         print("### LSS - Medida: ",medida_atual, "de ",numero_de_medidas)

         if ((medida_atual) == (numero_de_medidas)):
             comanda_mudar_radio = 5

         downlink()
         time.sleep(tempo_entre_medidas)         
         uplink()

         gravaLOG_Pacote()
         calculaPSR()
         calculaPSRDL()
         calculaTaxaCanal()
         calculaMaxMinRSSI()
         gravaLOG_Gerencia()
         gravaLOG_Aplicacao()

         
      else:
         print("################## Medições LoRa Site Survey finalizadas ##################")
         print("PSR DOWNLINK ", psrDL_geral, "%")
         print("PSR UPLINK ", psr_geral, "%")
         condicao_start = 0
         medida_atual = 0
         comanda_mudar_radio = 0
         inicia_lora_site_survey = 0
         confirma_mudar_radio = 0
         enlace_testado = 0
         perda_geral = 0
         tempo_entre_medidas = 8
         perda_total = 0
         contador_DL = 0
         contador_UL = 0
         LSS_status = 0
         contador_perda_DL = 0
         #Atualiza arquivo de Parâmetros   
         Parametros = open(arquivo_parametros, 'w')
         Parametros.write("0\n0\n12\n125\n8\n14\n8\n0\n") 
         Parametros.close()
   else:
     medida_atual = 0
     perda_geral = 0
     condicao_start = 0
     comanda_mudar_radio = 0
     confirma_mudar_radio = 0
     enlace_testado = 0
     perda_geral = 0
     perda_total = 0
     contador_DL = 0
     contador_perda_DL = 0
     contador_UL = 0
     tempo_entre_medidas = 8
     LSS_status = 0
     print("LSS pausado")
     time.sleep(2)

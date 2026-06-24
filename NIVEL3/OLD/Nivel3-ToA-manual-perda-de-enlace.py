# N3 LoRa Site Survey - Versão 06/04/2026 - WissTek-IoT UNICAMP
# Versão Final - Modo Real + Aplicação (Comentários Originais Restaurados)
# Versão sem millis() - Adição do Envio Configurações de Rádio LoRa para devices LoRa - Anderson Fumachi
# Versão com millis() EM DESENVOLVIMENTO - Adição contagemd e tempo, caso muitas perdas de pacote
#                                          Caso PER > 10% Restaurar LoRa SF12/BW125/CR8/PWTx20
# Versão com INPUT Operador IoT do Tempo Entre Pacotes (2x ToA - Time on Air) Manualmente
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
#         Mensagem aos Devices LoRa de que poderá haver uma modificação de Rádio
#         Gateway espera receber no Pacote Uplink Byte 7 = 1 => Nó Sensor confirma 1
#         Nivel 3 espera receber no Pacote Uplink Byte 7 = 2 => Gateway 1 + Nó Sensor 1 confirmam
# 
# 
# 
# 
# 
# ========= Bibliotecas =================================
import serial
import math
import time
import struct
from time import localtime, strftime
import os
import random
import pandas as pd

#========== Criação de Variáveis =========================
global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL, air_quality_indicator
global valor_inicial_spreadingfactor, valor_inicial_bandwidth, valor_inicial_codingrate, valor_inicial_potencia_radio
global valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio
global valor_novo_spreadingfactor, valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio
global tamanho_do_pacote, taxa_canal_teorica, taxa_canal_calculada, bitrate, perda_geral, st_cmd_led_amarelo
global medida_atual, numero_de_medidas, condicao_start, tempo_entre_medidas, perda_total, enlace_testado
global recebe_valor_spreadingfactor, recebe_valor_bandwidth, recebe_valor_codingrate, recebe_valor_potencia_radio
global comanda_mudar_radio, contador_pacote_DL, LSS_status
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
tamanho_do_pacote = 52 
rssi_DL = 0
rssi_UL = 0 
snr_DL = 0
snr_UL = 0

 # Configuração Inicial/Atual Rádio LoRa
valor_inicial_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_inicial_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_inicial_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_inicial_potencia_radio = 20 # TX Power = 1 a 17 ?
# cmd_init_config = 0 # Comando de Downlink de mudança de configuração de rádio LoRa

 # Configuração Inicial/Atual Rádio LoRa
valor_atual_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_atual_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_atual_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_atual_potencia_radio = 20 # TX Power = 1 a 17 ?
# cmd_init_config = 0 # Comando de Downlink de mudança de configuração de rádio LoRa

 # Configuração Anterior - Rádio LoRa
valor_anterior_spreadingfactor = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_anterior_bandwidth = 125 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_anterior_codingrate = 8 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
valor_anterior_potencia_radio = 20 # TX Power = 1 a 17 ?
# cmd_run_config = 0 # Comando de Downlink de mudança de configuração de rádio LoRa

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
enlace_testado = 0
LSS_status = 0
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
air_quality_indicator = 0

# Adição variáveis de controle do ciclo de modif. configuração rádio LoRa
inicia_lora_site_survey = 0
comanda_mudar_radio = 0 # Comando de Downlink de mudança de configuração de rádio LoRa
confirma_mudar_radio = 0 # Recebe Uplink da Confirmação da mudança de rádio


 # Contabilização de PSR
psr_DL = 0
psr_UL = 0
psr_geral = 0 #Utilizada temporariamente, antes de implementar a 'separação' da PSR de Downlink e Uplink
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


#========== Configuração da Porta Serial ==================
ser = None # Inicializa vazia, será configurada no loop

#========== Criação de Arquivos de Gerência ===============
# Este conjunto de linhas serve para deletar os arquivos temporários de armazenamento para observação de dados em tempo real

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


if os.path.exists(os.path.join(dir_nivel4, 'dados_gerencia.tmp')): # Procura no Nível 4 se há um arquivo de gerência
   os.remove(os.path.join(dir_nivel4, 'dados_gerencia.tmp')) # Se há um arquivo de gerência, ele é deletado

if os.path.exists(os.path.join(dir_nivel4, 'dados_aplicacao.tmp')):# Procura no Nível 4 se há um arquivo de aplicação
   os.remove(os.path.join(dir_nivel4, 'dados_aplicacao.tmp')) # Se há um arquivo de aplicação, ele é deletado

# Cria o arquivo de parâmetros zerado para garantir estado inicial
arquivo_parametros = os.path.join(dir_nivel4, 'PARAMETROS.txt')
Parametros = open(arquivo_parametros, 'w')
Parametros.write("0\n0\n12\n125\n8\n20\n8\n0\n") # Adicionadas as linhas n12\n125000\n5\n17 no arquivo temporário de SF\BW\CR\PW
Parametros.close()

# Variáveis de Arquivo (serão definidas no loop ao iniciar o teste)
arquivo_LOG_pacote = ""
arquivo_LOG_gerencia = ""
arquivo_LOG_aplicacao = ""

# FUNÇÃO DE CÁLCULO AUTOMÁTICO DA JANELA DE TRANSMISSÃO DO TIME ON AIR DO RÁDIO LORA
# def calculo_toa_radio_lora(tamanho_do_pacote, valor_spreadingfactor, valor_bandwidth, valor_codingrate, n_preambulo=8, header_impl=False, crc_on=True, low_dr_opt=None):
def calculo_toa_radio_lora(n_preambulo=8, header_impl=False, crc_on=True, low_dr_opt=None):
    global tempo_entre_medidas, bitrate
    # 1. Parâmetros de tempo dos símbolos LoRa
    BANDWIDTH_Hz = valor_atual_bandwidth * 1000 #calcula Bandwidth em Hz
    tempo_simbolo = (2**valor_atual_spreadingfactor) / BANDWIDTH_Hz #calcula o tempo de símbolos de acordo com Spreading Factor e Bandwidth
    
    # 2. Tempo do Preâmbulo
    tempo_preambulo = (n_preambulo + 4.25) * tempo_simbolo
    
    # 3. Determinação automática do Low Data Rate Optimization
    # Obrigatório quando a duração do símbolo > 16ms
    if low_dr_opt is None:
        low_dr_opt = 1 if tempo_simbolo > 0.016 else 0 # Variável DE == 1 If ((SF >= 11) & (BW == 125kHz))
        
    # 4. Cálculo do número de símbolos do Payload (n_payload)
    # valor_CR = int(valor_codingrate.split('/')[1]) - 4 # 4/5 -> 1, 4/8 -> 4
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
    # calcula valor do tempo da comunicação serial + entre o Envio do Pacote via LoRa de Downlink + Uplink + Tempo Processamento NodeMCU
    valor_tempo = (2*(ToA_ms + (((10*tamanho_do_pacote)/115200))))/1000
    tempo_entre_medidas = max(math.ceil(valor_tempo), 0) #arredonda em segundos o tempo entre medidas
    print("### Valor Calculado do Tempo Entre Medidas [s]: ", tempo_entre_medidas)

    return round(tempo_entre_medidas, 2), round(bitrate, 2)
    # return tempo_entre_medidas #round(tempo_entre_medidas, 2) #, round(bitrate, 2)


#========== FUNÇÃO QUE RECONFIGURA RÁDIO LORA ================
#========== CASO MODIFICAÇÂO PELO USUÁRIO NO NÍVEL 6 ================
# BYTE PacoteUL[7] recebe a confirmação dos ciclos de Pacotes DL-UL
# Ciclo do Primeiro Pacote, informa aos devices LoRa que uma modificação de config. de rádio foi Comandada
# BYTE PacoteDL[7] envia o Comando para os ciclos de Pacotes DL-UL informando a requisição da reconfig. da rádio
def muda_radio_lora():
   global comanda_mudar_radio, inicia_lora_site_survey, valor_atual_spreadingfactor, valor_atual_bandwidth, valor_atual_codingrate, valor_atual_potencia_radio
   global valor_anterior_spreadingfactor, valor_anterior_bandwidth, valor_anterior_codingrate, valor_anterior_potencia_radio, valor_novo_spreadingfactor
   global valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status

   LSS_status = 3
   if (confirma_mudar_radio == 3): # indica que Nível 3 já recebeu do nó sensor LoRa Nivel 1 e da base LoRa nivel 2 novos pacotes
      # na nova configuração e aplica o Teste LoRa Site Survey
      comanda_mudar_radio = 3 # informa devices inicio lora site survey
      inicia_lora_site_survey = 1 # habilita inicio Teste LoRa Site Survey

   while ((confirma_mudar_radio > 0) and (confirma_mudar_radio < 2)): #era 3 Confirmação da modificação da rádio LoRa pelos devices em 3 ciclos de Pacotes DL & UL

      if confirma_mudar_radio <2: # Caso não confirmação de ambos devices (Base & Nó Sensor), continua enviando os comandos
         comanda_mudar_radio = 1 # Primeiro ciclo de Pacotes DL & UL para informar reconfig. rádio
         cmd_lora() # Inicia envio DL + tempo + recebimento de UL

      if (confirma_mudar_radio == 2): # garante que Nivel 1 e Nivel 2 receberam nova configuração rádio LoRa para receber
         # os novos valores de config. de rádio na próxima janela
         comanda_mudar_radio = 2 # Segundo ciclo de Pacotes DL & UL para informar reconfig. rádio para aplicar valores da nova configuração
         cmd_lora() # Inicia envio DL + tempo + recebimento de UL
         
         #if (confirma_mudar_radio == 3): # indica que Nível 3 recebeu do nó sensor LoRa Nivel 1 & da base LoRa nivel 2 a confirmação
         # da alteração da rádio LoRa
         #comanda_mudar_radio = 3 # # Terceiro ciclo de Pacotes DL & UL para testar que a nova reconfig. foi efetivada
         # Salva os valores atuais de rádio nas variáveis anterior - configuração rádio Anterior
         valor_anterior_spreadingfactor = valor_atual_spreadingfactor
         valor_anterior_bandwidth = valor_atual_bandwidth
         valor_anterior_codingrate = valor_atual_codingrate
         valor_anterior_potencia_radio = valor_atual_potencia_radio
         #  Salva os novos valores de rádio nas variáveis RUN - configuração rádio Rodando           
         valor_atual_spreadingfactor = valor_novo_spreadingfactor
         valor_atual_bandwidth = valor_novo_bandwidth
         valor_atual_codingrate = valor_novo_codingrate
         valor_atual_potencia_radio = valor_novo_potencia_radio
         # calculo_toa_radio_lora()
         #cmd_lora() # Inicia envio DL + tempo + recebimento de UL

      # Imprime na Serial para DEBUG os status do comando e confirmação dos devices na reconfig. da rádio LoRa
      #print("### MUDANÇA DE RÁDIO LORA ### ESTADO DO COMANDO : ", comanda_mudar_radio)
      print("### MUDANÇA DE RÁDIO LORA ### ESTADO DA CONFIRMAÇÃO DOS DEVICES : ", confirma_mudar_radio)


#========== INICIA ENVIOS DE PACOTES VIA RÁDIO LORA ================
#========== DOWNLINK E UPLINK - RÁDIO LORA ================
def cmd_lora():

   downlink()
   # TEMPO ENTRE PACOTES FIXO EM 8 SEGUNDOS DURANTE A TROCA DE CONFIGURAÇÃO DE RÁDIO LORA
   time.sleep(8)
   uplink()

#========== DOWNLINK ================
def downlink():
   global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL
   global air_quality_indicator, Pacote_DL, medida_atual, comanda_mudar_radio

   #print("")
   print("=============== ÍNICIO ENVIO DOWNLINK ===============")
   print("")

   # Limpa o pacote para garantir que não tem lixo
   for i in range(tamanho_do_pacote):
       Pacote_DL[i] = 0

   # Camada de Aplicação
   
   Pacote_DL[34] = ler_cmd_led_amarelo()
   if (Pacote_DL[34] == 1):
       print("### DOWNLINK ### COMANDO LED AMARELO: LIGA")


   # Camada de Transporte
   # contador_DL = contador_DL+1
   Pacote_DL[12] = int(medida_atual/256)
   Pacote_DL[13] = int(medida_atual%256)


   # Camada de Rede
   Pacote_DL[8] = ID_sensor
   Pacote_DL[10] = ID_base
   
   # converte Bandwidth para envio em Byte [0-255]
   if (valor_novo_bandwidth == 125):
      valor_BW = 1
   elif (valor_novo_bandwidth == 250):
      valor_BW = 2
   elif (valor_novo_bandwidth == 500):
      valor_BW = 3

   # Camada PHY Física
   Pacote_DL[0] = valor_novo_spreadingfactor # Envio pelo Byte [0] do Pacote_DL do valor de Spreading Spectrum
   Pacote_DL[1] = valor_BW # Envio pelo Byte [1] do Pacote_DL do valor de Bandwidth
   Pacote_DL[2] = valor_novo_codingrate # Envio pelo Byte [2] do Pacote_DL do valor de CondingRate
   Pacote_DL[3] = valor_novo_potencia_radio # Deixa preparado para alteração do usuário da Potência da Rádio LoRa


   # Camada MAC
   Pacote_DL[4] = (numero_de_medidas >> 8) & 0xFF  # MSB
   Pacote_DL[5] = numero_de_medidas & 0xFF         # LSB
   Pacote_DL[6] = tempo_entre_medidas
   Pacote_DL[7] = comanda_mudar_radio  # Envio pelo Byte [7] do Pacote_DL o comando de alterar config. Rádio LoRa

   # Imprime Pacote_DL na Serial Para DEBUG
   #print("### DOWNLINK ### Pacote de Downlink Enviado")
   #print(*Pacote_DL)
   #print("")
   
   # Camada Física
   # Envio para o Hardware (Modo Real)
   if (ser is not None):
       ser.write(bytearray(Pacote_DL))
           
   #print("================== FIM ENVIO DOWNLINK ==================")
   ser.reset_output_buffer() # Opcional: limpa
   ser.reset_input_buffer() # Opcional: limpa


#========== UPLINK ==================
def uplink():
   global perda_geral, rssi_DL, rssi_UL, contador_UL, ultimo_pacote_DL, air_quality_indicator
   global Pacote_UL, luminosidade, confirma_mudar_radio, snr_UL, snr_DL, st_cmd_led_amarelo
   global perda_total, contador_pacote_DL, contador_DL, medida_atual, numero_de_medidas

   #print("")
   #print("=============== ÍNICIO RECEBIMENTO UPLINK ===============")

   # Camada Física
   # Leitura do Hardware
   #Se existe um objeto serial configurado
   if (ser is not None):
       #Existe ao menos 1 byte esperando na serial?
       if(ser.in_waiting > 0):
           #Realiza a a leitura da serial
           Pacote_UL_bytes = ser.read(tamanho_do_pacote) #52
           if len(Pacote_UL_bytes) == tamanho_do_pacote: #52
               
               # Cria novamente um pacote vazio para receber os dados
               Pacote_UL = [0] * tamanho_do_pacote # 52
               
               # Copia para o um vetor (lista) com números, pois o que chega da serial são bytes
               for i in range(tamanho_do_pacote): #52
                   Pacote_UL[i] = Pacote_UL_bytes[i]
           else:
               Pacote_UL = [] 
       else:
           Pacote_UL = [] 
           
   if(len(Pacote_UL)==tamanho_do_pacote): #52
      val_dl = Pacote_UL[0]
      snr_DL = Pacote_UL[1]
      val_ul = Pacote_UL[2]
      snr_UL = Pacote_UL[3]
               
      # Imprime Pacote_UL na Serial Para DEBUG
      # ----------------------------------------------------------------------
      #print("### UPLINK ### Pacote de Uplink Recebido")
      # ----------------------------------------------------------------------
      #print(*Pacote_UL)
      #print("")
      
      # Conversão de Byte para RSSI (Cálculo Ajustado)
      # Fórmula: dbm = ((rssi_int - 256) / 2.0) - 74.0 (se > 127) ou (rssi_int / 2.0) - 74.0
      
      # Cálculo para Downlink
      # RSSI DL
      if val_dl > 127:
          rssi_DL = ((val_dl - 256) / 2.0) - 74.0
      else:
          rssi_DL = (val_dl / 2.0) - 74.0

      # SNR DL
      snr_DL =  (snr_DL - 130) / 10 # ((snr_UL_real_db*10)+130)

      # Cálculo para Uplink
      # RSSI UL
      if val_ul > 127:
          rssi_UL = ((val_ul - 256) / 2.0) - 74.0
      else:
          rssi_UL = (val_ul / 2.0) - 74.0


      #((snr_UL_real_db*10)+130); 
      # SNR UL
      snr_UL =  (snr_UL - 130) / 10 

      # Camada MAC
      confirma_mudar_radio = Pacote_UL[7] # recebe info de confirmação da nova configuração de rádio LoRa
      # Imprime na Serial para DEBUG
      if (confirma_mudar_radio > 0):
          print("### UPLINK ### ESTADO RADIO LORA ### 4 LSS EM FUNCIONAMENTO : ", confirma_mudar_radio)
          print("")

      # Camada de Rede
      if(Pacote_UL[8]== 0 and Pacote_UL[10] ==1):
         #print("### UPLINK ### Pacote recebido (Uplink) para esta Borda")

         # Camada de Transporte

         contador_UL = int(Pacote_UL[14]*256) + Pacote_UL[15]
         contador_DL = int(Pacote_UL[12]*256) + Pacote_UL[13]
         if (enlace_testado != 0):
             contador_UL -= 1
             contador_DL -= 1
         # Camada de Aplicação      
         # Processamento da Luminosidade (LDR)
         # Reconstrói valor de 10 bits 
         luminosidade = int(Pacote_UL[17] * 256) + Pacote_UL[18]

      st_cmd_led_amarelo = Pacote_UL[34]
         
   else:
      perda_geral = perda_geral + 1 # refaz rádio recover
      perda_total += 1 # Vai para Nivel 6
      print("### UPLINK ### FALHA - Pacotes não recebidos: ", perda_total) 


   # LIMPA DADOS DA SERIAL
   ser.reset_output_buffer() # Opcional: limpa
   ser.reset_input_buffer() # Opcional: limpa

   # EM DESENVOLVIMENTO
   if (perda_geral >= (numero_de_medidas*0.10)): # Caso PER > 10%
       print("")
       print("### UPLINK ### FALHA DE ENLACE ### Pacotes não recebidos : ", perda_geral)
       #retorna_valor_radio_maximo()
       perda_geral = 0
       perda_enlace()

   
   #print("=============== FIM RECEBIMENTO UPLINK ===============")


#============================================================================================================================
       
def teste_enlace():
    global confirma_mudar_radio, comanda_mudar_radio, medida_atual, numero_de_medidas, condicao_start, LSS_status
    LSS_status = 2
    comanda_mudar_radio = 3
    time.sleep(1)
    cmd_lora()
    comanda_mudar_radio = 0


def perda_enlace():
    global confirma_mudar_radio, comanda_mudar_radio, medida_atual, numero_de_medidas, condicao_start, perda_geral
    global valor_novo_spreadingfactor, valor_novo_bandwidth, valor_novo_codingrate, valor_novo_potencia_radio, LSS_status
    LSS_status = 4
    perda_geral = 0
    comanda_mudar_radio = 10
    cmd_lora()
    print("### PERDA DE ENLACE LORA ### COMANDANDO GATEWAY LORA BEST DISTANCE CONFIGURATION")
    if (confirma_mudar_radio == 10):
        print("")
        print("### RECUPERAÇÃO DE ENLACE LORA ### REALIZADO COM SUCESSO GATEWAY LORA BEST DISTANCE CONFIGURATION")
        teste_enlace()

        if (confirma_mudar_radio == 4):
            perda_geral = 0
            valor_novo_spreadingfactor = recebe_valor_spreadingfactor
            valor_novo_bandwidth = recebe_valor_bandwidth
            valor_novo_codingrate = recebe_valor_codingrate
            valor_novo_potencia_radio = recebe_valor_potencia_radio     

            comanda_mudar_radio = 1
            confirma_mudar_radio = 1
            print("### DETECTADO MUDANÇA DE CONFIG RADIO LORA ###", comanda_mudar_radio)
            muda_radio_lora() # chama a função de reconfigurar os valores da rádio LoRa

            #inicia_lora_site_survey = 1 # Inicia LoRa site Survey com Nivel 3
            comanda_mudar_radio = 3 # comando de Site survey
            confirma_mudar_radio = 0 # zera confirmação
            time.sleep(1)

        else:
            medida_atual = numero_de_medidas
            condicao_start = 0   
            comanda_mudar_radio = 0
            confirma_mudar_radio = 0      
            perda_geral = 0  


#========== Armazenamento de Dados no LOG de pacote
def gravaLOG_Pacote():
   log = open(arquivo_LOG_pacote, 'a')
   print(strftime("%d/%m/%Y %H:%M:%S"),";",Pacote_UL, file=log)
   log.close()


#========== Armazenamento de Dados para Exibição
def gravaLOG_Gerencia():
     global rssi_max_dl, rssi_min_dl, rssi_max_ul, rssi_min_ul, snr_UL, snr_DL

     # 1. Grava no arquivo temporário (.tmp) para o Nível 6 Rede ler
     gerencia = open(os.path.join(dir_nivel4, 'dados_gerencia.tmp'), 'a')
     print(medida_atual, ";", rssi_DL, ";", round(psr_geral, 2), ";", round(psr_geral, 2), ";", rssi_UL, ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, ";", valor_atual_spreadingfactor, ";", valor_atual_bandwidth, ";", valor_atual_codingrate, ";", valor_atual_potencia_radio, ";", round(taxa_canal_teorica, 2), ";", round(taxa_canal_calculada, 2), ";", round(snr_DL, 2), ";", round(snr_UL, 2), ";", round(contador_DL, 2), ";", round(contador_UL, 2), ";", round(perda_total, 0), ";", round(LSS_status, 0), file=gerencia, sep='')
     gerencia.close()
     
     # 2. Grava no arquivo de LOG definitivo
     log_def = open(arquivo_LOG_gerencia, 'a')
     print(strftime("%d/%m/%Y %H:%M:%S"), ";", medida_atual, ";", rssi_DL, ";", rssi_UL, ";", perda_geral, ";", round(psr_geral, 2), ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, ";", valor_atual_spreadingfactor, ";", valor_atual_bandwidth, ";", valor_atual_codingrate, ";", valor_atual_potencia_radio, ";", taxa_canal_teorica, ";", taxa_canal_calculada, ";", snr_DL, ";", snr_UL, ";", contador_DL, ";",contador_UL, ";",perda_total, ";", LSS_status, file=log_def, sep='')
     log_def.close()


def gravaLOG_Aplicacao():
     # 1. Grava no arquivo temporário (.tmp) para o Nível 6 Aplicação ler
     app_tmp = open(os.path.join(dir_nivel4, 'dados_aplicacao.tmp'), 'a')
     print(medida_atual, ";", luminosidade, file=app_tmp, sep='')
     app_tmp.close()
     
     # 2. Grava no Log Definitivo de Aplicação
     app_def = open(arquivo_LOG_aplicacao, 'a')
     print(strftime("%d/%m/%Y %H:%M:%S"), ";", medida_atual, ";", luminosidade, file=app_def, sep='')
     app_def.close()


#===========Calculo da PSR geral
def calculaPSR():
    global medida_atual, psr_geral, perda_total
    if medida_atual > 0:
        # Sucesso = Total tentado (medida_atual) - Falhas (perda_geral)
        pacotes_recebidos = medida_atual - perda_total
        psr_geral = (pacotes_recebidos / medida_atual) * 100
    else:
        psr_geral = 0.0


#===========Calculo da taxa de Canal
def calculaTaxaCanal():
    global taxa_canal_teorica, taxa_canal_calculada, psr_geral, valor_novo_bandwidth, valor_novo_spreadingfactor, valor_novo_codingrate

    # valor_CR = int(valor_codingrate.split('/')[1]) - 4 # 4/5 -> 1, 4/8 -> 4
    if (valor_atual_codingrate == 5):
        valor_CR = 1
    elif (valor_atual_codingrate == 6):
        valor_CR = 2
    elif (valor_atual_codingrate == 7):
        valor_CR = 3
    elif (valor_atual_codingrate == 8):
        valor_CR = 4
    

    # multiplica por 1000 para transformar de kbps em bps
    taxa_canal_teorica = 1000*(valor_novo_spreadingfactor*((valor_novo_bandwidth*1000)/(2**valor_novo_spreadingfactor))*(4/(4+valor_CR)))/1000
    taxa_canal_calculada = (taxa_canal_teorica * psr_geral)/100
    
    return round(taxa_canal_teorica, 2), round(taxa_canal_calculada, 2)


#===========Calculo de Máximos e Mínimos RSSI
def calculaMaxMinRSSI():
    global rssi_DL, rssi_UL, rssi_max_dl, rssi_min_dl, rssi_max_ul, rssi_min_ul
    if rssi_DL > rssi_max_dl: rssi_max_dl = rssi_DL
    if rssi_DL < rssi_min_dl: rssi_min_dl = rssi_DL
    if rssi_UL > rssi_max_ul: rssi_max_ul = rssi_UL
    if rssi_UL < rssi_min_ul: rssi_min_ul = rssi_UL


# ======================================================================================
# INÍCIO LEITURA SERIAL
# Configura a serial
# para COM# o número que se coloca é n-1 no primeiro parâmetro. Ex COM9  valor 8
n_serial = input("Digite o número da serial do Gateway LoRa = COM ")  # seta a serial
n_serial1 = int(n_serial) - 1
ser = serial.Serial("COM" + str(n_serial), 115200, timeout=0.5)  # serial Windows
# ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1) # serial Linux
# ser = serial.Serial('/dev/cu.usbserial-0001', 115200, timeout=1) # serial OSX

# Aguarde o ESP32 "acordar" após o reset da conexão
print("Aguardando estabilização...")
time.sleep(3)       # Aguarda 3s ESP32 inicializar
ser.flushInput()    # Limpa qualquer lixo de memória do boot

# 1. Limpa o buffer de ENTRADA (dados que chegaram e não foram lidos)
ser.reset_input_buffer()

# 2. Limpa o buffer de SAÍDA (dados que foram enviados, mas não saíram fisicamente)
ser.reset_output_buffer()
time.sleep(0.5)
print("Porta Serial Conectada")


#========== Leitura de Parâmetros =============
while True:
   LSS_status = 0
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
   # Chama function calculo ToA (Time On Air) Radio LoRa
   # calculo_toa_radio_lora() # Este INPUT é Manual, realizado pelo Operador IoT
   

   if (condicao_start == 1):
      if (enlace_testado == 0):
         teste_enlace()
         enlace_testado = 1
         if (confirma_mudar_radio == 4):
             print("### LSS - TESTE ENLACE LORA REALIZADO COM SUCESSO ###")
             if ((valor_atual_spreadingfactor != valor_inicial_spreadingfactor) or (valor_atual_bandwidth != valor_inicial_bandwidth) or (valor_atual_codingrate != valor_inicial_codingrate) or (valor_atual_potencia_radio != valor_inicial_potencia_radio)):
   
                #valor_novo_spreadingfactor = valor_atual_spreadingfactor
                #valor_novo_bandwidth = valor_atual_bandwidth
                #valor_novo_codingrate = valor_atual_codingrate
                #valor_novo_potencia_radio = valor_atual_potencia_radio
                comanda_mudar_radio = 1
                confirma_mudar_radio = 1
                print("### LSS - Mudança de Configuração de Rádio Detectada")
                print("### LSS - Entrando em Modo Muda Config. Rádio LoRa ### ", comanda_mudar_radio)
                muda_radio_lora() # chama a função de reconfigurar os valores da rádio LoRa

                inicia_lora_site_survey = 1 # Inicia LoRa site Survey com Nivel 3
                comanda_mudar_radio = 3 # comando de Site survey
                confirma_mudar_radio = 0 # zera confirmação
                time.sleep(1)

         else:
             print("### LSS - ENLACE LORA PERDIDO - REINICIAR DEVICES LORA E PYTHON NIVEL 3 ###")
             perda_enlace() # TRABALHAR AQUI NA RECUPERAÇÃO DO ENLACE
             comanda_mudar_radio = 0
             confirma_mudar_radio = 0

      #Apenas para imprimir um cabeçalho dos testes no terminal
      if (medida_atual == 0): # and (start_teste_site_suvey == 1)):
         print("################## LSS - Iniciando Medições LoRa #################")

         # Reset de variáveis
         # cmd_new_config = 0 # zera cmd
         # confirm_new_config = 0 # zera cmd
         contador_DL = 0; contador_UL = 0; psr_geral = 0; perda_geral = 0
         rssi_DL = 0; rssi_UL = 0; luminosidade = 0
         rssi_max_dl = -200; rssi_min_dl = 200; rssi_max_ul = -200; rssi_min_ul = 200
         
         # Criação do arquivo de LOG para armanezamento completo dos dados aquisitados
         arquivo_LOG_pacote = os.path.join(dir_nivel4, strftime("LOG_pacote_%Y_%m_%d_%H-%M-%S.txt"))
         arquivo_LOG_gerencia = os.path.join(dir_nivel4, strftime("LOG_gerencia_%Y_%m_%d_%H-%M-%S.txt"))
         arquivo_LOG_aplicacao = os.path.join(dir_nivel4, strftime("LOG_aplicacao_%Y_%m_%d_%H-%M-%S.txt"))
         
         print ("Arquivo de LOG de pacote: %s" % arquivo_LOG_pacote)
         print ("Arquivo de LOG de gerencia: %s" % arquivo_LOG_gerencia)
         
         # Inicializa arquivos físicos
         open(arquivo_LOG_pacote, 'w').close()
         
         f = open(arquivo_LOG_gerencia, 'w')
         print ('Time stamp;medida_atual;RSSI_DL;RSSI_UL;Perdas;PSR;Max_DL;Min_DL;Max_UL;Min_UL;valor_atual_spreadingfactor;valor_atual_bandwidth;valor_atual_codingrate;valor_atual_potencia_radio;taxa_canal_teorica;taxa_canal_calculada;snr_DL;snr_UL;contador_DL;contador_UL;perda_total;LSS_status', file=f)
         # print ('Time stamp;Contador;RSSI_DL;RSSI_UL;Perdas;PSR;Max_DL;Min_DL;Max_UL;Min_UL', file=f)
         f.close()
         
         f = open(arquivo_LOG_aplicacao, 'w')
         print ('Time stamp;Medida;Luminosidade', file=f)
         f.close()
         
         # Limpa temporários
         open(os.path.join(dir_nivel4, 'dados_gerencia.tmp'), 'w').close()
         open(os.path.join(dir_nivel4, 'dados_aplicacao.tmp'), 'w').close()
      
      # print("### medida atual ###", medida_atual)
      # print("### numero_de_medidas ###", numero_de_medidas)
      if (medida_atual < numero_de_medidas):
         LSS_status = 1
         tempo_entre_medidas = valor_tempo
         # if (medida_atual < (numero_de_medidas + start_teste_site_suvey)):
         # Compara se há alteração na configuração do rádio LoRa pelo usuário e faz processo de modificação dos novos valores de rádio
         if ((valor_novo_spreadingfactor != valor_atual_spreadingfactor) or (valor_novo_bandwidth != valor_atual_bandwidth) or (valor_novo_codingrate != valor_atual_codingrate) or (valor_novo_potencia_radio != valor_atual_potencia_radio)):
            comanda_mudar_radio = 1
            confirma_mudar_radio = 1
            print("### LSS - Mudança de Configuração de Rádio Detectada")
            print("### LSS - Entrando em Modo Muda Config. Rádio LoRa ### ", comanda_mudar_radio)
            muda_radio_lora() # chama a função de reconfigurar os valores da rádio LoRa

            inicia_lora_site_survey = 1 # Inicia LoRa site Survey com Nivel 3
            comanda_mudar_radio = 3 # comando de Site survey
            confirma_mudar_radio = 0 # zera confirmação

            # IMPRIME NA SERIAL PARA DEBUG OS VALORES ATUAIS DO NÍVEL 6 PARA RÁDIO LORA
            # Chama function calculo ToA (Time On Air) Radio LoRa
            # calculo_toa_radio_lora()

            time.sleep(2)  # Pausa por 2 segundos PARA ESTABILIZAR MUDANÇA DE RÁDIO NOS DEVICES LORA
 
         else:
            comanda_mudar_radio = 3 # ERA 3 em 08/04/2026 Inicia LoRa site Survey para os Dispositivos Niveis 1 e 2
            confirma_mudar_radio = 0 # zera confirm
            time.sleep(2)

         medida_atual = medida_atual + 1
         print("### LSS - Medida: ",medida_atual, "de ",numero_de_medidas)

         if ((medida_atual) == (numero_de_medidas)):
             # informa aos devices LoRa que é o último pacote de medidas
             comanda_mudar_radio = 5

         downlink() 

         time.sleep(tempo_entre_medidas)
         print("### LSS - Tempo Entre Medidas: ",tempo_entre_medidas, " [s]")
         
         uplink()

         gravaLOG_Pacote()
         calculaPSR()
         calculaTaxaCanal()
         calculaMaxMinRSSI()
         gravaLOG_Gerencia()
         gravaLOG_Aplicacao()   
         
      else:
         # Se atingiu o limite, para o script alterando o arquivo PARAMETROS
         print("################## Medições LoRa Site Survey finalizadas ##################")
         # Zera as Variáveis do Processo do Site Survey
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
         

         #Atualiza arquivo de Parâmetros   
         Parametros = open(arquivo_parametros, 'w')
         Parametros.write("0\n0\n12\n125\n8\n20\n8\n0\n") 
         Parametros.close()
   else:
     # Zera as Variáveis do Processo do Site Survey
     medida_atual = 0 # Garante que próximo teste comece do zero
     perda_geral = 0 # E sem acúmulo de perdas de pacote
     condicao_start = 0 # Garante o início do próximo teste
     comanda_mudar_radio = 0
     confirma_mudar_radio = 0
     enlace_testado = 0
     perda_geral = 0
     perda_total = 0
     contador_DL = 0
     contador_UL = 0
     tempo_entre_medidas = 8
     LSS_status = 0
     print("LSS pausado") # Comentado para não poluir
     time.sleep(2)

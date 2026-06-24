# N3 LoRa Site Survey - Versão 28/01/2026 - WissTek-IoT UNICAMP
# Versão Final - Modo Real + Aplicação (Comentários Originais Restaurados)

# ========= Bibliotecas =================================
import serial
import math
import time
import struct
from time import localtime, strftime
import os
import random

#========== Criação de Variáveis =========================
global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL, air_quality_indicator 
 # definições de teste: configurações importantes para a bateria de testes extraídas do arquivo de parâmetros

numero_de_medidas = 0
rota = [] # neste momento é um enlace ponto a ponto, que futuramente poderá ser usada para roteamento
condicao_start = 0
medida_atual = 0 # Variáveis Auxiliares

valor_spreadingfactor = 12
valor_bandwidth = 125000
valor_codingrate = 5

 # Camada Física
tamanho_do_pacote = 52 
rssi_DL = 0
rssi_UL = 0 
snr_DL = 0
snr_UL = 0

 # Configuração Inicial Rádio LoRa
valor_init_SF = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_init_BW = 1 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_init_CR = 5 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
cmd_init_config = 0 # Comando de Downlink de mudança de configuração de rádio LoRa

 # Configuração Atual Rádio LoRa
valor_run_SF = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_run_BW = 1 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_run_CR = 5 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
cmd_run_config = 0 # Comando de Downlink de mudança de configuração de rádio LoRa

 # Configuração Nova Rádio LoRa
valor_new_SF = 12 # Spreading Factor inicial = Maior espalhamento possível 12 (de 7 a 12)
valor_new_BW = 1 # Bandwidth inicial = 125kHz (1 = 125kHz | 2 = 250kHz | 3 = 500kHz)
valor_new_CR = 5 # CodingRate Denominator = 5/4 (5/4 | 6/4 | 7/4 | 8/4)
cmd_new_config = 0 # Comando de Downlink de mudança de configuração de rádio LoRa

 # Camada MAC
tempo_entre_medidas = 5 # original = 1

 # Camada de Rede
ID_base = 0
ID_sensor = 1

 # Camada de Transporte
contador_DL = 0
ultimo_pacote_DL = 0
contador_UL = 0
ultimo_pacote_UL = 0

 # Camada de Aplicação
luminosidade = 0 # Nova variável para leitura do LDR
air_quality_indicator = 0

start_teste_site_suvey = 0
confirm_new_config = 0

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

#========== Criação de Pacotes
Pacote_UL = [0] * tamanho_do_pacote
Pacote_DL = [0] * tamanho_do_pacote

#========== Configuração da Porta Serial ==================
ser = None # Inicializa vazia, será configurada no loop

#========== Criação de Arquivos de Gerência ===============
# Este conjunto de linhas serve para deletar os arquivos temporários de armazenamento para observação de dados em tempo real

dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')

if os.path.exists(os.path.join(dir_nivel4, 'dados_gerencia.tmp')): # Procura no Nível 4 se há um arquivo de gerência
   os.remove(os.path.join(dir_nivel4, 'dados_gerencia.tmp')) # Se há um arquivo de gerência, ele é deletado

if os.path.exists(os.path.join(dir_nivel4, 'dados_aplicacao.tmp')):# Procura no Nível 4 se há um arquivo de aplicação
   os.remove(os.path.join(dir_nivel4, 'dados_aplicacao.tmp')) # Se há um arquivo de aplicação, ele é deletado

# Cria o arquivo de parâmetros zerado para garantir estado inicial
arquivo_parametros = os.path.join(dir_nivel4, 'PARAMETROS.txt')
Parametros = open(arquivo_parametros, 'w')
Parametros.write("0\n0\n") 
Parametros.close()

# Variáveis de Arquivo (serão definidas no loop ao iniciar o teste)
arquivo_LOG_pacote = ""
arquivo_LOG_gerencia = ""
arquivo_LOG_aplicacao = ""


#========== CONFIGURA RADIO LORA ================
#========== CASO MODIFICAÇÂO PELO USUÁRIO ================
def config_radio_lora():
   global cmd_new_config, start_teste_site_suvey

   while (confirm_new_config < 3):

      if confirm_new_config <2:
         # if ((cmd_new_config == 1) or (confirm_new_config <2)):
         # indica que não havia mudança de config.
         cmd_new_config = 1
         cmd_lora() # Inicia envio DL + tempo + recebimento de UL

      if (confirm_new_config == 2): # garante que Nivel 1 e Nivel 2 receberam nova configuração rádio LoRa e irão implementar na próxima janela
         cmd_new_config = 2
         cmd_lora() # Inicia envio DL + tempo + recebimento de UL
         
      if (confirm_new_config == 3): # indicam nó sensor LoRa Nivel 1 & a base LoRa nivel 2 receberam a configuração e
         # o cmd_config para alteração da rádio LoRa
         cmd_new_config = 3 # reenvia requisição de modif. configuração
         cmd_lora() # Inicia envio DL + tempo + recebimento de UL
         
      if (confirm_new_config == 4): # indicam nó sensor LoRa Nivel 1 ou base LoRa nivel 2 prontos para pacotes LoRa Site Survey
         cmd_new_config = 0 # inicia a rede teste LoRa Site Survey
         start_teste_site_suvey = 3 # habilita inicio teste LSS

      print("### CMD CONFIG RADIO LORA ### ", cmd_new_config)
      print("### CONFIRM CONFIG RADIO LORA ### ", confirm_new_config)


#========== INICIA ENVIOS DE PACOTES VIA RÁDIO LORA ================
#========== DOWNLINK E UPLINK - RÁDIO LORA ================
def cmd_lora():
   print("### ENVIANDO PACOTE DOWNLINK ###")
   downlink()
   time.sleep(tempo_entre_medidas)
   print("### RECEBENDO PACOTE UPLINK ###")
   uplink()
        


#========== DOWNLINK ================
def downlink():
   global rssi_DL, rssi_UL, contador_UL, contador_DL, ultimo_pacote_DL, ultimo_pacote_UL, air_quality_indicator, Pacote_DL
   
   # Limpa o pacote para garantir que não tem lixo
   for i in range(tamanho_do_pacote):
       Pacote_DL[i] = 0


   # Camada de Aplicação
   #Por enquanto estes valores não significam nada para o Nó Sensor
   Pacote_DL[51] = 10
   Pacote_DL[50] = 12

   # Camada de Transporte
   contador_DL = contador_DL+1
   Pacote_DL[12] = int(contador_DL/256)
   Pacote_DL[13] = int(contador_DL%256)

   # Camada de Rede
   Pacote_DL[8] = ID_sensor
   Pacote_DL[10] = ID_base
   
   Pacote_DL[0] = valor_new_SF
   Pacote_DL[1] = valor_new_BW
   Pacote_DL[2] = valor_new_CR
   #   Pacote_DL[3] = valor_PW
   Pacote_DL[11] = cmd_new_config

   # Camada MAC
   
   print("[Nível 3 - Borda] - Física - Pacote de Downlink")
   print(*Pacote_DL)
   print("================================================")
   # Camada Física
   # Envio para o Hardware (Modo Real)
   if (ser is not None):
       ser.write(bytearray(Pacote_DL))
           
   print('##### Pacote enviado para Nó Sensor (Downlink)')

#========== UPLINK ==================
def uplink():
   global perda_geral, rssi_DL, rssi_UL, contador_UL, ultimo_pacote_DL, air_quality_indicator, Pacote_UL, luminosidade, confirm_new_config
   
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
               Pacote_UL = [0] * 52
               
               # Copia para o um vetor (lista) com números, pois o que chega da serial são bytes
               for i in range(tamanho_do_pacote): #52
                   Pacote_UL[i] = Pacote_UL_bytes[i]
           else:
               Pacote_UL = [] 
       else:
           Pacote_UL = [] 
           
   if(len(Pacote_UL)==tamanho_do_pacote): #52
      val_dl = Pacote_UL[0]
      val_ul = Pacote_UL[2]
      
      confirm_new_config = Pacote_UL[11] # recebe info de validação da nova configuração de rádio LoRa    

      # print("### CMD CONFIG RADIO LORA ### ", cmd_new_config)
      print("### CONFIRM CONFIG RADIO LORA ### ", confirm_new_config)

      # ----------------------------------------------------------------------
      print("[Nível 3 - Borda] - Física - Pacote de Uplink")
      # ----------------------------------------------------------------------
      print(*Pacote_UL)
      print("================================================")
      
      # Conversão de Byte para RSSI (Cálculo Ajustado)
      # Fórmula: dbm = ((rssi_int - 256) / 2.0) - 74.0 (se > 127) ou (rssi_int / 2.0) - 74.0
      
      # Cálculo para Downlink
      if val_dl > 127:
          rssi_DL = ((val_dl - 256) / 2.0) - 74.0
      else:
          rssi_DL = (val_dl / 2.0) - 74.0
      
      # Cálculo para Uplink
      if val_ul > 127:
          rssi_UL = ((val_ul - 256) / 2.0) - 74.0
      else:
          rssi_UL = (val_ul / 2.0) - 74.0

   # Camada MAC

   # Camada de Rede
      if(Pacote_UL[8]== 0 and Pacote_UL[10] ==1):
         print("##### OK - Pacote recebido (Uplink)")

   # Camada de Transporte
         contador_UL = int(Pacote_UL[14]*256) + Pacote_UL[15]
         ultimo_pacote_DL = int(Pacote_UL[12]*256) + Pacote_UL[13]

   # Camada de Aplicação      
         # Processamento da Luminosidade (LDR)
         # Reconstrói valor de 10 bits 
         luminosidade = int(Pacote_UL[17] * 256) + Pacote_UL[18]
         
   else:
      perda_geral = perda_geral+1
      print("##### FALHA - Pacote não recebido")

#========== Armazenamento de Dados no LOG de pacote
def gravaLOG_Pacote():
   log = open(arquivo_LOG_pacote, 'a')
   print(strftime("%d/%m/%Y %H:%M:%S"),";",Pacote_UL, file=log)
   log.close()
        
#========== Armazenamento de Dados para Exibição
def gravaLOG_Gerencia():
     global rssi_max_dl, rssi_min_dl, rssi_max_ul, rssi_min_ul

     # 1. Grava no arquivo temporário (.tmp) para o Nível 6 Rede ler
     gerencia = open(os.path.join(dir_nivel4, 'dados_gerencia.tmp'), 'a')
     print(medida_atual, ";", rssi_DL, ";", round(psr_geral, 2), ";", round(psr_geral, 2), ";", rssi_UL, ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, file=gerencia, sep='')
     gerencia.close()
     
     # 2. Grava no arquivo de LOG definitivo
     log_def = open(arquivo_LOG_gerencia, 'a')
     print(strftime("%d/%m/%Y %H:%M:%S"), ";", medida_atual, ";", rssi_DL, ";", rssi_UL, ";", perda_geral, ";", round(psr_geral, 2), ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, file=log_def, sep='')
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
    global medida_atual, perda_geral, psr_geral
    if medida_atual > 0:
        # Sucesso = Total tentado (medida_atual) - Falhas (perda_geral)
        pacotes_recebidos = medida_atual - perda_geral
        psr_geral = (pacotes_recebidos / medida_atual) * 100
    else:
        psr_geral = 0.0

#===========Calculo de Máximos e Mínimos RSSI
def calculaMaxMinRSSI():
    global rssi_DL, rssi_UL, rssi_max_dl, rssi_min_dl, rssi_max_ul, rssi_min_ul
    if rssi_DL > rssi_max_dl: rssi_max_dl = rssi_DL
    if rssi_DL < rssi_min_dl: rssi_min_dl = rssi_DL
    if rssi_UL > rssi_max_ul: rssi_max_ul = rssi_UL
    if rssi_UL < rssi_min_ul: rssi_min_ul = rssi_UL

#========== Leitura de Parâmetros =============
while True:
   # Leitura constante do arquivo de parâmetros
   if os.path.exists(arquivo_parametros):
       Parametros = open(arquivo_parametros, 'r')
       line = Parametros.readline()
       if len(line) > 0: condicao_start = int(line)
       line = Parametros.readline()
       if len(line) > 0: numero_de_medidas = int(line)
       line = Parametros.readline()
       if len(line) > 0: valor_spreadingfactor = int(line)
       line = Parametros.readline()
       if len(line) > 0: valor_bandwidth = int(line)
       line = Parametros.readline()
       if len(line) > 0: valor_codingrate = int(line)       
       Parametros.close()

   valor_new_SF = valor_spreadingfactor
   print("### VALOR SPREADING FACTOR: ", valor_new_SF)
   
   if (valor_bandwidth == 125000):
       valor_new_BW = 1
   elif (valor_bandwidth == 250000):
       valor_new_BW = 2
   elif (valor_bandwidth == 500000):  
       valor_new_BW = 3
   print("### VALOR BANDWIDTH: ", valor_new_BW)
   
   valor_new_CR = valor_codingrate
   print("### VALOR CONDINGRATE: ", valor_new_CR)

   # Tentativa de Conexão Serial Automática (Se estiver desconectado)
   if ser is None:
       try:
           # Ajuste a porta aqui (/dev/ttyUSB0 ou COMx)
           print("Configuração da porta serial (caminho completo)")
           print("Para Windows: COM3, COM4, etc")
           print("Para Linux: /dev/ttyUSB0 , /dev/ttyUSB1, etc")
           porta_serial = input("Digite aqui:")
           ser = serial.Serial(porta_serial, 115200, timeout=0.5, parity=serial.PARITY_NONE)
           print("Porta Serial Conectada")
       except:
           pass # Se der erro, tenta de novo na próxima volta


   if (condicao_start == 1):
       
      #Apenas para imprimir um cabeçalho dos testes no terminal
      if (medida_atual == 0): # and (start_teste_site_suvey == 1)):
         print("################## Iniciando testes #################")
         
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
         print ('Time stamp;Contador;RSSI_DL;RSSI_UL;Perdas;PSR;Max_DL;Min_DL;Max_UL;Min_UL', file=f)
         f.close()
         
         f = open(arquivo_LOG_aplicacao, 'w')
         print ('Time stamp;Medida;Luminosidade', file=f)
         f.close()
         
         # Limpa temporários
         open(os.path.join(dir_nivel4, 'dados_gerencia.tmp'), 'w').close()
         open(os.path.join(dir_nivel4, 'dados_aplicacao.tmp'), 'w').close()
      
      if (medida_atual < numero_de_medidas):
         # if (medida_atual < (numero_de_medidas + start_teste_site_suvey)):
         # Compara se há alteração na configuração do rádio LoRa e faz processo de modificação dos novos valores de rádio
         if ((valor_new_SF != valor_run_SF) or (valor_new_BW != valor_run_BW) or (valor_new_CR != valor_run_CR)):
            cmd_new_config = 1
            print("### DETECTADO MUDANÇA DE CONFIG RADIO LORA ###", cmd_new_config)

            config_radio_lora()
           
            valor_run_SF = valor_new_SF
            valor_run_BW = valor_new_BW
            valor_run_CR = valor_new_CR
            cmd_new_config = 0
            # confirm_new_config = 0 # zera confirm
         else:
            start_teste_site_suvey = 0
            cmd_new_config = 0 # zera cmd
            confirm_new_config = 0 # zera cmd
 

         medida_atual = medida_atual + 1
         print("### Medida:",medida_atual, "de ",numero_de_medidas)

         downlink()
         time.sleep(tempo_entre_medidas)        
         uplink()
         
         gravaLOG_Pacote()
         calculaPSR()
         calculaMaxMinRSSI()
         gravaLOG_Gerencia()
         gravaLOG_Aplicacao()
         
         
      else:
         # Se atingiu o limite, para o script alterando o arquivo PARAMETROS
         print("################## Testes finalizados ##################")
         condicao_start = 0
         medida_atual = 0
         #Atualiza arquivo de Parâmetros   
         Parametros = open(arquivo_parametros, 'w')
         Parametros.write("0\n0\n") 
         Parametros.close()
   else:
     medida_atual = 0 # Garante que próximo teste comece do zero
     print("Script pausado") # Comentado para não poluir
     time.sleep(2)

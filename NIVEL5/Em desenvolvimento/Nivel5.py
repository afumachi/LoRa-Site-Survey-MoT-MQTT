import os
import math
import statistics
import time
import numpy as np

file_gerencia = os.path.join(os.path.dirname(__file__), '../NIVEL4/dados_gerencia.tmp')
file_abstracao = os.path.join(os.path.dirname(__file__), '../NIVEL4/dados_abstracao.txt')
# file_media_movel = os.path.join(os.path.dirname(__file__), '../NIVEL_4/dados_media_movel.txt')

if os.path.exists(file_abstracao):
   os.remove(file_abstracao)

Gerencia = open(file_gerencia, 'a+')
Gerencia.close()
Abstracao = open(file_abstracao, 'a+')
Abstracao.close()
# MediaMovel = open(file_media_movel, 'a+')
# MediaMovel.close()

# s = open(file_abstracao,'w')
# s.write("0"+"\n")
# s.write("0"+"\n")
# s.write("0"+"\n")
# s.close()

global max_rssi, min_rssi, rssi_media_dbm, desv_pad_rssi_dbm, num_mm

global max_rssiu, min_rssiu, rssi_media_dbmu, desv_pad_rssi_dbmu

global PSR_DL

global PSR_UL

num_mm = 0
max_rssi = -100.0
min_rssi = -10.0
rssi_media_dbm = 0
desv_pad_rssi_dbm = 0
PSR_DL = 0
PSR_UL = 0
snr_DL = 0
snr_UL = 0

rssi_u= 0
rssi_media_u = 0
desv_pad_rssi_dbmu = 0
rssi_media_dbmu = 0
max_rssiu = -100.0
min_rssiu = -10.0
    
def grava_abstracao():
    s = open(file_abstracao,'w')
    s.write(str(max_rssi)+"\n")
    s.write(str(min_rssi)+"\n")
    s.write(str(rssi_media_dbm)+"\n")
    s.write(str(desv_pad_rssi_dbm)+"\n")
    s.write(str(PSR_DL)+"\n")
    s.write(str(PSR_UL)+"\n")
    s.write(str(max_rssiu)+"\n")
    s.write(str(min_rssiu)+"\n")
    s.write(str(rssi_media_dbmu)+"\n")
    s.write(str(desv_pad_rssi_dbmu)+"\n")
    s.close()

# print(medida_atual, ";", rssi_DL, ";", round(psr_geral, 2), ";", round(psr_geral, 2), ";", rssi_UL, ";", rssi_max_dl, ";", rssi_min_dl, ";", rssi_max_ul, ";", rssi_min_ul, ";", valor_atual_spreadingfactor, ";", valor_atual_bandwidth, ";", valor_atual_codingrate, ";", valor_atual_potencia_radio, ";", round(taxa_canal_teorica, 2), ";", round(taxa_canal_calculada, 2), ";", round(snr_DL, 2), ";", round(snr_UL, 2), file=gerencia, sep='')

def calcula_maximo_minimo(valor):
    global max_rssi, min_rssi

    if (valor > max_rssi):
        max_rssi = valor

    if (valor < min_rssi):
        min_rssi = valor

def calcula_maximo_minimou(valor):
    global max_rssiu, min_rssiu

    if (valor > max_rssiu):
        max_rssiu = valor

    if (valor < min_rssiu):
        min_rssiu = valor

def captura_dados():
    dados = open(file_gerencia,'r')

    global s1
    global rssi_media_dbm
    global max_rssi, min_rssi
    global desv_pad_rssi_dbm

    global rssi_media_dbmu
    global max_rssiu, min_rssiu
    global desv_pad_rssi_dbmu

    global PSR_DL
    global PSR_UL

    x = [] #RSSI DOWN LINK
    xUP = [] #RSSI UP LINK
    
    y = []
    z= []


    for line in dados:
        line=line.strip()
        Y = line.split(';')
        y.append(Y)
   
    # RSSI DOWN LINK
    
    rssi_w = 0
    rssi_media_w = 0
    rssi_media_dbm = 0
    max_rssi = -100.0
    min_rssi = -10.0
    rssi_w = 0

    # RSSI UP LINK
    rssi_u= 0    
    rssi_media_u = 0
    rssi_media_dbmu = 0
    max_rssiu = -100.0
    min_rssiu = -10.0
    
    for i in range(len(y)):
        if((y[i][1])!='')and((y[i][2])!=''):
           
            rssi_dbm = float(y[i][1])
            rssi_UP = float(y[i][4])
                            
            x.append(rssi_dbm)
            xUP.append(rssi_UP)
                            
            z.append(int(y[i][0]))
                            
            if (len(x) > num_mm):
               #média aritmética da RSSI DOWN LINK
                rssi_media_dbm = np.mean(x)

               #média aritmética da RSSI UP LINK
                rssi_media_dbmu = np.mean(xUP)

            calcula_maximo_minimo(rssi_dbm)
            calcula_maximo_minimou(rssi_UP)



    if (len(x) > 1):
        desv_pad_rssi_dbm = statistics.stdev(x)
        desv_pad_rssi_dbmu = statistics.stdev(xUP)
                            
        PSR_DL = y[-1][2]
        PSR_UL = y[-1][3]

    grava_abstracao()
    dados.close()

ultima_condicao_start = 0
print("NIVEL 5 Iniciado")
                            
while True:
    param_n6_n1 = open(os.path.join(os.path.dirname(__file__), '../NIVEL4/PARAMETROS.txt'), 'r')
    condicao_start = param_n6_n1.readline()
    num_mm = param_n6_n1.readline()
    num_mm = param_n6_n1.readline()

    if (num_mm != ''):
        num_mm = int(num_mm)
    if (condicao_start != ''):
        condicao_start = int(condicao_start)
        param_n6_n1.close()

    if(ultima_condicao_start == 1 and condicao_start == 0):
        grava_abstracao()
    
    if(ultima_condicao_start == 0 and condicao_start == 1):
        Abstracao = open(file_abstracao, 'w').close()
    
    if(condicao_start == 1):
        time.sleep(.05)
        # s = open(file_abstracao,'w')
        # s.write("0"+"\n")
        # s.write("0"+"\n")
        # s.write("0"+"\n")
        # s.write("0"+"\n")
        # s.write("0"+"\n")
        # s.close()
        captura_dados()
    else:
        time.sleep(1)

    ultima_condicao_start = condicao_start

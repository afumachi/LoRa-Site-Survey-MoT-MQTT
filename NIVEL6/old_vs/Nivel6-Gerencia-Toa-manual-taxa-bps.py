
import time
import os
import tkinter.messagebox as tkMessageBox
import tkinter.ttk as ttk
import tkinter.filedialog

import tkinter
from tkinter import *
#import tkinter.messagebox as tkMessageBox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

from matplotlib.figure import Figure
import math



#----------------------------- CRIAÇÃO DA JANELA PRINCIPAL ---------------------
janela_principal=Tk() # Criando a tela principal, usando um objeto TKinter
janela_principal.title("LORA SITE SURVEY VERSÃO ESP32 - ToA MANUAL com TAXA DE TRANSMISSÃO") # Função para alterar titulo da janela
janela_principal.geometry('1300x920') #1300x700 # Define o tamanho da janela
janela_principal.resizable(True, True) # Possibilita o redimensionamento da janela principal
#-------------------------------------------------------------------------------


#------------------------- CRIAÇÃO DA REGIÃO DE PARAMETRIZAÇÃO -----------------
reg_parametrizacao = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_parametrizacao.place(x=10,y=10,width=300,height=380) 

titulo_parametrizacao = Label(reg_parametrizacao, font=("Arial", 14, "bold"),text = "Configurações LoRa",padx=5,pady=5).pack(side=TOP, anchor="n")
#-------------------------------------------------------------------------------

#---------------------- CRIAÇÃO DO INTERVALO DE MEDIDAS ------------------------
intervalo = Label(reg_parametrizacao, text = "Qtde. de Medidas", font=("Arial", 12))
intervalo.place(x=20,y=40)
valor_intervalo=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_intervalo.place(x=170,y=40)
valor_intervalo.insert(0, "0")

#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
tempo_tx_rx = Label(reg_parametrizacao, text = "Tempo de Rádio", font=("Arial", 12))
tempo_tx_rx.place(x=20,y=75)
tempoinfo = Label(reg_parametrizacao, text = "Em segundos", font=("Arial", 8))
tempoinfo.place(x=30,y=95)
valor_tempo_tx_rx=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_tempo_tx_rx.place(x=170,y=75)
valor_tempo_tx_rx.insert(0, "7")


#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
spreadingfactor = Label(reg_parametrizacao, text = "Spreading Factor", font=("Arial", 12))
spreadingfactor.place(x=20,y=110)
spreadingfactorinfo = Label(reg_parametrizacao, text = "7 a 12", font=("Arial", 8))
spreadingfactorinfo.place(x=30,y=130)
valor_spreadingfactor=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_spreadingfactor.place(x=170,y=110)
valor_spreadingfactor.insert(0, "12")


#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
bandwidth = Label(reg_parametrizacao, text = "Bandwidth", font=("Arial", 12))
bandwidth.place(x=20,y=145)
bandwidthinfo = Label(reg_parametrizacao, text = "125, 250, 500 kHz", font=("Arial", 8))
bandwidthinfo.place(x=30,y=165)
valor_bandwidth=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_bandwidth.place(x=170,y=145)
valor_bandwidth.insert(0, "125")


#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
codingrate = Label(reg_parametrizacao, text = "CodingRate", font=("Arial", 12))
codingrate.place(x=20,y=180)
codingrateinfo = Label(reg_parametrizacao, text = "5 a 8 => 4/5, 4/6, 4/7, 4/8", font=("Arial", 8))
codingrateinfo.place(x=30,y=200)
valor_codingrate=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_codingrate.place(x=170,y=180)
valor_codingrate.insert(0, "8")



#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
potencia_radio = Label(reg_parametrizacao, text = "Potência de Rádio", font=("Arial", 12))
potencia_radio.place(x=20,y=215)
potencia_radioinfo = Label(reg_parametrizacao, text = "2 a 20dBm", font=("Arial", 8))
potencia_radioinfo.place(x=30,y=235)
valor_potencia_radio=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_potencia_radio.place(x=170,y=215)
valor_potencia_radio.insert(0, "20")



# Label de Feedback de Status
status_texto = StringVar()
status_texto.set("AGUARDANDO...")
label_status = Label(reg_parametrizacao, textvariable=status_texto, font=("Arial", 10, "bold"), fg="gray")
label_status.place(x=25, y=300)


lss_status = Label(reg_parametrizacao, font=("Arial", 12, "bold"), text="STATUS LSS :", fg="blue", padx=5, pady=5)
lss_status.place(x=20,y=325)

lss_status_texto = StringVar()
lss_status_texto.set("TESTE LSS PARADO")
label_lss_status = Label(reg_parametrizacao, textvariable=lss_status_texto, font=("Arial", 12, "bold"), fg="green", padx=5, pady=5)
label_lss_status.place(x=20, y=350)

def captura_num_medidas():
    if valor_intervalo.get() == "":
        num_medidas = 0
    else:
        num_medidas = int(valor_intervalo.get())
        
    if(num_medidas <= 0):
         num_medidas = 10

    return int(num_medidas)


def captura_num_spreadingfactor():
    if valor_spreadingfactor.get() == "":
        num_spreadingfactor = 12
    else:
        num_spreadingfactor = int(valor_spreadingfactor.get())

    if(num_spreadingfactor <= 7):
        num_spreadingfactor = 7

    if(num_spreadingfactor >= 12):
        num_spreadingfactor = 12
        
    return int(num_spreadingfactor)



def captura_num_bandwidth():
    if valor_bandwidth.get() == "":
        num_bandwidth = 125
    else:
        num_bandwidth = int(valor_bandwidth.get())
        
    if(num_bandwidth < 200):
         num_bandwidth = 125

    if((num_bandwidth >= 200) and (num_bandwidth < 350)):
         num_bandwidth = 250    

    if(num_bandwidth >= 350):
         num_bandwidth = 500

    return int(num_bandwidth)



def captura_num_codingrate():
    if valor_codingrate.get() == "":
        num_codingrate = 8
    else:
        num_codingrate = int(valor_codingrate.get())
        
    if(num_codingrate <= 5):
         num_codingrate = 5

    if(num_codingrate >= 8):
        num_codingrate = 8

    return int(num_codingrate)



def captura_num_potencia_radio():
    if valor_potencia_radio.get() == "":
        num_potencia_radio = 20
    else:
        num_potencia_radio = int(valor_potencia_radio.get())
        
    if(num_potencia_radio <= 2):
         num_potencia_radio = 2

    if(num_potencia_radio >= 20):
        num_potencia_radio = 20

    return int(num_potencia_radio)



def captura_num_tempo_tx_rx():
    if valor_tempo_tx_rx.get() == "":
        num_tempo = 7
    else:
        num_tempo = int(valor_tempo_tx_rx.get())
        
    if(num_tempo <= 1):
         num_tempo = 1

    if(num_tempo >= 10):
        num_tempo = 10

    return int(num_tempo)

#------------------------------ GRAVACAO DOS COMANDOS --------------------------
def grava_comandos(condicao_start):
    arquivo_txt = os.path.join(os.path.dirname(__file__), '../NIVEL4/PARAMETROS.txt') 
    s = open(arquivo_txt,'w')
    s.write(str(condicao_start)+"\n")      # Linha 1: Start/Stop
    s.write(str(captura_num_medidas())+"\n") # Linha 2: Numero de medidas
    s.write(str(captura_num_spreadingfactor())+"\n") # Linha 3: Spreading Factor
    s.write(str(captura_num_bandwidth())+"\n") # Linha 4: Bandwidth
    s.write(str(captura_num_codingrate())+"\n") # Linha 5: CodingRate Denominator
    s.write(str(captura_num_potencia_radio())+"\n") # Linha 6: TX POWER
    s.write(str(captura_num_tempo_tx_rx())+"\n") # Linha 7: TEMPO TX RX
    s.close()
#-------------------------------------------------------------------------------

#------------------------------ CRIAÇÃO DO BOTÃO -------------------------------
def iniciar_teste():
    grava_comandos(1)
    status_texto.set("TESTE EM ANDAMENTO...")
    label_status.config(fg="green")

bot_ini_teste=Button(reg_parametrizacao,text="INICIAR TESTE",font=("Arial", 13, "bold"), width=20,command=iniciar_teste)
bot_ini_teste.place(x=25,y=260) 
bot_ini_teste.config(state="normal")
#-------------------------------------------------------------------------------

#------------------------- CRIAÇÃO DA REGIÃO DE DESEMPENHO ---------------------
reg_desempenho = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
#reg_desempenho.place(x=10,y=240,width=300,height=410) 
reg_desempenho.place(x=10,y=400,width=300,height=610) # y=340

titulo_desempenho = Label(reg_desempenho, font=("Arial", 13, "bold"),text = "Intensidade do Sinal",padx=5,pady=5).pack(side=TOP, anchor="n")

# --- CABEÇALHOS ---
RDONW = Label(reg_desempenho, font=("Arial", 12, "bold"), text="RSSI DOWNLINK", fg="blue", padx=5, pady=5)
RDONW.place(x=10, y=45, anchor="w") 

RUP = Label(reg_desempenho, font=("Arial", 12, "bold"), text="RSSI UPLINK", fg="green", padx=5, pady=5)
RUP.place(x=10, y=150, anchor="w")


RPSRS = Label(janela_principal, font=("Arial", 14, "bold"), text="DESEMPENHO", fg="black", padx=5, pady=5)
RPSRS.place(x=1185, y=30, anchor="center")


RPSRD = Label(janela_principal, font=("Arial", 14, "bold"), text="DA REDE", fg="black", padx=5, pady=5)
RPSRD.place(x=1185, y=55, anchor="center")

RPSR = Label(janela_principal, font=("Arial", 14, "bold"), text="PSR (Geral)", fg="blue", padx=5, pady=5)
RPSR.place(x=1090, y=100, anchor="w")

RPSRL = Label(janela_principal, font=("Arial", 10, "bold"), text="________________________", fg="black", padx=5, pady=5)
RPSRL.place(x=1090, y=145, anchor="w")

RTCH = Label(janela_principal, font=("Arial", 13, "bold"), text="Taxa Teórica", fg="blue", padx=5, pady=5)
RTCH.place(x=1090, y=170, anchor="w")

RTCHRE = Label(janela_principal, font=("Arial", 13, "bold"), text="Taxa Efetiva", fg="green", padx=5, pady=5)
RTCHRE.place(x=1090, y=230, anchor="w")

RTCHREL = Label(janela_principal, font=("Arial", 10, "bold"), text="________________________", fg="black", padx=5, pady=5)
RTCHREL.place(x=1090, y=275, anchor="w")

RTSND = Label(janela_principal, font=("Arial", 13, "bold"), text="SNR Downlink", fg="blue", padx=5, pady=5)
RTSND.place(x=1090, y=300, anchor="w")

RTSNU = Label(janela_principal, font=("Arial", 13, "bold"), text="SNR Uplink", fg="green", padx=5, pady=5)
RTSNU.place(x=1090, y=360, anchor="w")

RTSNUL = Label(janela_principal, font=("Arial", 10, "bold"), text="________________________", fg="black", padx=5, pady=5)
RTSNUL.place(x=1090, y=405, anchor="w")

RCDL = Label(janela_principal, font=("Arial", 13, "bold"), text="Downlinks", fg="blue", padx=5, pady=5)
RCDL.place(x=1090, y=430, anchor="w")

RCUL = Label(janela_principal, font=("Arial", 13, "bold"), text="Uplinks", fg="green", padx=5, pady=5)
RCUL.place(x=1090, y=490, anchor="w")

RCULL = Label(janela_principal, font=("Arial", 10, "bold"), text="________________________", fg="black", padx=5, pady=5)
RCULL.place(x=1090, y=535, anchor="w")

RPERDA = Label(janela_principal, font=("Arial", 13, "bold"), text="Pacotes Perdidos", fg="red", padx=5, pady=5)
RPERDA.place(x=1090, y=570, anchor="w")

RPER = Label(janela_principal, font=("Arial", 14, "bold"), text="PER (Geral)", fg="red", padx=5, pady=5)
RPER.place(x=1090, y=630, anchor="w")

# --- VARIÁVEIS DE TEXTO ---
str_atual_dl = StringVar()
str_max_dl = StringVar()
str_min_dl = StringVar()

str_atual_ul = StringVar()
str_max_ul = StringVar()
str_min_ul = StringVar()

str_atual_psr = StringVar()

srt_atual_taxa_canal = StringVar()

srt_atual_taxa_real_canal = StringVar()

srt_snr_DL = StringVar()
srt_snr_UL = StringVar()

srt_medida_atual_DL =StringVar()
srt_counter_DL = StringVar()
srt_counter_UL = StringVar()
srt_perda_total_UL = StringVar()

str_atual_per = StringVar()

str_lss_status =StringVar()

# Inicialização
str_atual_dl.set("Atual: -- dBm")
str_max_dl.set("Máx: 0 dBm")
str_min_dl.set("Mín: 0 dBm")

str_atual_ul.set("Atual: -- dBm")
str_max_ul.set("Máx: 0 dBm")
str_min_ul.set("Mín: 0 dBm")

str_atual_psr.set("Atual: -- %")

srt_atual_taxa_canal.set("Teórica: -- bps")

srt_atual_taxa_real_canal.set("Real: -- bps")

srt_snr_DL.set(" -- dB")

srt_snr_UL.set(" -- dB")


srt_medida_atual_DL.set(" -- Pacotes")

srt_counter_UL.set(" -- Pacotes")

srt_perda_total_UL.set(" -- Pacotes")

str_atual_per.set("Atual: -- %")



# --- LABELS DOWNLINK ---
lbl_atual_dl = Label(reg_desempenho, font=("Arial", 11, "bold"),textvariable = str_atual_dl,padx=5,pady=2)
lbl_atual_dl.place(x=10, y=60) 
lbl_max_dl = Label(reg_desempenho, font=("Arial", 11),textvariable = str_max_dl,padx=5,pady=2)
lbl_max_dl.place(x=10, y=85) 
lbl_min_dl = Label(reg_desempenho, font=("Arial", 11),textvariable = str_min_dl,padx=5,pady=2)
lbl_min_dl.place(x=10, y=110) 

# --- LABELS UPLINK ---
lbl_atual_ul = Label(reg_desempenho, font=("Arial", 11, "bold"),textvariable = str_atual_ul,padx=5,pady=2)
lbl_atual_ul.place(x=10, y=165) 
lbl_max_ul = Label(reg_desempenho, font=("Arial", 11),textvariable = str_max_ul,padx=5,pady=2)
lbl_max_ul.place(x=10, y=190) 
lbl_min_ul = Label(reg_desempenho, font=("Arial", 11),textvariable = str_min_ul,padx=5,pady=2)
lbl_min_ul.place(x=10, y=215) 


# --- LABELS PSR ---
lbl_atual_psr = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = str_atual_psr,padx=5,pady=2)
lbl_atual_psr.place(x=1090, y=130, anchor="w") 


# --- LABELS TAXA DO CANAL ---
lbl_atual_taxa_canal = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_atual_taxa_canal,padx=5,pady=2)
lbl_atual_taxa_canal.place(x=1090, y=195, anchor="w") 

# --- LABELS TAXA REAL DO CANAL ---
lbl_atual_taxa_real_canal = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_atual_taxa_real_canal,padx=5,pady=2)
lbl_atual_taxa_real_canal.place(x=1090, y=255, anchor="w") 


# --- LABELS SNR ---
# snr DL
lbl_snr_dl = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_snr_DL,padx=5,pady=2)
lbl_snr_dl.place(x=1090, y=325, anchor="w") 

# snr UL
lbl_snr_ul = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_snr_UL,padx=5,pady=2)
lbl_snr_ul.place(x=1090, y=385, anchor="w") 


# --- LABELS CONTADORES ---

# counter medida atual DL
lbl_medida_atual_dl = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_medida_atual_DL,padx=5,pady=2)
lbl_medida_atual_dl.place(x=1090, y=455, anchor="w") 

# counter Feedback UL
lbl_counter_ul = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_counter_UL,padx=5,pady=2)
lbl_counter_ul.place(x=1090, y=515, anchor="w") 

# counter LOST PKT
lbl_perda_total_ul = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = srt_perda_total_UL,padx=5,pady=2)
lbl_perda_total_ul.place(x=1090, y=595, anchor="w") 

# PER%
lbl_per = Label(janela_principal, font=("Arial", 13, "bold"),textvariable = str_atual_per,padx=5,pady=2)
lbl_per.place(x=1090, y=655, anchor="w") 


#-------------------------------------------------------------------------------


#---------------------------- CRIAÇÃO DA REGIÃO DE GRÁFICO ---------------------
reg_grafico = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_grafico.place(x=320, y=10, width=750, height=790) 
#-------------------------------------------------------------------------------


#----------------------------- CRIAÇÃO DO GRÁFICO ----------------------
style.use("ggplot")

def grafico_rssi(f,c):

        f.clear()
    
        x = [] #RSSI DOWN LINK
        xUP = [] #RSSI UP LINK
    
        y = []
        z= []

        psr_dl=[] 
        
        # Variáveis locais para guardar o último valor de Max/Min lido
        ultimo_max_dl = "0"
        ultimo_min_dl = "0"
        ultimo_max_ul = "0"
        ultimo_min_ul = "0"
        taxa_canal_teorica = "0"
        taxa_canal_calculada = "0"
        snr_DL = "0"
        snr_UL = "0"
        medida_atual_DL = "0"
        counter_DL = "0"
        counter_UL = "0"
        perda_total_UL = "0"
        atual_per = "0"
        lss_status = "0"
        
        
        # Leitura do arquivo .tmp
        path_tmp = os.path.join(os.path.dirname(__file__), '../NIVEL4/dados_gerencia.tmp')
        
        if os.path.exists(path_tmp):
            try:
                dados = open(path_tmp,'r')
                for line in dados:
                    line=line.strip()
                    Y = line.split(';')
                    y.append(Y)
                dados.close()
            except:
                pass

        for i in range(len(y)):
            # Agora verificamos se tem 9 colunas (as 5 originais + 4 novas de Max/Min)
            if len(y[i]) >= 15: #9
                if((y[i][0])!=''):
                    z.append(int(y[i][0]))     # Contador
                    x.append(float(y[i][1]))   # RSSI DL
                    psr_dl.append(float(y[i][2])) # PSR Geral
                    xUP.append(float(y[i][4])) # RSSI UL
                    
                    # Lê as colunas extras:
                    medida_atual_DL = y[i][0] # Coluna 6 (Indice 5)
                    ultimo_max_dl = y[i][5] # Coluna 6 (Indice 5)
                    ultimo_min_dl = y[i][6] # Coluna 7 (Indice 6)
                    ultimo_max_ul = y[i][7] # Coluna 8 (Indice 7)
                    ultimo_min_ul = y[i][8] # Coluna 9 (Indice 8)
                    taxa_canal_teorica = y[i][13] # Coluna 14 (Indice 13)
                    taxa_canal_calculada = y[i][14] # Coluna 15 (Indice 14)
                    snr_DL = y[i][15] # Coluna 16 (Indice 15)
                    snr_UL = y[i][16] # Coluna 17 (Indice 16)
                    counter_DL = y[i][17] # Coluna 18 (Indice 17)
                    counter_UL = y[i][18] # Coluna 19 (Indice 18)
                    perda_total_UL = y[i][19] # Coluna 20 (Indice 19)
                    lss_status = y[i][20] # Coluna 21 (Indice 20)
                    


        # --- ATUALIZAÇÃO DOS VALORES "ATUAL" ---
        if len(x) > 0:
            str_atual_dl.set(f"Atual: {x[-1]} dBm")
        if len(xUP) > 0:
            str_atual_ul.set(f"Atual: {xUP[-1]} dBm")
        if len(psr_dl) > 0:
            str_atual_psr.set(f"Atual: {psr_dl[-1]} %")

        # --- SUBPLOT 1: RSSI DOWNLINK ---
        axis = f.add_subplot(311)
        axis.plot(z,x,label='RSSI DOWNLINK', color='blue')
        axis.set_ylabel('RSSI DL (dBm)')
        axis.legend(loc='upper right', fontsize='x-small')
    
        # --- SUBPLOT 2: RSSI UPLINK ---
        axis1 = f.add_subplot(312)
        axis1.plot(z,xUP,label='RSSI UPLINK', color='red')
        axis1.set_ylabel('RSSI UL (dBm)')
        axis1.legend(loc='upper right', fontsize='x-small')

        # --- SUBPLOT 3: PSR (GERAL) ---
        axis2 = f.add_subplot(313)
        axis2.plot(z, psr_dl, label='PSR (Geral)', color='green')
        axis2.set_ylabel('PSR (%)')
        axis2.set_xlabel('Medida')
        axis2.set_ylim(-5, 105) 
        axis2.legend(loc='upper right', fontsize='x-small')

        # Atualiza os textos da tela com o último valor lido do arquivo
        str_max_dl.set("Máx: " + ultimo_max_dl + " dBm")
        str_min_dl.set("Mín: " + ultimo_min_dl + " dBm") 
        
        str_max_ul.set("Máx: " + ultimo_max_ul + " dBm")
        str_min_ul.set("Mín: " + ultimo_min_ul + " dBm") 

        srt_atual_taxa_canal.set(taxa_canal_teorica + " bps")
        srt_atual_taxa_real_canal.set(taxa_canal_calculada + " bps")

        srt_snr_DL.set(snr_DL + " dB")
        
        srt_snr_UL.set(snr_UL + " dB")


        srt_medida_atual_DL.set(medida_atual_DL + " Pacotes")
                
        srt_counter_UL.set(counter_UL + " Pacotes")
        
        srt_perda_total_UL.set(perda_total_UL + " Pacotes")

        # Check if the list has at least one element
        if psr_dl:
            per_total = 100 - psr_dl[-1]
        else:
            per_total = 0  # Or 100, depending on your preferred starting state

        str_atual_per.set(f"Atual: {round(per_total, 2)} %")
        

        # Atualiza status for 0 E o texto ainda estiver dizendo "EM ANDAMENTO", atualiza.

        if lss_status == "1":
            lss_status_texto.set("LSS EM ANDAMENTO")
            label_lss_status.config(fg="green") 
        elif lss_status == "2":
            lss_status_texto.set("LSS TESTE ENLACE")
            label_lss_status.config(fg="green")
        elif lss_status == "3":
            lss_status_texto.set("LSS MUDA RÁDIO")
            label_lss_status.config(fg="blue")
        elif lss_status == "4":
            lss_status_texto.set("LSS ENLACE PERDIDO")
            label_lss_status.config(fg="red") 
        
        # --- VERIFICAÇÃO AUTOMÁTICA DE STATUS (FIM DE TESTE) ---
        # Se encontrar "0" na primeira linha de PARAMETROS.txt, atualiza para FINALIZADO
        path_param = os.path.join(os.path.dirname(__file__), '../NIVEL4/PARAMETROS.txt')
        if os.path.exists(path_param):
            try:
                pp = open(path_param, 'r')
                status_lido = pp.readline().strip()
                pp.close()
                
                # Se o status for 0 E o texto ainda estiver dizendo "EM ANDAMENTO", atualiza.
                if status_lido == '0' and status_texto.get() == "TESTE EM ANDAMENTO...":
                    status_texto.set("TESTE LSS FINALIZADO")
                    label_status.config(fg="green")
                if lss_status == "0":
                    lss_status_texto.set("LSS PARADO")
                    label_lss_status.config(fg="green") 
            except:
                pass

        f.subplots_adjust(left=0.12, bottom=0.20, right=0.95, top=0.95, wspace=None, hspace=0.6)
        c.draw()
        
        janela_principal.after(800, grafico_rssi, f, c) 

def callback():
    if tkMessageBox.askokcancel("Sair", "Tem certeza que deseja sair?"):
        grava_comandos(0)
        status_texto.set("PARADO")
        label_status.config(fg="red")
        janela_principal.destroy()


fig = Figure(figsize=(8.5, 7.5), facecolor='white') 
canvas = FigureCanvasTkAgg(fig, master=reg_grafico)

canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
grafico_rssi(fig,canvas)  

#-------------------------------- RODA A JANELA PRINCIPAL ----------------------
janela_principal.protocol("WM_DELETE_WINDOW", callback)
janela_principal.mainloop()
janela_principal.update_idletasks()

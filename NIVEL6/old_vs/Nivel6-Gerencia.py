import tkinter
from tkinter import *
import tkinter.messagebox as tkMessageBox
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os
import math

#----------------------------- CRIAÇÃO DA JANELA PRINCIPAL ---------------------
janela_principal=Tk() # Criando a tela principal, usando um objeto TKinter
janela_principal.title("LORA SITE SURVEY VERSÃO 1") # Função para alterar titulo da janela
janela_principal.geometry('1000x820') # Define o tamanho da janela
janela_principal.resizable(True, True) # Possibilita o redimensionamento da janela principal
#-------------------------------------------------------------------------------

#------------------------- CRIAÇÃO DA REGIÃO DE PARAMETRIZAÇÃO -----------------
reg_parametrizacao = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_parametrizacao.place(x=10,y=10,width=300,height=470) 

titulo_parametrizacao = Label(reg_parametrizacao, font=("Arial", 14, "bold"),text = "Configurações LoRa",padx=5,pady=5).pack(side=TOP, anchor="n")
#-------------------------------------------------------------------------------

#---------------------- CRIAÇÃO DO INTERVALO DE MEDIDAS ------------------------
intervalo = Label(reg_parametrizacao, text = "Qtde. de Medidas", font=("Arial", 12))
intervalo.place(x=20,y=40)
valor_intervalo=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_intervalo.place(x=170,y=40)
valor_intervalo.insert(0, "0")

#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
spreadingfactor = Label(reg_parametrizacao, text = "Spreading Factor", font=("Arial", 12))
spreadingfactor.place(x=20,y=70)
valor_spreadingfactor=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_spreadingfactor.place(x=170,y=70)
valor_spreadingfactor.insert(0, "12")


#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
bandwidth = Label(reg_parametrizacao, text = "Bandwidth", font=("Arial", 12))
bandwidth.place(x=20,y=100)
valor_bandwidth=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_bandwidth.place(x=170,y=100)
valor_bandwidth.insert(0, "125000")


#---------------------- CRIAÇÃO DOS CAMPOS DE CONFIGURAÇÕES DE RÁDIO LORA ------------------------
codingrate = Label(reg_parametrizacao, text = "CodingRate", font=("Arial", 12))
codingrate.place(x=20,y=130)
valor_codingrate=Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_codingrate.place(x=170,y=130)
valor_codingrate.insert(0, "5")



# Label de Feedback de Status
status_texto = StringVar()
status_texto.set("AGUARDANDO...")
label_status = Label(reg_parametrizacao, textvariable=status_texto, font=("Arial", 10, "bold"), fg="gray")
label_status.place(x=25, y=230) 

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
        num_bandwidth = 125000
    else:
        num_bandwidth = int(valor_bandwidth.get())
        
    if(num_bandwidth < 200000):
         num_spreadingfactor = 125000

    if((num_bandwidth >= 200000) or (num_bandwidth < 350000)):
         num_spreadingfactor = 250000    

    if(num_bandwidth >= 350000):
         num_spreadingfactor = 500000

    return int(num_bandwidth)



def captura_num_codingrate():
    if valor_codingrate.get() == "":
        num_codingrate = 5
    else:
        num_codingrate = int(valor_codingrate.get())
        
    if(num_codingrate <= 5):
         num_codingrate = 5

    if(num_codingrate >= 8):
        num_codingrate = 8

    return int(num_codingrate)


#------------------------------ GRAVACAO DOS COMANDOS --------------------------
def grava_comandos(condicao_start):
    arquivo_txt = os.path.join(os.path.dirname(__file__), '../NIVEL4/PARAMETROS.txt') 
    s = open(arquivo_txt,'w')
    s.write(str(condicao_start)+"\n")      # Linha 1: Start/Stop
    s.write(str(captura_num_medidas())+"\n") # Linha 2: Numero de medidas
    s.write(str(captura_num_spreadingfactor())+"\n") # Linha 3: Spreading Factor
    s.write(str(captura_num_bandwidth())+"\n") # Linha 4: Bandwidth
    s.write(str(captura_num_codingrate())+"\n") # Linha 5: CodingRate Denominator
    s.close()
#-------------------------------------------------------------------------------

#------------------------------ CRIAÇÃO DO BOTÃO -------------------------------
def iniciar_teste():
    grava_comandos(1)
    status_texto.set("TESTE EM ANDAMENTO...")
    label_status.config(fg="green")

bot_ini_teste=Button(reg_parametrizacao,text="INICIAR TESTE",font=("Arial", 14, "bold"), width=20,command=iniciar_teste)
bot_ini_teste.place(x=25,y=170) 
bot_ini_teste.config(state="normal")
#-------------------------------------------------------------------------------

#------------------------- CRIAÇÃO DA REGIÃO DE DESEMPENHO ---------------------
reg_desempenho = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
#reg_desempenho.place(x=10,y=240,width=300,height=410) 
reg_desempenho.place(x=10,y=290,width=300,height=410)

titulo_desempenho = Label(reg_desempenho, font=("Arial", 16, "bold"),text = "Desempenho de Rede",padx=5,pady=5).pack(side=TOP, anchor="n")

# --- CABEÇALHOS ---
RDONW = Label(reg_desempenho, font=("Arial", 13, "bold"), text="RSSI DOWNLINK", fg="blue", padx=5, pady=5)
RDONW.place(x=150, y=55, anchor="center") 

RUP = Label(reg_desempenho, font=("Arial", 13, "bold"), text="RSSI UPLINK", fg="red", padx=5, pady=5)
RUP.place(x=150, y=175, anchor="center")

RPSR = Label(reg_desempenho, font=("Arial", 13, "bold"), text="PSR (Geral)", fg="green", padx=5, pady=5)
RPSR.place(x=150, y=295, anchor="center")

# --- VARIÁVEIS DE TEXTO ---
str_atual_dl = StringVar()
str_max_dl = StringVar()
str_min_dl = StringVar()

str_atual_ul = StringVar()
str_max_ul = StringVar()
str_min_ul = StringVar()

str_atual_psr = StringVar()

# Inicialização
str_atual_dl.set("Atual: -- dBm")
str_max_dl.set("Máx: 0 dBm")
str_min_dl.set("Mín: 0 dBm")

str_atual_ul.set("Atual: -- dBm")
str_max_ul.set("Máx: 0 dBm")
str_min_ul.set("Mín: 0 dBm")

str_atual_psr.set("Atual: -- %")

# --- LABELS DOWNLINK ---
lbl_atual_dl = Label(reg_desempenho, font=("Arial", 12, "bold"),textvariable = str_atual_dl,padx=5,pady=2)
lbl_atual_dl.place(x=10, y=80) 
lbl_max_dl = Label(reg_desempenho, font=("Arial", 11),textvariable = str_max_dl,padx=5,pady=2)
lbl_max_dl.place(x=10, y=105) 
lbl_min_dl = Label(reg_desempenho, font=("Arial", 11),textvariable = str_min_dl,padx=5,pady=2)
lbl_min_dl.place(x=10, y=130) 

# --- LABELS UPLINK ---
lbl_atual_ul = Label(reg_desempenho, font=("Arial", 12, "bold"),textvariable = str_atual_ul,padx=5,pady=2)
lbl_atual_ul.place(x=10, y=200) 
lbl_max_ul = Label(reg_desempenho, font=("Arial", 11),textvariable = str_max_ul,padx=5,pady=2)
lbl_max_ul.place(x=10, y=225) 
lbl_min_ul = Label(reg_desempenho, font=("Arial", 11),textvariable = str_min_ul,padx=5,pady=2)
lbl_min_ul.place(x=10, y=250) 

# --- LABELS PSR ---
lbl_atual_psr = Label(reg_desempenho, font=("Arial", 14, "bold"),textvariable = str_atual_psr,padx=5,pady=2)
lbl_atual_psr.place(x=150, y=335, anchor="center") 


#-------------------------------------------------------------------------------


#---------------------------- CRIAÇÃO DA REGIÃO DE GRÁFICO ---------------------
reg_grafico = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_grafico.place(x=320, y=10, width=670, height=790) 
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
            if len(y[i]) >= 9:
                if((y[i][0])!=''):
                    z.append(int(y[i][0]))     # Contador
                    x.append(float(y[i][1]))   # RSSI DL
                    psr_dl.append(float(y[i][2])) # PSR Geral
                    xUP.append(float(y[i][4])) # RSSI UL
                    
                    # Lê as colunas extras:
                    ultimo_max_dl = y[i][5] # Coluna 6 (Indice 5)
                    ultimo_min_dl = y[i][6] # Coluna 7 (Indice 6)
                    ultimo_max_ul = y[i][7] # Coluna 8 (Indice 7)
                    ultimo_min_ul = y[i][8] # Coluna 9 (Indice 8)
        
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
                    status_texto.set("TESTE FINALIZADO")
                    label_status.config(fg="blue") 
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

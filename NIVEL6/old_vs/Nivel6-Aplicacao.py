

import time
import os
import tkinter.messagebox as tkMessageBox
import tkinter.ttk as ttk
import tkinter.filedialog

import tkinter
from tkinter import *
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os
import math




dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')

#========== Criação do arquivo de CMD LED AMARELO
CMD_LED_FILE = os.path.join(dir_nivel4, 'cmd_led_amarelo.txt')
# -------- ARQUIVO DE COMANDO DO LED AMARELO --------
# CMD_LED_FILE = "cmd_led_amarelo.txt"

if not os.path.exists(CMD_LED_FILE):
    with open(CMD_LED_FILE, "w") as f:
        f.write("0")

led_amarelo_estado = 0


def ler_estado_led():
    try:
        with open(CMD_LED_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val in ("0", "1") else 0
    except Exception:
        return 0


def escrever_estado_led(estado):
    try:
        with open(CMD_LED_FILE, "w") as f:
            f.write(str(estado))
    except Exception as e:
        print(f"Erro ao escrever cmd_led_amarelo.txt: {e}")


def toggle_led():
    global led_amarelo_estado
    led_amarelo_estado = 1 if led_amarelo_estado == 0 else 0
    escrever_estado_led(led_amarelo_estado)
    atualizar_botao_led()
    print(f"[N6] LED Amarelo → {'ON' if led_amarelo_estado else 'OFF'}")


def atualizar_botao_led():
    if led_amarelo_estado == 1:
        btn_led.config(text="LED AMARELO: ON",  bg="#FFD700", fg="#333333", activebackground="#FFC200")
    else:
        btn_led.config(text="LED AMARELO: OFF", bg="#555555", fg="#FFFFFF", activebackground="#444444")




#----------------------------- CRIAÇÃO DA JANELA PRINCIPAL ---------------------
janela_principal=Tk() 
janela_principal.title("MONITORAMENTO DE APLICAÇÃO (LUMINOSIDADE)") 
janela_principal.geometry('1300x720') 
janela_principal.resizable(True, True) 
#-------------------------------------------------------------------------------

#------------------------- CRIAÇÃO DA REGIÃO DE STATUS -----------------
reg_status = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_status.place(x=10,y=10,width=300,height=100) 

titulo_status = Label(reg_status, font=("Arial", 14, "bold"),text = "STATUS DO SISTEMA",padx=5,pady=5).pack(side=TOP, anchor="n")

# Variável de Texto para o Status
status_texto = StringVar()
status_texto.set("AGUARDANDO...")

# Label que mostra o status grande
label_status = Label(reg_status, textvariable=status_texto, font=("Arial", 16, "bold"), fg="gray")
label_status.place(x=150, y=55, anchor="center") 
#-------------------------------------------------------------------------------

#------------------------- CRIAÇÃO DA REGIÃO DE DADOS ---------------------
reg_dados = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_dados.place(x=10,y=120,width=300,height=410) 

titulo_dados = Label(reg_dados, font=("Arial", 16, "bold"),text = "DADOS APLICAÇÃO",padx=5,pady=5).pack(side=TOP, anchor="n")

# --- CABEÇALHOS ---
RLUM = Label(reg_dados, font=("Arial", 13, "bold"), text="LUMINOSIDADE", fg="orange", padx=5, pady=5)
RLUM.place(x=150, y=100, anchor="center") 

# --- VARIÁVEIS DE TEXTO ---
str_atual_lum = StringVar()
str_atual_lum.set("--")

# --- LABEL VALOR ---
lbl_atual_lum = Label(reg_dados, font=("Arial", 30, "bold"),textvariable = str_atual_lum,padx=5,pady=2)
lbl_atual_lum.place(x=150, y=150, anchor="center") 

#-------------------------------------------------------------------------------


RLAM = Label(reg_dados, font=("Arial", 11, "bold"), text="COMANDA LED AMARELO", fg="black", padx=5, pady=5)
RLAM.place(x=150, y=230, anchor="center") 


led_amarelo_estado = ler_estado_led()
#width=26,
btn_led = Button(reg_dados, text="", font=("Arial", 12, "bold"),
                 width=18, height=1, cursor="hand2", relief="raised", bd=3,
                 command=toggle_led)
btn_led.place(x=50, y=250)
atualizar_botao_led()


#-------------------------------------------------------------------------------

#---------------------------- CRIAÇÃO DA REGIÃO DE GRÁFICO ---------------------
reg_grafico = Frame(master=janela_principal,borderwidth=1, relief='sunken') 
reg_grafico.place(x=320, y=10, width=700, height=700) #width=670, height=790)
#-------------------------------------------------------------------------------

#----------------------------- CRIAÇÃO DO GRÁFICO ----------------------
style.use("ggplot")

def grafico_aplicacao(f,c):

        f.clear()
    
        x_medidas = [] 
        y_lum = [] 
        
        # Leitura do arquivo de APLICAÇÃO (.tmp)
        # Formato esperado: Medida ; Luminosidade
        path_tmp = os.path.join(os.path.dirname(__file__), '../NIVEL4/dados_aplicacao.tmp')
        
        if os.path.exists(path_tmp):
            try:
                dados = open(path_tmp,'r')
                for line in dados:
                    line=line.strip()
                    colunas = line.split(';')
                    
                    # Garante que tem pelo menos 2 colunas
                    if len(colunas) >= 2:
                        if (colunas[0] != ''):
                            x_medidas.append(int(colunas[0])) # Coluna 0: Medida
                            y_lum.append(int(colunas[1]))     # Coluna 1: Luminosidade
                dados.close()
            except:
                pass
        
        # --- ATUALIZAÇÃO DO VALOR "ATUAL" NA TELA ---
        if len(y_lum) > 0:
            str_atual_lum.set(f"{y_lum[-1]}")

        # --- PLOTAGEM DO GRÁFICO ---
        axis = f.add_subplot(111) # Apenas um gráfico grande
        axis.plot(x_medidas, y_lum, label='Luminosidade', color='orange')
        axis.set_ylabel('Luminosidade (0-4095)')
        axis.set_xlabel('Medida')
        axis.set_ylim(0, 4095) # Fixo para ADC de 10 bits
        axis.legend(loc='upper right', fontsize='medium')
    
        # --- LEITURA PASSIVA DO STATUS (Apenas para exibir na tela) ---
        path_param = os.path.join(os.path.dirname(__file__), '../NIVEL4/PARAMETROS.txt')
        if os.path.exists(path_param):
            try:
                pp = open(path_param, 'r')
                status_lido = pp.readline().strip()
                pp.close()
                
                if status_lido == '1':
                    status_texto.set("EM ANDAMENTO")
                    label_status.config(fg="green")
                else:
                    status_texto.set("PARADO")
                    label_status.config(fg="red")
            except:
                pass

        f.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.95)
        c.draw()
        
        # Chama a função novamente daqui a 800ms
        janela_principal.after(800, grafico_aplicacao, f, c) 

def callback():
    if tkMessageBox.askokcancel("Sair", "Tem certeza que deseja sair?"):
        janela_principal.destroy()

fig = Figure(figsize=(8.5, 7.5), facecolor='white') 
canvas = FigureCanvasTkAgg(fig, master=reg_grafico)

canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
grafico_aplicacao(fig,canvas)  

#-------------------------------- RODA A JANELA PRINCIPAL ----------------------
janela_principal.protocol("WM_DELETE_WINDOW", callback)
janela_principal.mainloop()
janela_principal.update_idletasks()

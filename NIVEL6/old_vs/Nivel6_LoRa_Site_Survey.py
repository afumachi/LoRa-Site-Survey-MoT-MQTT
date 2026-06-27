# =============================================================================
# NÍVEL 6 - SISTEMA UNIFICADO COM ABAS
# Versão: Unificado - Aplicação + Gerência + Conexão Serial
# Aba 1: Aplicação (Luminosidade + LED Amarelo com feedback UL)
# Aba 2: Gerência (LoRa Site Survey - RSSI, PSR, Taxa)
# Aba 3: Modelagem Multi-Wall - COST 231 
# Aba 4: Conexão Serial (Seleção de porta COM para Nível 3)
# =============================================================================

import time
import os
import tkinter.messagebox as tkMessageBox
import tkinter.ttk as ttk
import tkinter

from tkinter import *
import matplotlib
matplotlib.use('TkAgg')
from matplotlib import style
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math
import serial
import serial.tools.list_ports



# =============================================================================
# PATHS
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')

# =============================================================================
# REFRESH das telas
# =============================================================================

REFRESH_MS = 800   # Intervalo de atualização dos gráficos [ms] (200 ms)

# =============================================================================
# ARQUIVO DE COMANDO LED AMARELO
# =============================================================================
CMD_LED_FILE = os.path.join(dir_nivel4, 'cmd_led_amarelo.txt')
if not os.path.exists(CMD_LED_FILE):
    with open(CMD_LED_FILE, "w") as f:
        f.write("0")

# =============================================================================
# ARQUIVO DE FEEDBACK DO LED AMARELO (escrito pelo Nível 3 via UL Byte 34)
# =============================================================================
CONF_CMD_LED_FILE = os.path.join(dir_nivel4, 'conf_cmd_led_amarelo.txt')
if not os.path.exists(CONF_CMD_LED_FILE):
    with open(CONF_CMD_LED_FILE, "w") as f:
        f.write("0")

# =============================================================================
# ARQUIVO DE CONFIGURAÇÃO DA PORTA SERIAL (lido pelo Nível 3)
# =============================================================================
SERIAL_CONFIG_FILE = os.path.join(dir_nivel4, 'serial_config.txt')

# =============================================================================
# VARIÁVEIS GLOBAIS
# =============================================================================
led_amarelo_estado = 0          # Estado do comando enviado ao LED (0/1)
led_amarelo_feedback = 0        # Feedback do UL Byte 34 (0/1)


# =============================================================================
# FUNÇÕES DE LEITURA / ESCRITA DE ARQUIVOS
# =============================================================================

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


def ler_feedback_led():
    """Lê o arquivo de confirmação do LED Amarelo (escrito pelo Nível 3 - UL Byte 34)."""
    try:
        with open(CONF_CMD_LED_FILE, "r") as f:
            val = f.read().strip()
            return int(val) if val in ("0", "1") else 0
    except Exception:
        return 0


def toggle_led():
    global led_amarelo_estado
    led_amarelo_estado = 1 if led_amarelo_estado == 0 else 0
    escrever_estado_led(led_amarelo_estado)
    print(f"[N6] LED Amarelo CMD → {'ON' if led_amarelo_estado else 'OFF'}")


def atualizar_visual_led():
    """Atualiza a aparência do botão LED com base no COMANDO e no FEEDBACK do UL."""
    fb = ler_feedback_led()
    if fb == 1:
        # Feedback do nó confirma LED LIGADO → fundo amarelo
        btn_led.config(
            text="LED AMARELO: ON ✔",
            bg="#FFD700", fg="#333333",
            activebackground="#FFC200"
        )
    else:
        if led_amarelo_estado == 1:
            # Comando enviado mas ainda sem feedback → laranja (aguardando)
            btn_led.config(
                text="LED AMARELO: CMD ON",
                bg="#FFA500", fg="#FFFFFF",
                activebackground="#FF8C00"
            )
        else:
            # Desligado
            btn_led.config(
                text="LED AMARELO: OFF",
                bg="#555555", fg="#FFFFFF",
                activebackground="#444444"
            )


# =============================================================================
# FUNÇÃO DE LISTAGEM DE PORTAS SERIAIS
# =============================================================================

def listar_portas():
    """Retorna lista de portas seriais disponíveis."""
    ports = serial.tools.list_ports.comports()
    lista = []
    for p in ports:
        lista.append(f"{p.device} - {p.description}")
    if not lista:
        lista = ["Nenhuma porta encontrada"]
    return lista


def atualizar_lista_portas():
    """Atualiza o combobox de portas seriais."""
    portas = listar_portas()
    combo_portas['values'] = portas
    if portas and portas[0] != "Nenhuma porta encontrada":
        combo_portas.current(0)
    lbl_serial_status.config(text="Lista atualizada.", fg="blue")


def salvar_porta_serial():
    """Salva a porta selecionada no arquivo lido pelo Nível 3."""
    selecao = combo_portas.get()
    if not selecao or selecao == "Nenhuma porta encontrada":
        lbl_serial_status.config(text="Nenhuma porta válida selecionada.", fg="red")
        return

    # Extrai só o nome da porta (ex: "COM3" ou "/dev/ttyUSB0")
    porta = selecao.split(" - ")[0].strip()

    try:
        with open(SERIAL_CONFIG_FILE, "w") as f:
            f.write(porta + "\n")
        lbl_serial_status.config(
            text=f"Porta '{porta}' salva! Reinicie o Nível 3.",
            fg="green"
        )
        lbl_porta_ativa.config(text=f"Porta ativa: {porta}", fg="green")
        print(f"[N6] Porta serial configurada: {porta}")
    except Exception as e:
        lbl_serial_status.config(text=f"Erro ao salvar: {e}", fg="red")


def ler_porta_ativa():
    """Lê a porta atualmente configurada no arquivo."""
    try:
        with open(SERIAL_CONFIG_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "Não configurada"


# =============================================================================
# JANELA PRINCIPAL
# =============================================================================
janela_principal = Tk()
janela_principal.title("SISTEMA LORA - NÍVEL 6 UNIFICADO")
janela_principal.geometry('1350x780')
janela_principal.resizable(True, True)

# =============================================================================
# NOTEBOOK (ABAS)
# =============================================================================
notebook = ttk.Notebook(janela_principal)
notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

# Estilo das abas
style_ttk = ttk.Style()
style_ttk.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=[12, 6])

# =============================================================================
# ABA 1: APLICAÇÃO
# =============================================================================
aba_aplicacao = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_aplicacao, text="  📊 Aplicação  ")

# --- STATUS ---
reg_status_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_status_app.place(x=10, y=10, width=300, height=100)

Label(reg_status_app, font=("Arial", 14, "bold"), text="STATUS DO SISTEMA",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

status_texto_app = StringVar()
status_texto_app.set("AGUARDANDO...")
label_status_app = Label(reg_status_app, textvariable=status_texto_app,
                         font=("Arial", 16, "bold"), fg="gray", bg="#F0F0F0")
label_status_app.place(x=150, y=55, anchor="center")

# --- DADOS APLICAÇÃO ---
reg_dados_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_dados_app.place(x=10, y=120, width=300, height=420)

Label(reg_dados_app, font=("Arial", 16, "bold"), text="DADOS APLICAÇÃO",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

Label(reg_dados_app, font=("Arial", 13, "bold"), text="LUMINOSIDADE",
      fg="orange", padx=5, pady=5, bg="#F0F0F0").place(x=150, y=100, anchor="center")

str_atual_lum = StringVar()
str_atual_lum.set("--")
Label(reg_dados_app, font=("Arial", 30, "bold"), textvariable=str_atual_lum,
      padx=5, pady=2, bg="#F0F0F0").place(x=150, y=150, anchor="center")

# --- LED AMARELO ---
Label(reg_dados_app, font=("Arial", 11, "bold"), text="COMANDA LED AMARELO",
      fg="black", padx=5, pady=5, bg="#F0F0F0").place(x=150, y=235, anchor="center")

Label(reg_dados_app, font=("Arial", 9), text="(fundo amarelo = confirmado pelo nó)",
      fg="gray", bg="#F0F0F0").place(x=150, y=258, anchor="center")

led_amarelo_estado = ler_estado_led()

btn_led = Button(reg_dados_app, text="", font=("Arial", 12, "bold"),
                 width=20, height=1, cursor="hand2", relief="raised", bd=3,
                 command=toggle_led)
btn_led.place(x=30, y=270)

# Feedback label
lbl_feedback_led = Label(reg_dados_app, font=("Arial", 10), text="UL Byte[34]: --",
                         fg="gray", bg="#F0F0F0")
lbl_feedback_led.place(x=150, y=330, anchor="center")

# --- GRÁFICO APLICAÇÃO ---
reg_grafico_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken')
reg_grafico_app.place(x=320, y=10, width=700, height=720)

style.use("ggplot")

fig_app = Figure(figsize=(8.5, 7.5), facecolor='white')
canvas_app = FigureCanvasTkAgg(fig_app, master=reg_grafico_app)
canvas_app.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)


def grafico_aplicacao(f, c):
    f.clear()
    x_medidas = []
    y_lum = []

    path_tmp = os.path.join(dir_nivel4, 'dados_aplicacao.tmp')
    if os.path.exists(path_tmp):
        try:
            dados = open(path_tmp, 'r')
            for line in dados:
                line = line.strip()
                colunas = line.split(';')
                if len(colunas) >= 2:
                    if colunas[0] != '':
                        x_medidas.append(int(colunas[0]))
                        y_lum.append(int(colunas[1]))
            dados.close()
        except Exception:
            pass

    if len(y_lum) > 0:
        str_atual_lum.set(f"{y_lum[-1]}")

    axis = f.add_subplot(111)
    axis.plot(x_medidas, y_lum, label='Luminosidade', color='orange')
    axis.set_ylabel('Luminosidade (0-4095)')
    axis.set_xlabel('Medida')
    axis.set_ylim(0, 4095)
    axis.legend(loc='upper right', fontsize='medium')

    # Leitura passiva do status
    path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    if os.path.exists(path_param):
        try:
            pp = open(path_param, 'r')
            status_lido = pp.readline().strip()
            pp.close()
            if status_lido == '1':
                status_texto_app.set("EM ANDAMENTO")
                label_status_app.config(fg="green")
            else:
                status_texto_app.set("PARADO")
                label_status_app.config(fg="red")
        except Exception:
            pass

    # Atualiza LED: lê feedback do UL Byte 34
    fb = ler_feedback_led()
    lbl_feedback_led.config(
        text=f"UL Byte[34]: {fb}",
        fg="green" if fb == 1 else "gray"
    )
    atualizar_visual_led()

    f.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.95)
    c.draw()

    janela_principal.after(800, grafico_aplicacao, f, c)


grafico_aplicacao(fig_app, canvas_app)

# =============================================================================
# ABA 2: GERÊNCIA
# =============================================================================
aba_gerencia = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia, text="  📡 Gerência LoRa  ")

# --- PARAMETRIZAÇÃO ---
reg_parametrizacao = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_parametrizacao.place(x=10, y=10, width=300, height=380)

Label(reg_parametrizacao, font=("Arial", 14, "bold"), text="Configurações LoRa",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

# Qtde. de Medidas
Label(reg_parametrizacao, text="Qtde. de Medidas", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=40)
valor_intervalo = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_intervalo.place(x=170, y=40)
valor_intervalo.insert(0, "0")

# Tempo de Rádio
Label(reg_parametrizacao, text="Tempo de Rádio", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=75)
Label(reg_parametrizacao, text="Em segundos", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=95)
valor_tempo_tx_rx = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_tempo_tx_rx.place(x=170, y=75)
valor_tempo_tx_rx.insert(0, "8")

# Spreading Factor
Label(reg_parametrizacao, text="Spreading Factor", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=110)
Label(reg_parametrizacao, text="7 a 12", font=("Arial", 8), bg="#F0F0F0").place(x=30, y=130)
valor_spreadingfactor = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_spreadingfactor.place(x=170, y=110)
valor_spreadingfactor.insert(0, "12")

# Bandwidth
Label(reg_parametrizacao, text="Bandwidth", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=145)
Label(reg_parametrizacao, text="125, 250, 500 kHz", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=165)
valor_bandwidth = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_bandwidth.place(x=170, y=145)
valor_bandwidth.insert(0, "125")

# CodingRate
Label(reg_parametrizacao, text="CodingRate", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=180)
Label(reg_parametrizacao, text="5 a 8 => 4/5, 4/6, 4/7, 4/8", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=200)
valor_codingrate = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_codingrate.place(x=170, y=180)
valor_codingrate.insert(0, "8")

# Potência
Label(reg_parametrizacao, text="Potência de Rádio", font=("Arial", 12),
      bg="#F0F0F0").place(x=20, y=215)
Label(reg_parametrizacao, text="2 a 20dBm", font=("Arial", 8),
      bg="#F0F0F0").place(x=30, y=235)
valor_potencia_radio = Entry(reg_parametrizacao, width=10, font=("Arial", 12))
valor_potencia_radio.place(x=170, y=215)
valor_potencia_radio.insert(0, "20")

# Status
status_texto_ger = StringVar()
status_texto_ger.set("AGUARDANDO...")
label_status_ger = Label(reg_parametrizacao, textvariable=status_texto_ger,
                         font=("Arial", 10, "bold"), fg="gray", bg="#F0F0F0")
label_status_ger.place(x=25, y=300)

# Status LSS
lss_status_texto = StringVar()
lss_status_texto.set("TESTE LSS PARADO")
Label(reg_parametrizacao, font=("Arial", 12, "bold"), text="STATUS LSS :",
      fg="blue", padx=5, pady=5, bg="#F0F0F0").place(x=20, y=325)
label_lss_status = Label(reg_parametrizacao, textvariable=lss_status_texto,
                         font=("Arial", 12, "bold"), fg="green", padx=5, pady=5, bg="#F0F0F0")
label_lss_status.place(x=20, y=350)


# --- FUNÇÕES DE CAPTURA E GRAVAÇÃO ---
def captura_num_medidas():
    v = valor_intervalo.get()
    n = int(v) if v else 0
    return int(n) if n > 0 else 10


def captura_num_spreadingfactor():
    v = valor_spreadingfactor.get()
    n = int(v) if v else 12
    return max(7, min(12, int(n)))


def captura_num_bandwidth():
    v = valor_bandwidth.get()
    n = int(v) if v else 125
    if n < 200:
        return 125
    elif n < 350:
        return 250
    else:
        return 500


def captura_num_codingrate():
    v = valor_codingrate.get()
    n = int(v) if v else 8
    return max(5, min(8, int(n)))


def captura_num_potencia_radio():
    v = valor_potencia_radio.get()
    n = int(v) if v else 20
    return max(2, min(20, int(n)))


def captura_num_tempo_tx_rx():
    v = valor_tempo_tx_rx.get()
    n = int(v) if v else 8
    return max(1, min(10, int(n)))


def grava_comandos(condicao_start):
    arquivo_txt = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    s = open(arquivo_txt, 'w')
    s.write(str(condicao_start) + "\n")
    s.write(str(captura_num_medidas()) + "\n")
    s.write(str(captura_num_spreadingfactor()) + "\n")
    s.write(str(captura_num_bandwidth()) + "\n")
    s.write(str(captura_num_codingrate()) + "\n")
    s.write(str(captura_num_potencia_radio()) + "\n")
    s.write(str(captura_num_tempo_tx_rx()) + "\n")
    s.close()


def iniciar_teste():
    grava_comandos(1)
    status_texto_ger.set("TESTE EM ANDAMENTO...")
    label_status_ger.config(fg="green")


btn_iniciar = Button(reg_parametrizacao, text="INICIAR TESTE",
                     font=("Arial", 13, "bold"), width=20, command=iniciar_teste)
btn_iniciar.place(x=25, y=260)

# --- DESEMPENHO ---
reg_desempenho = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_desempenho.place(x=10, y=400, width=300, height=340)

Label(reg_desempenho, font=("Arial", 13, "bold"), text="Intensidade do Sinal",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

Label(reg_desempenho, font=("Arial", 12, "bold"), text="RSSI DOWNLINK",
      fg="blue", padx=5, pady=5, bg="#F0F0F0").place(x=10, y=45, anchor="w")
Label(reg_desempenho, font=("Arial", 12, "bold"), text="RSSI UPLINK",
      fg="green", padx=5, pady=5, bg="#F0F0F0").place(x=10, y=150, anchor="w")

# StringVars Gerência
str_atual_dl = StringVar(); str_atual_dl.set("Atual: -- dBm")
str_max_dl = StringVar();   str_max_dl.set("Máx: 0 dBm")
str_min_dl = StringVar();   str_min_dl.set("Mín: 0 dBm")
str_atual_ul = StringVar(); str_atual_ul.set("Atual: -- dBm")
str_max_ul = StringVar();   str_max_ul.set("Máx: 0 dBm")
str_min_ul = StringVar();   str_min_ul.set("Mín: 0 dBm")
str_atual_psr = StringVar(); str_atual_psr.set("Atual: -- %")
srt_atual_taxa_canal = StringVar();      srt_atual_taxa_canal.set("-- bps")
srt_atual_taxa_real_canal = StringVar(); srt_atual_taxa_real_canal.set("-- bps")
srt_snr_DL = StringVar(); srt_snr_DL.set("-- dB")
srt_snr_UL = StringVar(); srt_snr_UL.set("-- dB")
srt_medida_atual_DL = StringVar(); srt_medida_atual_DL.set("-- Pacotes")
srt_counter_UL = StringVar();      srt_counter_UL.set("-- Pacotes")
srt_perda_total_UL = StringVar();  srt_perda_total_UL.set("-- Pacotes")
str_atual_per = StringVar();       str_atual_per.set("Atual: -- %")

Label(reg_desempenho, font=("Arial", 11, "bold"), textvariable=str_atual_dl,
      padx=5, pady=2, bg="#F0F0F0").place(x=10, y=60)
Label(reg_desempenho, font=("Arial", 11), textvariable=str_max_dl,
      padx=5, pady=2, bg="#F0F0F0").place(x=10, y=85)
Label(reg_desempenho, font=("Arial", 11), textvariable=str_min_dl,
      padx=5, pady=2, bg="#F0F0F0").place(x=10, y=110)
Label(reg_desempenho, font=("Arial", 11, "bold"), textvariable=str_atual_ul,
      padx=5, pady=2, bg="#F0F0F0").place(x=10, y=165)
Label(reg_desempenho, font=("Arial", 11), textvariable=str_max_ul,
      padx=5, pady=2, bg="#F0F0F0").place(x=10, y=190)
Label(reg_desempenho, font=("Arial", 11), textvariable=str_min_ul,
      padx=5, pady=2, bg="#F0F0F0").place(x=10, y=215)

# Painel direito da Gerência (métricas de rede)
frm_metricas = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_metricas.place(x=1070, y=10, width=270, height=730)

def _lbl_m(texto, var, cor="blue", y_pos=0):
    Label(frm_metricas, font=("Arial", 12, "bold"), text=texto,
          fg=cor, bg="#F0F0F0").place(x=10, y=y_pos)
    Label(frm_metricas, font=("Arial", 12, "bold"), textvariable=var,
          fg="black", bg="#F0F0F0").place(x=10, y=y_pos + 22)

_lbl_m("PSR (Geral)",         str_atual_psr,          "blue",  10)
_lbl_m("Taxa Teórica",        srt_atual_taxa_canal,   "blue",  80)
_lbl_m("Taxa Efetiva",        srt_atual_taxa_real_canal, "blue", 150)
_lbl_m("SNR Downlink",        srt_snr_DL,             "blue",  220)
_lbl_m("SNR Uplink",          srt_snr_UL,             "green", 290)
_lbl_m("Downlinks",           srt_medida_atual_DL,    "blue",  360)
_lbl_m("Uplinks",             srt_counter_UL,         "green", 430)
_lbl_m("Pacotes Perdidos",    srt_perda_total_UL,     "red",   500)
_lbl_m("PER (Geral)",         str_atual_per,          "red",   570)

# --- GRÁFICO GERÊNCIA ---
reg_grafico_ger = Frame(master=aba_gerencia, borderwidth=1, relief='sunken')
reg_grafico_ger.place(x=320, y=10, width=740, height=730)

fig_ger = Figure(figsize=(8.5, 7.5), facecolor='white')
canvas_ger = FigureCanvasTkAgg(fig_ger, master=reg_grafico_ger)
canvas_ger.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)


def grafico_rssi(f, c):
    f.clear()
    x = []; xUP = []; y = []; z = []; psr_dl = []
    ultimo_max_dl = "0"; ultimo_min_dl = "0"
    ultimo_max_ul = "0"; ultimo_min_ul = "0"
    taxa_canal_teorica = "0"; taxa_canal_calculada = "0"
    snr_DL = "0"; snr_UL = "0"
    medida_atual_DL = "0"; counter_DL = "0"
    counter_UL = "0"; perda_total_UL = "0"
    atual_per = "0"; lss_status = "0"

    path_tmp = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
    if os.path.exists(path_tmp):
        try:
            dados = open(path_tmp, 'r')
            for line in dados:
                line = line.strip()
                Y = line.split(';')
                y.append(Y)
            dados.close()
        except Exception:
            pass

    for i in range(len(y)):
        if len(y[i]) >= 15:
            if y[i][0] != '':
                z.append(int(y[i][0]))
                x.append(float(y[i][1]))
                psr_dl.append(float(y[i][2]))
                xUP.append(float(y[i][4]))
                medida_atual_DL  = y[i][0]
                ultimo_max_dl    = y[i][5]
                ultimo_min_dl    = y[i][6]
                ultimo_max_ul    = y[i][7]
                ultimo_min_ul    = y[i][8]
                taxa_canal_teorica    = y[i][13]
                taxa_canal_calculada  = y[i][14]
                snr_DL      = y[i][15]
                snr_UL      = y[i][16]
                counter_DL  = y[i][17]
                counter_UL  = y[i][18]
                perda_total_UL = y[i][19]
                lss_status  = y[i][20]

    if x:     str_atual_dl.set(f"Atual: {x[-1]} dBm")
    if xUP:   str_atual_ul.set(f"Atual: {xUP[-1]} dBm")
    if psr_dl: str_atual_psr.set(f"Atual: {psr_dl[-1]} %")

    axis = f.add_subplot(311)
    axis.plot(z, x, label='RSSI DOWNLINK', color='blue')
    axis.set_ylabel('RSSI DL (dBm)')
    axis.legend(loc='upper right', fontsize='x-small')

    axis1 = f.add_subplot(312)
    axis1.plot(z, xUP, label='RSSI UPLINK', color='red')
    axis1.set_ylabel('RSSI UL (dBm)')
    axis1.legend(loc='upper right', fontsize='x-small')

    axis2 = f.add_subplot(313)
    axis2.plot(z, psr_dl, label='PSR (Geral)', color='green')
    axis2.set_ylabel('PSR (%)')
    axis2.set_xlabel('Medida')
    axis2.set_ylim(-5, 105)
    axis2.legend(loc='upper right', fontsize='x-small')

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

    per_total = (100 - psr_dl[-1]) if psr_dl else 0
    str_atual_per.set(f"Atual: {round(per_total, 2)} %")

    if lss_status == "1":
        lss_status_texto.set("LSS EM ANDAMENTO"); label_lss_status.config(fg="green")
    elif lss_status == "2":
        lss_status_texto.set("LSS TESTE ENLACE"); label_lss_status.config(fg="green")
    elif lss_status == "3":
        lss_status_texto.set("LSS MUDA RÁDIO"); label_lss_status.config(fg="blue")
    elif lss_status == "4":
        lss_status_texto.set("LSS ENLACE PERDIDO"); label_lss_status.config(fg="red")

    path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    if os.path.exists(path_param):
        try:
            pp = open(path_param, 'r')
            status_lido = pp.readline().strip()
            pp.close()
            if status_lido == '0' and status_texto_ger.get() == "TESTE EM ANDAMENTO...":
                status_texto_ger.set("TESTE LSS FINALIZADO")
                label_status_ger.config(fg="green")
            if lss_status == "0":
                lss_status_texto.set("LSS PARADO")
                label_lss_status.config(fg="green")
        except Exception:
            pass

    f.subplots_adjust(left=0.12, bottom=0.20, right=0.95, top=0.95, hspace=0.6)
    c.draw()
    janela_principal.after(800, grafico_rssi, f, c)


grafico_rssi(fig_ger, canvas_ger)



# =============================================================================
# ABA 3: CONEXÃO SERIAL
# =============================================================================
aba_serial = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_serial, text="  🔌 Conexão Serial  ")

# Título
Label(aba_serial, text="CONFIGURAÇÃO DA PORTA SERIAL DO GATEWAY LORA",
      font=("Arial", 16, "bold"), fg="#1a1a2e", bg="#F0F0F0").place(x=50, y=30)

Label(aba_serial, text="Selecione a porta COM do Gateway LoRa. A porta será salva em arquivo e lida automaticamente pelo Nível 3.",
      font=("Arial", 11), fg="#555555", bg="#F0F0F0", wraplength=700, justify="left").place(x=50, y=70)

# Separador visual
Frame(aba_serial, bg="#CCCCCC", height=2).place(x=50, y=105, width=700)

# Lista de portas
Label(aba_serial, text="Portas seriais disponíveis:", font=("Arial", 13, "bold"),
      bg="#F0F0F0").place(x=50, y=125)

combo_portas = ttk.Combobox(aba_serial, font=("Arial", 12), width=45, state="readonly")
combo_portas.place(x=50, y=155)

# Botão Atualizar
btn_atualizar = Button(aba_serial, text="🔄 Atualizar Lista",
                       font=("Arial", 11, "bold"), bg="#3a86ff", fg="white",
                       activebackground="#265fd3", cursor="hand2", relief="flat",
                       command=atualizar_lista_portas, padx=10, pady=4)
btn_atualizar.place(x=50, y=200)

# Botão Salvar
btn_salvar_porta = Button(aba_serial, text="💾 Salvar e Aplicar Porta",
                          font=("Arial", 13, "bold"), bg="#2dc653", fg="white",
                          activebackground="#1fa83e", cursor="hand2", relief="flat",
                          command=salvar_porta_serial, padx=14, pady=6)
btn_salvar_porta.place(x=50, y=250)

# Status
lbl_serial_status = Label(aba_serial, text="Aguardando seleção...",
                           font=("Arial", 12), fg="gray", bg="#F0F0F0")
lbl_serial_status.place(x=50, y=310)

# Separador
Frame(aba_serial, bg="#CCCCCC", height=2).place(x=50, y=345, width=700)

# Porta atualmente ativa
Label(aba_serial, text="Porta configurada atualmente:",
      font=("Arial", 12, "bold"), bg="#F0F0F0").place(x=50, y=365)
porta_atual = ler_porta_ativa()
lbl_porta_ativa = Label(aba_serial, text=f"Porta ativa: {porta_atual}",
                        font=("Arial", 14, "bold"),
                        fg="green" if porta_atual != "Não configurada" else "gray",
                        bg="#F0F0F0")
lbl_porta_ativa.place(x=50, y=395)

# Instruções
Frame(aba_serial, bg="#CCCCCC", height=2).place(x=50, y=440, width=700)

Label(aba_serial, text="Como usar:", font=("Arial", 12, "bold"), bg="#F0F0F0").place(x=50, y=460)

instrucoes = (
    "1. Conecte o Gateway LoRa (ESP32) ao computador via USB.\n"
    "2. Clique em '🔄 Atualizar Lista' para ver as portas disponíveis.\n"
    "3. Selecione a porta correta no menu suspenso.\n"
    "4. Clique em '💾 Salvar e Aplicar Porta'.\n"
    "5. Inicie (ou reinicie) o script Nível 3 — ele lerá a porta automaticamente.\n\n"
    "Obs: O arquivo salvo é: NIVEL4/serial_config.txt"
)
Label(aba_serial, text=instrucoes, font=("Arial", 11), fg="#333333",
      bg="#F0F0F0", justify="left").place(x=50, y=490)

# Popula a lista de portas na inicialização
atualizar_lista_portas()

#

# aqui estava gráfico

#

# =============================================================================
# CALLBACK DE FECHAR JANELA
# =============================================================================
def callback():
    if tkMessageBox.askokcancel("Sair", "Tem certeza que deseja sair?"):
        grava_comandos(0)
        janela_principal.destroy()


janela_principal.protocol("WM_DELETE_WINDOW", callback)
janela_principal.mainloop()
janela_principal.update_idletasks()

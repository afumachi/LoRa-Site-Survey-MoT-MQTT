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


"""

ent_ds_d0 = 1.0
ent_ds_d1 = 10.0
ent_ds_d2 = 30.0
ent_ds_d3 = 5.0
ent_ld_n = 3.0
ent_ld_d0 = 1.0
ent_ld_sigma = 0.0
ent_ds_n1 = 2.0
ent_ds_n2 = 3.5
ent_ds_n3 = 3.5
ent_ds_sigma = 0.0


"""

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



# 

# 


# =============================================================================
# ABA 3: MODELO COST 231 MULTI-WALL – ANÁLISE DE PATH LOSS ONLINE
# =============================================================================
# Modelo COST 231 Multi-Wall (Låftman, 1994 / ETSI TR 101 112):
#
#   PL(d) = PL_fs(d) + L_c + Σ(k_i · L_wi) + n_f^((n_f+2)/(n_f+1) - b) · L_f
#
# Onde:
#   PL_fs(d)  = 20·log10(d) + 20·log10(f_MHz) + 20·log10(4π/c)   [dB]
#   L_c       = constante de perda soft (tipicamente 37 dB @ 915 MHz indoor)
#   k_i       = número de paredes do tipo i atravessadas
#   L_wi      = atenuação da parede tipo i [dB]
#   n_f       = número de pisos atravessados
#   L_f       = atenuação por piso [dB]
#   b         = empiric offset (padrão = 0.46)
#
# Margem de enlace:  ML = Pt + Gt + Gr – PL(d) – Sensibilidade_rx
# Distância máxima:  d_max = 10^((Pt + Gt + Gr – PL_limite – Σ WAF – Σ FAF – L_c) / 20)
# =============================================================================

aba_propagacao = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_propagacao, text="  📶 Propagação Multi-Wall ") #  Propagação COST231

# ---------------------------------------------------------------------------
# CONSTANTES FÍSICAS
# ---------------------------------------------------------------------------
FREQ_MHZ_C231    = 915.0
VELOCIDADE_LUZ   = 3e8
LC_INDOOR        = 37.0    # Constante de perda indoor COST 231 @ 900 MHz [dB]
B_EMPIRICO       = 0.46    # Coeficiente empírico de piso
PT_DBM_DEFAULT   = 20.0    # Potência TX padrão [dBm]
SENS_RX_DBM      = -137.0  # Sensibilidade típica LoRa SF12/BW125 [dBm]

# ---------------------------------------------------------------------------
# HISTÓRICO DE AMOSTRAS PARA O GRÁFICO
# ---------------------------------------------------------------------------
hist_medida    = []
hist_pl_dl     = []
hist_pl_ul     = []
hist_pl_modelo = []
hist_pl_min    = []   # PL mínima (melhor caso – sem paredes/pisos)
hist_margem_dl = []
hist_margem_ul = []

ultima_medida_c231 = -1

# ---------------------------------------------------------------------------
# FRAME ESQUERDO: PARÂMETROS DO OPERADOR
# ---------------------------------------------------------------------------
frm_params = Frame(aba_propagacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_params.place(x=8, y=8, width=318, height=730)

Label(frm_params, text="Parâmetros COST 231 Multi-Wall",
      font=("Arial", 13, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=10)
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=32, width=295)

# ── Distância ──────────────────────────────────────────────────────────────
Label(frm_params, text="Distância d [m]", font=("Arial", 11, "bold"),
      bg="#F0F0F0").place(x=10, y=45)
Label(frm_params, text="Nó Sensor ↔ Gateway (medida real)",
      font=("Arial", 9), fg="#666666", bg="#F0F0F0").place(x=10, y=63)
ent_distancia = Entry(frm_params, width=10, font=("Arial", 12))
ent_distancia.place(x=220, y=45)
ent_distancia.insert(0, "6.0")

# ── Potência TX ─────────────────────────────────────────────────────────────
Label(frm_params, text="Potência TX [dBm]", font=("Arial", 11, "bold"),
      bg="#F0F0F0").place(x=10, y=85)
Label(frm_params, text="Nível 3 usa raw['pw'] — confira aqui",
      font=("Arial", 9), fg="#666666", bg="#F0F0F0").place(x=10, y=103)
ent_pt = Entry(frm_params, width=10, font=("Arial", 12))
ent_pt.place(x=220, y=85)
ent_pt.insert(0, "20")

# ── Separador Paredes ───────────────────────────────────────────────────────
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=122, width=295)
Label(frm_params, text="Paredes atravessadas no enlace",
      font=("Arial", 11, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=130)

# Cabeçalho tabela paredes
Label(frm_params, text="Qtde", font=("Arial", 9, "bold"), bg="#F0F0F0").place(x=220, y=150)
Label(frm_params, text="Aten. [dB]", font=("Arial", 9, "bold"), bg="#F0F0F0").place(x=255, y=150)

# Parede 1
Label(frm_params, text="Parede tipo 1", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=168)
Label(frm_params, text="(ex: alvenaria simples)",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=183)
ent_k1 = Entry(frm_params, width=4, font=("Arial", 11))
ent_k1.place(x=220, y=168); ent_k1.insert(0, "1")
ent_lw1 = Entry(frm_params, width=6, font=("Arial", 11))
ent_lw1.place(x=258, y=168); ent_lw1.insert(0, "9.0")

# Parede 2
Label(frm_params, text="Parede tipo 2", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=200)
Label(frm_params, text="(ex: drywall / tabica)",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=215)
ent_k2 = Entry(frm_params, width=4, font=("Arial", 11))
ent_k2.place(x=220, y=200); ent_k2.insert(0, "1")
ent_lw2 = Entry(frm_params, width=6, font=("Arial", 11))
ent_lw2.place(x=258, y=200); ent_lw2.insert(0, "4.0")

# Parede 3
Label(frm_params, text="Parede tipo 3", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=232)
Label(frm_params, text="(ex: vidro simples)",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=247)
ent_k3 = Entry(frm_params, width=4, font=("Arial", 11))
ent_k3.place(x=220, y=232); ent_k3.insert(0, "0")
ent_lw3 = Entry(frm_params, width=6, font=("Arial", 11))
ent_lw3.place(x=258, y=232); ent_lw3.insert(0, "2.0")

# Parede 4
Label(frm_params, text="Parede tipo 4", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=264)
Label(frm_params, text="(ex: concreto armado)",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=279)
ent_k4 = Entry(frm_params, width=4, font=("Arial", 11))
ent_k4.place(x=220, y=264); ent_k4.insert(0, "0")
ent_lw4 = Entry(frm_params, width=6, font=("Arial", 11))
ent_lw4.place(x=258, y=264); ent_lw4.insert(0, "15.0")

# ── Separador Pisos ─────────────────────────────────────────────────────────
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=298, width=295)
Label(frm_params, text="Pisos / andares atravessados",
      font=("Arial", 11, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=306)

Label(frm_params, text="Nº de pisos (n_f)", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=328)
ent_nf = Entry(frm_params, width=6, font=("Arial", 11))
ent_nf.place(x=220, y=328); ent_nf.insert(0, "0")

Label(frm_params, text="Aten. por piso (L_f) [dB]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=356)
Label(frm_params, text="Laje concreto ≈ 15 dB | madeira ≈ 10 dB",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=371)
ent_lf = Entry(frm_params, width=6, font=("Arial", 11))
ent_lf.place(x=220, y=356); ent_lf.insert(0, "0.0")

# ── Constante indoor L_c ────────────────────────────────────────────────────
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=390, width=295)
Label(frm_params, text="Constante indoor L_c [dB]",
      font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=398)
Label(frm_params, text="COST231 padrão: 37 dB @ 900 MHz",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=416)
ent_lc = Entry(frm_params, width=6, font=("Arial", 11))
ent_lc.place(x=220, y=398); ent_lc.insert(0, "37.0")

# ── Sensibilidade RX ────────────────────────────────────────────────────────
Label(frm_params, text="Sensibilidade RX [dBm]",
      font=("Arial", 10), bg="#F0F0F0").place(x=10, y=438)
Label(frm_params, text="LoRa SF12/BW125 ≈ −137 dBm",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=454)
ent_sens = Entry(frm_params, width=8, font=("Arial", 11))
ent_sens.place(x=220, y=438); ent_sens.insert(0, "-137.0")

# ── BOTÃO APLICAR ───────────────────────────────────────────────────────────
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=476, width=295)

def aplicar_parametros_c231():
    """Reseta histórico e recalcula gráfico com novos parâmetros."""
    global hist_medida, hist_pl_dl, hist_pl_ul, hist_pl_modelo
    global hist_pl_min, hist_margem_dl, hist_margem_ul, ultima_medida_c231
    hist_medida.clear(); hist_pl_dl.clear(); hist_pl_ul.clear()
    hist_pl_modelo.clear(); hist_pl_min.clear()
    hist_margem_dl.clear(); hist_margem_ul.clear()
    ultima_medida_c231 = -1
    lbl_c231_status.config(text="Parâmetros aplicados – aguardando dados...", fg="blue")
    print("[N6/C231] Parâmetros atualizados pelo operador.")

btn_aplicar = Button(frm_params, text="▶  APLICAR PARÂMETROS",
                     font=("Arial", 12, "bold"), bg="#185FA5", fg="white",
                     activebackground="#0C447C", cursor="hand2", relief="flat",
                     command=aplicar_parametros_c231, padx=8, pady=5)
btn_aplicar.place(x=10, y=485, width=294)

# ── MÉTRICAS CALCULADAS (painel resultado) ──────────────────────────────────
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=520, width=295)
Label(frm_params, text="Resultados online",
      font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=528)

str_c231_pl_modelo = StringVar(); str_c231_pl_modelo.set("PL modelo : -- dB")
str_c231_pl_dl     = StringVar(); str_c231_pl_dl.set("PL medido DL: -- dB")
str_c231_pl_ul     = StringVar(); str_c231_pl_ul.set("PL medido UL: -- dB")
str_c231_margem    = StringVar(); str_c231_margem.set("Margem pior: -- dB")
str_c231_dmax      = StringVar(); str_c231_dmax.set("d_max modelo: -- m")
str_c231_waf_tot   = StringVar(); str_c231_waf_tot.set("WAF+FAF total: -- dB")
str_c231_qualidade = StringVar(); str_c231_qualidade.set("Qualidade: --")

def _lbl_res(var, y, cor="black"):
    Label(frm_params, textvariable=var, font=("Arial", 10, "bold"),
          fg=cor, bg="#F0F0F0").place(x=14, y=y)

_lbl_res(str_c231_pl_modelo, 548, "#185FA5")
_lbl_res(str_c231_pl_dl,     566, "#3B6D11")
_lbl_res(str_c231_pl_ul,     584, "#993C1D")
_lbl_res(str_c231_margem,    602, "#854F0B")
_lbl_res(str_c231_dmax,      620, "#533")
_lbl_res(str_c231_waf_tot,   638, "#555")

lbl_c231_qualidade = Label(frm_params, textvariable=str_c231_qualidade,
                            font=("Arial", 13, "bold"), fg="gray", bg="#F0F0F0")
lbl_c231_qualidade.place(x=14, y=660)

lbl_c231_status = Label(frm_params, text="Aguardando dados do Nível 3...",
                         font=("Arial", 9), fg="gray", bg="#F0F0F0", wraplength=290,
                         justify="left")
lbl_c231_status.place(x=10, y=695)

# ---------------------------------------------------------------------------
# FRAME DIREITO: GRÁFICO
# ---------------------------------------------------------------------------
frm_graf_c231 = Frame(aba_propagacao, borderwidth=1, relief='sunken')
frm_graf_c231.place(x=334, y=8, width=1000, height=730)

fig_c231 = Figure(facecolor='white')
canvas_c231 = FigureCanvasTkAgg(fig_c231, master=frm_graf_c231)
canvas_c231.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

# ---------------------------------------------------------------------------
# FUNÇÕES DO MODELO COST 231 MULTI-WALL
# ---------------------------------------------------------------------------

def c231_capturar_params() -> dict:
    """Lê e valida todos os campos do operador. Retorna dict com valores."""
    def fval(entry, default):
        try:    return float(entry.get())
        except: return default
    def ival(entry, default):
        try:    return max(0, int(entry.get()))
        except: return default

    return {
        'd_m':   max(0.1,  fval(ent_distancia, 6.0)),
        'pt':    fval(ent_pt, 20.0),
        'k1':    ival(ent_k1, 1),   'lw1': fval(ent_lw1, 9.0),
        'k2':    ival(ent_k2, 1),   'lw2': fval(ent_lw2, 4.0),
        'k3':    ival(ent_k3, 0),   'lw3': fval(ent_lw3, 2.0),
        'k4':    ival(ent_k4, 0),   'lw4': fval(ent_lw4, 15.0),
        'nf':    ival(ent_nf, 0),
        'lf':    fval(ent_lf, 0.0),
        'lc':    fval(ent_lc, 37.0),
        'sens':  fval(ent_sens, -137.0),
    }


def c231_pl_espaco_livre(d_m: float) -> float:
    """Perda no espaço livre Friis [dB] para FREQ_MHZ_C231."""
    if d_m <= 0:
        return 0.0
    k = 20 * math.log10(4 * math.pi * 1e6 / VELOCIDADE_LUZ)
    return 20 * math.log10(d_m) + 20 * math.log10(FREQ_MHZ_C231) + k


def c231_waf_total(p: dict) -> float:
    """Σ kᵢ · Lwᵢ  para as 4 categorias de parede."""
    return (p['k1']*p['lw1'] + p['k2']*p['lw2'] +
            p['k3']*p['lw3'] + p['k4']*p['lw4'])


def c231_faf(nf: int, lf: float) -> float:
    """
    Atenuação por piso (Floor Attenuation Factor) – COST 231 Multi-Wall.
    FAF = nf^((nf+2)/(nf+1) − b) · Lf      com b = 0.46
    Para nf=0: FAF = 0.
    """
    if nf <= 0 or lf <= 0:
        return 0.0
    expoente = (nf + 2) / (nf + 1) - B_EMPIRICO
    return (nf ** expoente) * lf


def c231_pl_total(d_m: float, p: dict) -> float:
    """
    Path Loss total COST 231 Multi-Wall [dB].
    PL = PL_fs(d) + L_c + WAF_total + FAF
    """
    return (c231_pl_espaco_livre(d_m)
            + p['lc']
            + c231_waf_total(p)
            + c231_faf(p['nf'], p['lf']))


def c231_pl_minimo(d_m: float, p: dict) -> float:
    """PL mínimo (só espaço livre + L_c – sem paredes nem pisos)."""
    return c231_pl_espaco_livre(d_m) + p['lc']


def c231_distancia_maxima(p: dict) -> float:
    """
    Distância máxima teórica onde PL_total = Link_budget.
    Link_budget = Pt + 0 (ganhos de antena isótropa) – Sensibilidade_rx
    d_max = 10^((LB – L_c – WAF – FAF) / 20)
    """
    try:
        lb = p['pt'] - p['sens']                   # Link budget [dB]
        pl_fixo = p['lc'] + c231_waf_total(p) + c231_faf(p['nf'], p['lf'])
        expoente = (lb - pl_fixo - 20 * math.log10(FREQ_MHZ_C231)
                    - 20 * math.log10(4 * math.pi * 1e6 / VELOCIDADE_LUZ)) / 20.0
        d_max = 10 ** expoente
        return max(0.0, d_max)
    except Exception:
        return 0.0


def c231_qualidade(margem_db: float) -> tuple:
    """(texto, cor_tk) baseado na margem de enlace."""
    if margem_db >= 30:  return "EXCELENTE  ▲▲▲", "green"
    if margem_db >= 20:  return "BOM  ▲▲",         "#1a7a1a"
    if margem_db >= 10:  return "REGULAR  ▲",       "orange"
    if margem_db >= 0:   return "RUIM  ▽",          "red"
    return               "CRÍTICO  ▽▽▽",            "darkred"


def c231_ler_gerencia() -> dict:
    """Lê última linha de dados_gerencia.tmp – mesmo parser do Nível 5."""
    r = {'medida': 0, 'rssi_dl': None, 'rssi_ul': None, 'pw': PT_DBM_DEFAULT,
         'valido': False}
    path = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
    if not os.path.exists(path):
        return r
    try:
        ultima = None
        with open(path, 'r') as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    ultima = ln
        if ultima is None:
            return r
        cols = ultima.split(';')
        if len(cols) < 13:
            return r
        r['medida']  = int(cols[0])   if cols[0]  else 0
        r['rssi_dl'] = float(cols[1]) if cols[1]  else None
        r['rssi_ul'] = float(cols[4]) if cols[4]  else None
        r['pw']      = float(cols[12]) if cols[12] else PT_DBM_DEFAULT
        r['valido']  = (r['rssi_dl'] is not None and r['rssi_ul'] is not None)
    except Exception as e:
        print(f"[N6/C231] Erro leitura gerencia: {e}")
    return r


# ---------------------------------------------------------------------------
# LOOP DE ATUALIZAÇÃO DO GRÁFICO COST 231
# ---------------------------------------------------------------------------

def atualizar_grafico_c231(fig, canvas):
    global hist_medida, hist_pl_dl, hist_pl_ul, hist_pl_modelo
    global hist_pl_min, hist_margem_dl, hist_margem_ul, ultima_medida_c231

    raw = c231_ler_gerencia()
    p   = c231_capturar_params()

    if raw['valido'] and raw['medida'] != ultima_medida_c231:
        ultima_medida_c231 = raw['medida']
        Pt = raw['pw']

        # Path Loss medido = Pt – RSSI
        pl_dl_med = Pt - raw['rssi_dl']
        pl_ul_med = Pt - raw['rssi_ul']

        # Path Loss modelo para distância informada pelo operador
        pl_mod = c231_pl_total(p['d_m'], p)
        pl_min = c231_pl_minimo(p['d_m'], p)

        # Margem = Link_budget – PL_medido
        lb = Pt - p['sens']
        mg_dl = lb - pl_dl_med
        mg_ul = lb - pl_ul_med

        hist_medida.append(raw['medida'])
        hist_pl_dl.append(pl_dl_med)
        hist_pl_ul.append(pl_ul_med)
        hist_pl_modelo.append(pl_mod)
        hist_pl_min.append(pl_min)
        hist_margem_dl.append(mg_dl)
        hist_margem_ul.append(mg_ul)

        # Mantém janela deslizante de 200 amostras
        JANELA = 200
        if len(hist_medida) > JANELA:
            for lst in [hist_medida, hist_pl_dl, hist_pl_ul, hist_pl_modelo,
                        hist_pl_min, hist_margem_dl, hist_margem_ul]:
                lst.pop(0)

        # Atualiza painel de resultados
        waf_tot = c231_waf_total(p)
        faf_val = c231_faf(p['nf'], p['lf'])
        dmax    = c231_distancia_maxima(p)
        mg_pior = min(mg_dl, mg_ul)
        qual_txt, qual_cor = c231_qualidade(mg_pior)

        str_c231_pl_modelo.set(f"PL modelo : {pl_mod:.1f} dB")
        str_c231_pl_dl.set(    f"PL medido DL: {pl_dl_med:.1f} dB")
        str_c231_pl_ul.set(    f"PL medido UL: {pl_ul_med:.1f} dB")
        str_c231_margem.set(   f"Margem pior: {mg_pior:.1f} dB")
        str_c231_dmax.set(     f"d_max modelo: {dmax:.1f} m")
        str_c231_waf_tot.set(  f"WAF={waf_tot:.1f} dB  FAF={faf_val:.1f} dB  L_c={p['lc']:.1f} dB")
        str_c231_qualidade.set(qual_txt)
        lbl_c231_qualidade.config(fg=qual_cor)
        lbl_c231_status.config(
            text=f"Med.{raw['medida']} | RSSI_DL={raw['rssi_dl']:.1f} | RSSI_UL={raw['rssi_ul']:.1f} dBm",
            fg="green"
        )

    # ── PLOTAGEM ─────────────────────────────────────────────────────────────
    fig.clear()
    fig.patch.set_facecolor('white')

    if len(hist_medida) < 2:
        ax = fig.add_subplot(111)
        ax.set_facecolor('#F8F8F8')
        ax.text(0.5, 0.5, 'Aguardando dados do Nível 3...',
                ha='center', va='center', fontsize=13, color='#888888',
                transform=ax.transAxes)
        ax.set_axis_off()
        canvas.draw()
        janela_principal.after(REFRESH_MS, atualizar_grafico_c231, fig, canvas)
        return

    xs = hist_medida

    # ── Subplot 1: Path Loss total [dB] ──────────────────────────────────────
    ax1 = fig.add_subplot(311)
    ax1.set_facecolor('#F8F8F8')
    ax1.plot(xs, hist_pl_dl,     color='#1565C0', lw=1.6,  label='PL medido DL')
    ax1.plot(xs, hist_pl_ul,     color='#B71C1C', lw=1.6,  label='PL medido UL')
    ax1.plot(xs, hist_pl_modelo, color='#2E7D32', lw=2.0,  label='PL COST231 (modelo)',
             linestyle='--')
    ax1.plot(xs, hist_pl_min,    color='#888888', lw=1.0,  label='PL mín (espaço livre+Lc)',
             linestyle=':')
    # Faixa de incerteza do modelo ±3 dB
    mod_arr = hist_pl_modelo
    ax1.fill_between(xs,
                     [v - 3 for v in mod_arr],
                     [v + 3 for v in mod_arr],
                     color='#2E7D32', alpha=0.10, label='Incerteza ±3 dB')
    ax1.set_ylabel('Path Loss [dB]', fontsize=9)
    ax1.set_title('Path Loss total – COST 231 Multi-Wall @ 915 MHz', fontsize=10, fontweight='bold')
    ax1.legend(loc='upper right', fontsize='x-small', ncol=2)
    ax1.grid(True, linestyle=':', alpha=0.5)

    # Anotação com valor atual do modelo
    if hist_pl_modelo:
        ax1.annotate(f"Modelo: {hist_pl_modelo[-1]:.1f} dB",
                     xy=(xs[-1], hist_pl_modelo[-1]),
                     xytext=(-60, 8), textcoords='offset points',
                     fontsize=8, color='#2E7D32',
                     arrowprops=dict(arrowstyle='->', color='#2E7D32', lw=0.8))

    # ── Subplot 2: Margem de enlace [dB] ─────────────────────────────────────
    ax2 = fig.add_subplot(312)
    ax2.set_facecolor('#F8F8F8')
    ax2.plot(xs, hist_margem_dl, color='#1565C0', lw=1.5, label='Margem DL')
    ax2.plot(xs, hist_margem_ul, color='#B71C1C', lw=1.5, label='Margem UL')
    ax2.axhline(y=30, color='#2E7D32', lw=0.8, linestyle='--', label='Excelente (30 dB)')
    ax2.axhline(y=20, color='#F9A825', lw=0.8, linestyle='--', label='Bom (20 dB)')
    ax2.axhline(y=10, color='#E65100', lw=0.8, linestyle='--', label='Regular (10 dB)')
    ax2.axhline(y=0,  color='#B71C1C', lw=1.2, linestyle='-',  label='Limite crítico')
    ax2.fill_between(xs, hist_margem_dl, 0,
                     where=[v >= 0 for v in hist_margem_dl],
                     color='#1565C0', alpha=0.08)
    ax2.fill_between(xs, hist_margem_ul, 0,
                     where=[v >= 0 for v in hist_margem_ul],
                     color='#B71C1C', alpha=0.08)
    ax2.set_ylabel('Margem [dB]', fontsize=9)
    ax2.set_title('Margem de enlace  (Link Budget – PL medido)', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize='x-small', ncol=3)
    ax2.grid(True, linestyle=':', alpha=0.5)

    # ── Subplot 3: Curva PL × distância (varredura teórica) ──────────────────
    ax3 = fig.add_subplot(313)
    ax3.set_facecolor('#F8F8F8')
    p_cur = c231_capturar_params()
    d_range = [0.5 + i * 0.5 for i in range(200)]  # 0,5 m … 100 m

    pl_curve_mw  = [c231_pl_total(d, p_cur) for d in d_range]
    pl_curve_min = [c231_pl_minimo(d, p_cur) for d in d_range]
    pl_curve_lb  = [p_cur['pt'] - p_cur['sens']] * len(d_range)  # Link budget

    ax3.plot(d_range, pl_curve_mw,  color='#2E7D32', lw=2.0,
             label='COST231 Multi-Wall (parâmetros do operador)')
    ax3.plot(d_range, pl_curve_min, color='#888888', lw=1.2, linestyle=':',
             label='Espaço livre + L_c (sem obstáculos)')
    ax3.axhline(y=p_cur['pt'] - p_cur['sens'], color='#B71C1C', lw=1.2,
                linestyle='--', label=f'Link budget ({p_cur["pt"]:.0f} dBm – {p_cur["sens"]:.0f} dBm)')

    # Marca distância real inserida pelo operador
    pl_real = c231_pl_total(p_cur['d_m'], p_cur)
    ax3.axvline(x=p_cur['d_m'], color='#1565C0', lw=1.0, linestyle='--')
    ax3.scatter([p_cur['d_m']], [pl_real], color='#1565C0', s=40, zorder=5,
                label=f"d operador = {p_cur['d_m']:.1f} m → PL={pl_real:.1f} dB")

    # Ponto atual medido (último valor)
    if hist_pl_dl:
        ax3.scatter([p_cur['d_m']], [hist_pl_dl[-1]], marker='D',
                    color='#1565C0', s=35, zorder=6, label=f"PL_DL atual={hist_pl_dl[-1]:.1f} dB")
        ax3.scatter([p_cur['d_m']], [hist_pl_ul[-1]], marker='D',
                    color='#B71C1C', s=35, zorder=6, label=f"PL_UL atual={hist_pl_ul[-1]:.1f} dB")

    # Linha de distância máxima
    dmax = c231_distancia_maxima(p_cur)
    if 0 < dmax < 200:
        ax3.axvline(x=dmax, color='#E65100', lw=1.0, linestyle=':',
                    label=f'd_max ≈ {dmax:.1f} m')

    ax3.set_xlabel('Distância [m]', fontsize=9)
    ax3.set_ylabel('Path Loss [dB]', fontsize=9)
    ax3.set_title('Curva PL × d  (modelo COST 231 – parâmetros do operador)', fontsize=10, fontweight='bold')
    ax3.legend(loc='lower right', fontsize='x-small', ncol=2)
    ax3.set_xlim(0, 105)
    ax3.grid(True, linestyle=':', alpha=0.5)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.08, hspace=0.52)
    canvas.draw()

    janela_principal.after(REFRESH_MS, atualizar_grafico_c231, fig, canvas)


# Inicia o loop da aba 4
atualizar_grafico_c231(fig_c231, canvas_c231)



# 

# 

# =============================================================================
# FUNÇÕES AUXILIARES LORA (usadas pelas novas abas)
# =============================================================================

def lora_sensibilidade_calculada() -> float:
    """
    Estima a sensibilidade LoRa com base em SF, BW e CR da aba Gerência.
    Fórmula aproximada (referência Semtech):
      SNR_limite(SF) [dBm]  – tabela empírica
      Sens = -174 + 10·log10(BW_Hz) + NF + SNR_limite
      NF típico indoor = 6 dB
    Se os campos estiverem em branco usa o valor do campo ent_sens (Multi-Wall).
    """
    try:
        sf  = int(valor_spreadingfactor.get())
        bw  = int(valor_bandwidth.get())          # kHz
        # SNR limite por SF (Semtech AN1200.22)
        snr_tab = {7: -7.5, 8: -10.0, 9: -12.5, 10: -15.0, 11: -17.5, 12: -20.0}
        snr_lim = snr_tab.get(max(7, min(12, sf)), -20.0)
        nf = 6.0   # noise figure típico
        sens = -174 + 10 * math.log10(bw * 1e3) + nf + snr_lim
        return round(sens, 1)
    except Exception:
        try:
            return float(ent_sens.get())
        except Exception:
            return -137.0


def lora_get_sf_bw_cr() -> tuple:
    """Retorna (SF, BW_kHz, CR_denominador) da aba Gerência."""
    try:   sf = int(valor_spreadingfactor.get())
    except: sf = 12
    try:   bw = int(valor_bandwidth.get())
    except: bw = 125
    try:   cr = int(valor_codingrate.get())
    except: cr = 8
    return sf, bw, cr


# =============================================================================
# ABA 4: LOG-DISTANCE PATH LOSS
# =============================================================================
# Modelo:  PL(d) = PL(d0) + 10·n·log10(d/d0) + X_sigma
#   PL(d0) = espaço livre em d0 (Friis)  → tipicamente d0=1 m
#   n       = expoente de path loss (2.0 = espaço livre, 3-4 = indoor)
#   X_sigma = variável aleatória gaussiana de shadowing (σ em dB)
# A aba lê d, Pt, Sensibilidade e parâmetros de parede do Multi-Wall
# e lê SF/BW/CR da aba Gerência para auto-calcular sensibilidade.
# =============================================================================

aba_logdist = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_logdist, text="  📉 Log-Distance PL  ")

# ── Histórico ──────────────────────────────────────────────────────────────
hist_ld_medida    = []
hist_ld_pl_dl     = []
hist_ld_pl_ul     = []
hist_ld_pl_modelo = []
hist_ld_margem_dl = []
hist_ld_margem_ul = []
ultima_medida_ld  = -1

# ── Frame parâmetros esquerdo ───────────────────────────────────────────────
frm_ld_params = Frame(aba_logdist, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_ld_params.place(x=8, y=8, width=318, height=730)

Label(frm_ld_params, text="Log-Distance Path Loss",
      font=("Arial", 13, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=10)
Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=32, width=295)

# Parâmetros próprios do modelo
Label(frm_ld_params, text="Parâmetros do Modelo", font=("Arial", 11, "bold"),
      bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=40)

Label(frm_ld_params, text="Expoente PL  n", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=65)
Label(frm_ld_params, text="Espaço livre=2 / Indoor≈3-4",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=82)
ent_ld_n = Entry(frm_ld_params, width=8, font=("Arial", 12))
ent_ld_n.place(x=210, y=65); ent_ld_n.insert(0, "3.0")

Label(frm_ld_params, text="Distância ref.  d₀ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=100)
Label(frm_ld_params, text="Tipicamente 1 m",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=117)
ent_ld_d0 = Entry(frm_ld_params, width=8, font=("Arial", 12))
ent_ld_d0.place(x=210, y=100); ent_ld_d0.insert(0, "1.0")

Label(frm_ld_params, text="Desvio Shadowing σ [dB]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=135)
Label(frm_ld_params, text="Indoor típico: 4-12 dB",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=152)
ent_ld_sigma = Entry(frm_ld_params, width=8, font=("Arial", 12))
ent_ld_sigma.place(x=210, y=135); ent_ld_sigma.insert(0, "0.0")

Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=170, width=295)
Label(frm_ld_params, text="Parâmetros do enlace (lidos do Multi-Wall)",
      font=("Arial", 10, "bold"), bg="#F0F0F0", fg="#444").place(x=10, y=178)

# Campos espelhados do Multi-Wall (readonly) – distância e Pt
str_ld_mirror_d   = StringVar(); str_ld_mirror_d.set("d = -- m")
str_ld_mirror_pt  = StringVar(); str_ld_mirror_pt.set("Pt = -- dBm")
str_ld_mirror_sf  = StringVar(); str_ld_mirror_sf.set("SF = --   BW = -- kHz   CR = 4/--")
str_ld_mirror_sens= StringVar(); str_ld_mirror_sens.set("Sens. estimada = -- dBm")

Label(frm_ld_params, textvariable=str_ld_mirror_d,
      font=("Arial", 10), fg="#185FA5", bg="#F0F0F0").place(x=14, y=200)
Label(frm_ld_params, textvariable=str_ld_mirror_pt,
      font=("Arial", 10), fg="#185FA5", bg="#F0F0F0").place(x=14, y=218)
Label(frm_ld_params, textvariable=str_ld_mirror_sf,
      font=("Arial", 10), fg="#2E7D32", bg="#F0F0F0").place(x=14, y=236)
Label(frm_ld_params, textvariable=str_ld_mirror_sens,
      font=("Arial", 10, "bold"), fg="#993C1D", bg="#F0F0F0").place(x=14, y=254)

Label(frm_ld_params, text="(distância e Pt são lidos da aba Multi-Wall;\n SF/BW/CR são lidos da aba Gerência LoRa)",
      font=("Arial", 8), fg="#888888", bg="#F0F0F0", justify="left").place(x=14, y=272)

Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=300, width=295)

def aplicar_parametros_ld():
    global hist_ld_medida, hist_ld_pl_dl, hist_ld_pl_ul
    global hist_ld_pl_modelo, hist_ld_margem_dl, hist_ld_margem_ul, ultima_medida_ld
    for lst in [hist_ld_medida, hist_ld_pl_dl, hist_ld_pl_ul,
                hist_ld_pl_modelo, hist_ld_margem_dl, hist_ld_margem_ul]:
        lst.clear()
    ultima_medida_ld = -1
    lbl_ld_status.config(text="Parâmetros aplicados – aguardando dados...", fg="blue")

btn_ld_aplicar = Button(frm_ld_params, text="▶  APLICAR PARÂMETROS",
                        font=("Arial", 12, "bold"), bg="#185FA5", fg="white",
                        activebackground="#0C447C", cursor="hand2", relief="flat",
                        command=aplicar_parametros_ld, padx=8, pady=5)
btn_ld_aplicar.place(x=10, y=310, width=294)

# Resultados
Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=348, width=295)
Label(frm_ld_params, text="Resultados online",
      font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=356)

str_ld_pl_modelo = StringVar(); str_ld_pl_modelo.set("PL modelo : -- dB")
str_ld_pl_dl     = StringVar(); str_ld_pl_dl.set("PL medido DL: -- dB")
str_ld_pl_ul     = StringVar(); str_ld_pl_ul.set("PL medido UL: -- dB")
str_ld_margem    = StringVar(); str_ld_margem.set("Margem pior: -- dB")
str_ld_dmax      = StringVar(); str_ld_dmax.set("d_max modelo: -- m")
str_ld_qualidade = StringVar(); str_ld_qualidade.set("Qualidade: --")

def _lbl_ld(var, y, cor="black"):
    Label(frm_ld_params, textvariable=var, font=("Arial", 10, "bold"),
          fg=cor, bg="#F0F0F0").place(x=14, y=y)

_lbl_ld(str_ld_pl_modelo, 376, "#185FA5")
_lbl_ld(str_ld_pl_dl,     394, "#3B6D11")
_lbl_ld(str_ld_pl_ul,     412, "#993C1D")
_lbl_ld(str_ld_margem,    430, "#854F0B")
_lbl_ld(str_ld_dmax,      448, "#533")

lbl_ld_qualidade = Label(frm_ld_params, textvariable=str_ld_qualidade,
                          font=("Arial", 13, "bold"), fg="gray", bg="#F0F0F0")
lbl_ld_qualidade.place(x=14, y=476)

lbl_ld_status = Label(frm_ld_params, text="Aguardando dados do Nível 3...",
                       font=("Arial", 9), fg="gray", bg="#F0F0F0",
                       wraplength=290, justify="left")
lbl_ld_status.place(x=10, y=510)

# Fórmula exibida
Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=548, width=295)
Label(frm_ld_params,
      text="PL(d) = PL(d₀) + 10·n·log₁₀(d/d₀)\nPL(d₀) = Friis em d₀\nd_max: PL(d)=Link Budget",
      font=("Arial", 9), fg="#555", bg="#F0F0F0", justify="left").place(x=10, y=556)

# ── Frame gráfico ───────────────────────────────────────────────────────────
frm_ld_graf = Frame(aba_logdist, borderwidth=1, relief='sunken')
frm_ld_graf.place(x=334, y=8, width=1000, height=730)

fig_ld  = Figure(facecolor='white')
canvas_ld = FigureCanvasTkAgg(fig_ld, master=frm_ld_graf)
canvas_ld.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

# ── Funções do modelo Log-Distance ─────────────────────────────────────────

def ld_capturar_params() -> dict:
    """Lê parâmetros do Log-Distance + espelha do Multi-Wall e Gerência."""
    def fval(e, d):
        try: return float(e.get())
        except: return d
    p_mw = c231_capturar_params()
    sens = lora_sensibilidade_calculada()
    sf, bw, cr = lora_get_sf_bw_cr()
    return {
        'n':    max(1.0, fval(ent_ld_n, 3.0)),
        'd0':   max(0.1, fval(ent_ld_d0, 1.0)),
        'sigma':fval(ent_ld_sigma, 0.0),
        'd_m':  p_mw['d_m'],
        'pt':   p_mw['pt'],
        'sens': sens,
        'sf': sf, 'bw': bw, 'cr': cr,
    }


def ld_pl_d0(d0: float) -> float:
    """PL em d0 (Friis) para 915 MHz."""
    if d0 <= 0: return 0.0
    k = 20 * math.log10(4 * math.pi * 1e6 / VELOCIDADE_LUZ)
    return 20 * math.log10(d0) + 20 * math.log10(FREQ_MHZ_C231) + k


def ld_pl_total(d_m: float, p: dict) -> float:
    """PL(d) = PL(d0) + 10·n·log10(d/d0)  [dB]."""
    if d_m <= 0: return 0.0
    ratio = max(d_m / p['d0'], 1e-9)
    return ld_pl_d0(p['d0']) + 10 * p['n'] * math.log10(ratio)


def ld_distancia_maxima(p: dict) -> float:
    """d_max onde PL(d) = Link_budget."""
    try:
        lb = p['pt'] - p['sens']
        pl0 = ld_pl_d0(p['d0'])
        expoente = (lb - pl0) / (10 * p['n'])
        return p['d0'] * (10 ** expoente)
    except Exception:
        return 0.0


def ld_atualizar_grafico(fig, canvas):
    global hist_ld_medida, hist_ld_pl_dl, hist_ld_pl_ul
    global hist_ld_pl_modelo, hist_ld_margem_dl, hist_ld_margem_ul, ultima_medida_ld

    raw = c231_ler_gerencia()
    p   = ld_capturar_params()

    # Atualiza espelhos
    sf, bw, cr = p['sf'], p['bw'], p['cr']
    str_ld_mirror_d.set(f"d = {p['d_m']:.1f} m")
    str_ld_mirror_pt.set(f"Pt = {p['pt']:.0f} dBm")
    str_ld_mirror_sf.set(f"SF={sf}  BW={bw} kHz  CR=4/{cr}")
    str_ld_mirror_sens.set(f"Sens. estimada = {p['sens']:.1f} dBm")

    if raw['valido'] and raw['medida'] != ultima_medida_ld:
        ultima_medida_ld = raw['medida']
        Pt = raw['pw']
        pl_dl = Pt - raw['rssi_dl']
        pl_ul = Pt - raw['rssi_ul']
        pl_mod = ld_pl_total(p['d_m'], p)
        lb  = Pt - p['sens']
        mg_dl = lb - pl_dl
        mg_ul = lb - pl_ul

        hist_ld_medida.append(raw['medida'])
        hist_ld_pl_dl.append(pl_dl)
        hist_ld_pl_ul.append(pl_ul)
        hist_ld_pl_modelo.append(pl_mod)
        hist_ld_margem_dl.append(mg_dl)
        hist_ld_margem_ul.append(mg_ul)

        JANELA = 200
        if len(hist_ld_medida) > JANELA:
            for lst in [hist_ld_medida, hist_ld_pl_dl, hist_ld_pl_ul,
                        hist_ld_pl_modelo, hist_ld_margem_dl, hist_ld_margem_ul]:
                lst.pop(0)

        dmax = ld_distancia_maxima(p)
        mg_pior = min(mg_dl, mg_ul)
        qual_txt, qual_cor = c231_qualidade(mg_pior)

        str_ld_pl_modelo.set(f"PL modelo : {pl_mod:.1f} dB")
        str_ld_pl_dl.set(    f"PL medido DL: {pl_dl:.1f} dB")
        str_ld_pl_ul.set(    f"PL medido UL: {pl_ul:.1f} dB")
        str_ld_margem.set(   f"Margem pior: {mg_pior:.1f} dB")
        str_ld_dmax.set(     f"d_max modelo: {dmax:.1f} m")
        str_ld_qualidade.set(qual_txt)
        lbl_ld_qualidade.config(fg=qual_cor)
        lbl_ld_status.config(
            text=f"Med.{raw['medida']} | n={p['n']:.1f} | d₀={p['d0']:.1f} m | σ={p['sigma']:.1f} dB",
            fg="green"
        )

    # ── Plotagem ────────────────────────────────────────────────────────────
    fig.clear()
    fig.patch.set_facecolor('white')
    xs = hist_ld_medida

    if len(xs) < 2:
        ax = fig.add_subplot(111)
        ax.set_facecolor('#F8F8F8')
        ax.text(0.5, 0.5, 'Aguardando dados do Nível 3...',
                ha='center', va='center', fontsize=13, color='#888888',
                transform=ax.transAxes)
        ax.set_axis_off()
        canvas.draw()
        janela_principal.after(REFRESH_MS, ld_atualizar_grafico, fig, canvas)
        return

    p_cur = ld_capturar_params()

    # Subplot 1 – PL temporal
    ax1 = fig.add_subplot(311)
    ax1.set_facecolor('#F8F8F8')
    ax1.plot(xs, hist_ld_pl_dl,     color='#1565C0', lw=1.6, label='PL medido DL')
    ax1.plot(xs, hist_ld_pl_ul,     color='#B71C1C', lw=1.6, label='PL medido UL')
    ax1.plot(xs, hist_ld_pl_modelo, color='#6A0DAD', lw=2.0, linestyle='--',
             label=f'Log-Distance n={p_cur["n"]:.1f}')
    if p_cur['sigma'] > 0:
        ax1.fill_between(xs,
                         [v - p_cur['sigma'] for v in hist_ld_pl_modelo],
                         [v + p_cur['sigma'] for v in hist_ld_pl_modelo],
                         color='#6A0DAD', alpha=0.12, label=f'±σ={p_cur["sigma"]:.1f} dB')
    ax1.set_ylabel('Path Loss [dB]', fontsize=9)
    ax1.set_title(f'Path Loss – Log-Distance (n={p_cur["n"]:.1f}, d₀={p_cur["d0"]:.1f} m) @ 915 MHz',
                  fontsize=10, fontweight='bold')
    ax1.legend(loc='upper right', fontsize='x-small', ncol=2)
    ax1.grid(True, linestyle=':', alpha=0.5)

    # Subplot 2 – Margem
    ax2 = fig.add_subplot(312)
    ax2.set_facecolor('#F8F8F8')
    ax2.plot(xs, hist_ld_margem_dl, color='#1565C0', lw=1.5, label='Margem DL')
    ax2.plot(xs, hist_ld_margem_ul, color='#B71C1C', lw=1.5, label='Margem UL')
    ax2.axhline(y=30, color='#2E7D32', lw=0.8, linestyle='--', label='Excelente (30 dB)')
    ax2.axhline(y=20, color='#F9A825', lw=0.8, linestyle='--', label='Bom (20 dB)')
    ax2.axhline(y=10, color='#E65100', lw=0.8, linestyle='--', label='Regular (10 dB)')
    ax2.axhline(y=0,  color='#B71C1C', lw=1.2, linestyle='-',  label='Limite crítico')
    ax2.fill_between(xs, hist_ld_margem_dl, 0,
                     where=[v >= 0 for v in hist_ld_margem_dl],
                     color='#1565C0', alpha=0.08)
    ax2.fill_between(xs, hist_ld_margem_ul, 0,
                     where=[v >= 0 for v in hist_ld_margem_ul],
                     color='#B71C1C', alpha=0.08)
    ax2.set_ylabel('Margem [dB]', fontsize=9)
    ax2.set_title('Margem de enlace (Link Budget – PL medido)', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize='x-small', ncol=3)
    ax2.grid(True, linestyle=':', alpha=0.5)

    # Subplot 3 – Curva PL × distância (varredura teórica)
    ax3 = fig.add_subplot(313)
    ax3.set_facecolor('#F8F8F8')
    d_range = [0.5 + i * 0.5 for i in range(200)]   # 0,5…100 m

    pl_ld_curve  = [ld_pl_total(d, p_cur) for d in d_range]
    pl_fs_curve  = [c231_pl_espaco_livre(d) for d in d_range]
    lb_line      = [p_cur['pt'] - p_cur['sens']] * len(d_range)

    ax3.plot(d_range, pl_ld_curve, color='#6A0DAD', lw=2.0,
             label=f'Log-Distance n={p_cur["n"]:.1f}')
    ax3.plot(d_range, pl_fs_curve, color='#888888', lw=1.2, linestyle=':',
             label='Espaço livre (n=2)')
    ax3.axhline(y=p_cur['pt'] - p_cur['sens'], color='#B71C1C', lw=1.2,
                linestyle='--',
                label=f'Link budget ({p_cur["pt"]:.0f} dBm – {p_cur["sens"]:.0f} dBm)')

    if p_cur['sigma'] > 0:
        ax3.fill_between(d_range,
                         [v - p_cur['sigma'] for v in pl_ld_curve],
                         [v + p_cur['sigma'] for v in pl_ld_curve],
                         color='#6A0DAD', alpha=0.12,
                         label=f'Faixa ±σ={p_cur["sigma"]:.1f} dB')

    pl_real = ld_pl_total(p_cur['d_m'], p_cur)
    ax3.axvline(x=p_cur['d_m'], color='#1565C0', lw=1.0, linestyle='--')
    ax3.scatter([p_cur['d_m']], [pl_real], color='#1565C0', s=40, zorder=5,
                label=f"d={p_cur['d_m']:.1f} m → PL={pl_real:.1f} dB")
    if hist_ld_pl_dl:
        ax3.scatter([p_cur['d_m']], [hist_ld_pl_dl[-1]], marker='D',
                    color='#1565C0', s=35, zorder=6,
                    label=f"PL_DL atual={hist_ld_pl_dl[-1]:.1f} dB")
        ax3.scatter([p_cur['d_m']], [hist_ld_pl_ul[-1]], marker='D',
                    color='#B71C1C', s=35, zorder=6,
                    label=f"PL_UL atual={hist_ld_pl_ul[-1]:.1f} dB")

    dmax_ld = ld_distancia_maxima(p_cur)
    if 0 < dmax_ld < 200:
        ax3.axvline(x=dmax_ld, color='#E65100', lw=1.0, linestyle=':',
                    label=f'd_max ≈ {dmax_ld:.1f} m')

    ax3.set_xlabel('Distância [m]', fontsize=9)
    ax3.set_ylabel('Path Loss [dB]', fontsize=9)
    ax3.set_title(f'Curva PL × d  – Log-Distance (n={p_cur["n"]:.1f}, d₀={p_cur["d0"]:.1f} m)',
                  fontsize=10, fontweight='bold')
    ax3.legend(loc='lower right', fontsize='x-small', ncol=2)
    ax3.set_xlim(0, 105)
    ax3.grid(True, linestyle=':', alpha=0.5)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.08, hspace=0.52)
    canvas.draw()
    janela_principal.after(REFRESH_MS, ld_atualizar_grafico, fig, canvas)


ld_atualizar_grafico(fig_ld, canvas_ld)


# =============================================================================
# ABA 5: DUAL-SLOPE PATH LOSS
# =============================================================================
# Modelo Dual-Slope (dois regimes de propagação):
#   d <= d1:   PL(d) = PL_fs(d1_ref) + 10·n1·log10(d/d0)
#   d1 < d <= d2:  PL(d) = PL(d1) + 10·n2·log10(d/d1)
#   d > d2:    PL(d) = PL(d2) + 10·n3·log10(d/d2)
# Lê d, Pt do Multi-Wall; SF/BW/CR da Gerência para sensibilidade.
# =============================================================================

aba_dualslope = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_dualslope, text="  📊 Dual-Slope PL  ")

# ── Histórico ──────────────────────────────────────────────────────────────
hist_ds_medida    = []
hist_ds_pl_dl     = []
hist_ds_pl_ul     = []
hist_ds_pl_modelo = []
hist_ds_margem_dl = []
hist_ds_margem_ul = []
ultima_medida_ds  = -1

# ── Frame parâmetros ────────────────────────────────────────────────────────
frm_ds_params = Frame(aba_dualslope, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_ds_params.place(x=8, y=8, width=318, height=730)

Label(frm_ds_params, text="Dual-Slope Path Loss",
      font=("Arial", 13, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=10)
Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=32, width=295)

Label(frm_ds_params, text="Parâmetros do Modelo", font=("Arial", 11, "bold"),
      bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=40)

# d0 – referência
Label(frm_ds_params, text="Distância ref.  d₀ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=62)
Label(frm_ds_params, text="Ponto base Friis (tipicamente 1 m)",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=79)
ent_ds_d0 = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_d0.place(x=210, y=62); ent_ds_d0.insert(0, "1.0")

# Região 1
Frame(frm_ds_params, bg="#CCAAFF", height=1).place(x=10, y=98, width=295)
Label(frm_ds_params, text="Região 1  (d ≤ d₁)", font=("Arial", 10, "bold"),
      fg="#6A0DAD", bg="#F0F0F0").place(x=10, y=104)
Label(frm_ds_params, text="Breakpoint d₁ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=124)
Label(frm_ds_params, text="Limite entre região 1 e 2",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=141)
ent_ds_d1 = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_d1.place(x=210, y=124); ent_ds_d1.insert(0, "10.0")

Label(frm_ds_params, text="Expoente n₁", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=158)
Label(frm_ds_params, text="Tipicamente ≈ 2 (quase LOS)",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=175)
ent_ds_n1 = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_n1.place(x=210, y=158); ent_ds_n1.insert(0, "2.0")

# Região 2
Frame(frm_ds_params, bg="#AACCFF", height=1).place(x=10, y=194, width=295)
Label(frm_ds_params, text="Região 2  (d₁ < d ≤ d₂)", font=("Arial", 10, "bold"),
      fg="#1565C0", bg="#F0F0F0").place(x=10, y=200)
Label(frm_ds_params, text="Breakpoint d₂ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=220)
Label(frm_ds_params, text="Limite entre região 2 e 3",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=237)
ent_ds_d2 = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_d2.place(x=210, y=220); ent_ds_d2.insert(0, "30.0")

Label(frm_ds_params, text="Expoente n₂", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=254)
Label(frm_ds_params, text="Indoor típico ≈ 3-4",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=271)
ent_ds_n2 = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_n2.place(x=210, y=254); ent_ds_n2.insert(0, "3.5")

# Região 3
Frame(frm_ds_params, bg="#AAFFCC", height=1).place(x=10, y=290, width=295)
Label(frm_ds_params, text="Região 3  (d > d₂)", font=("Arial", 10, "bold"),
      fg="#2E7D32", bg="#F0F0F0").place(x=10, y=296)
Label(frm_ds_params, text="Expoente n₃", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=316)
Label(frm_ds_params, text="Obstrução severa ≈ 4-6",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=333)
ent_ds_n3 = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_n3.place(x=210, y=316); ent_ds_n3.insert(0, "5.0")

# Desvio shadowing
Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=352, width=295)
Label(frm_ds_params, text="Desvio Shadowing σ [dB]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=360)
Label(frm_ds_params, text="Aplicado em toda a curva",
      font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=377)
ent_ds_sigma = Entry(frm_ds_params, width=8, font=("Arial", 12))
ent_ds_sigma.place(x=210, y=360); ent_ds_sigma.insert(0, "0.0")

# Espelhos Multi-Wall / Gerência
Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=396, width=295)
Label(frm_ds_params, text="Parâmetros do enlace (lidos automaticamente)",
      font=("Arial", 10, "bold"), bg="#F0F0F0", fg="#444").place(x=10, y=402)

str_ds_mirror_d    = StringVar(); str_ds_mirror_d.set("d = -- m")
str_ds_mirror_pt   = StringVar(); str_ds_mirror_pt.set("Pt = -- dBm")
str_ds_mirror_sf   = StringVar(); str_ds_mirror_sf.set("SF = --   BW = -- kHz   CR = 4/--")
str_ds_mirror_sens = StringVar(); str_ds_mirror_sens.set("Sens. estimada = -- dBm")

Label(frm_ds_params, textvariable=str_ds_mirror_d,
      font=("Arial", 10), fg="#185FA5", bg="#F0F0F0").place(x=14, y=422)
Label(frm_ds_params, textvariable=str_ds_mirror_pt,
      font=("Arial", 10), fg="#185FA5", bg="#F0F0F0").place(x=14, y=440)
Label(frm_ds_params, textvariable=str_ds_mirror_sf,
      font=("Arial", 10), fg="#2E7D32", bg="#F0F0F0").place(x=14, y=458)
Label(frm_ds_params, textvariable=str_ds_mirror_sens,
      font=("Arial", 10, "bold"), fg="#993C1D", bg="#F0F0F0").place(x=14, y=476)

# Botão aplicar
Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=498, width=295)

def aplicar_parametros_ds():
    global hist_ds_medida, hist_ds_pl_dl, hist_ds_pl_ul
    global hist_ds_pl_modelo, hist_ds_margem_dl, hist_ds_margem_ul, ultima_medida_ds
    for lst in [hist_ds_medida, hist_ds_pl_dl, hist_ds_pl_ul,
                hist_ds_pl_modelo, hist_ds_margem_dl, hist_ds_margem_ul]:
        lst.clear()
    ultima_medida_ds = -1
    lbl_ds_status.config(text="Parâmetros aplicados – aguardando dados...", fg="blue")

btn_ds_aplicar = Button(frm_ds_params, text="▶  APLICAR PARÂMETROS",
                         font=("Arial", 12, "bold"), bg="#185FA5", fg="white",
                         activebackground="#0C447C", cursor="hand2", relief="flat",
                         command=aplicar_parametros_ds, padx=8, pady=5)
btn_ds_aplicar.place(x=10, y=506, width=294)

# Resultados
Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=544, width=295)
Label(frm_ds_params, text="Resultados online",
      font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=550)

str_ds_pl_modelo = StringVar(); str_ds_pl_modelo.set("PL modelo : -- dB")
str_ds_pl_dl     = StringVar(); str_ds_pl_dl.set("PL medido DL: -- dB")
str_ds_pl_ul     = StringVar(); str_ds_pl_ul.set("PL medido UL: -- dB")
str_ds_margem    = StringVar(); str_ds_margem.set("Margem pior: -- dB")
str_ds_dmax      = StringVar(); str_ds_dmax.set("d_max modelo: -- m")
str_ds_regime    = StringVar(); str_ds_regime.set("Regime: --")
str_ds_qualidade = StringVar(); str_ds_qualidade.set("Qualidade: --")

def _lbl_ds(var, y, cor="black"):
    Label(frm_ds_params, textvariable=var, font=("Arial", 10, "bold"),
          fg=cor, bg="#F0F0F0").place(x=14, y=y)

_lbl_ds(str_ds_pl_modelo, 570, "#185FA5")
_lbl_ds(str_ds_pl_dl,     588, "#3B6D11")
_lbl_ds(str_ds_pl_ul,     606, "#993C1D")
_lbl_ds(str_ds_margem,    624, "#854F0B")
_lbl_ds(str_ds_dmax,      642, "#533")
_lbl_ds(str_ds_regime,    660, "#6A0DAD")

lbl_ds_qualidade = Label(frm_ds_params, textvariable=str_ds_qualidade,
                          font=("Arial", 12, "bold"), fg="gray", bg="#F0F0F0")
lbl_ds_qualidade.place(x=14, y=682)

lbl_ds_status = Label(frm_ds_params, text="Aguardando dados do Nível 3...",
                       font=("Arial", 9), fg="gray", bg="#F0F0F0",
                       wraplength=290, justify="left")
lbl_ds_status.place(x=10, y=706)

# ── Frame gráfico ───────────────────────────────────────────────────────────
frm_ds_graf = Frame(aba_dualslope, borderwidth=1, relief='sunken')
frm_ds_graf.place(x=334, y=8, width=1000, height=730)

fig_ds    = Figure(facecolor='white')
canvas_ds = FigureCanvasTkAgg(fig_ds, master=frm_ds_graf)
canvas_ds.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

# ── Funções do modelo Dual-Slope ────────────────────────────────────────────

def ds_capturar_params() -> dict:
    def fval(e, d):
        try: return float(e.get())
        except: return d
    p_mw = c231_capturar_params()
    sens = lora_sensibilidade_calculada()
    sf, bw, cr = lora_get_sf_bw_cr()
    d1 = max(0.5, fval(ent_ds_d1, 10.0))
    d2 = max(d1 + 0.1, fval(ent_ds_d2, 30.0))
    return {
        'd0':   max(0.1, fval(ent_ds_d0, 1.0)),
        'd1':   d1,
        'd2':   d2,
        'n1':   max(1.0, fval(ent_ds_n1, 2.0)),
        'n2':   max(1.0, fval(ent_ds_n2, 3.5)),
        'n3':   max(1.0, fval(ent_ds_n3, 5.0)),
        'sigma':fval(ent_ds_sigma, 0.0),
        'd_m':  p_mw['d_m'],
        'pt':   p_mw['pt'],
        'sens': sens,
        'sf': sf, 'bw': bw, 'cr': cr,
    }


def ds_pl_total(d_m: float, p: dict) -> float:
    """
    Dual-Slope PL:
      Região 1 (d ≤ d1):     PL0 + 10·n1·log10(d/d0)
      Região 2 (d1 < d ≤ d2): PL(d1) + 10·n2·log10(d/d1)
      Região 3 (d > d2):      PL(d2) + 10·n3·log10(d/d2)
    """
    if d_m <= 0: return 0.0
    pl0  = ld_pl_d0(p['d0'])
    pl_d1 = pl0 + 10 * p['n1'] * math.log10(max(p['d1'] / p['d0'], 1e-9))
    pl_d2 = pl_d1 + 10 * p['n2'] * math.log10(max(p['d2'] / p['d1'], 1e-9))

    if d_m <= p['d1']:
        return pl0 + 10 * p['n1'] * math.log10(max(d_m / p['d0'], 1e-9))
    elif d_m <= p['d2']:
        return pl_d1 + 10 * p['n2'] * math.log10(max(d_m / p['d1'], 1e-9))
    else:
        return pl_d2 + 10 * p['n3'] * math.log10(max(d_m / p['d2'], 1e-9))


def ds_regime(d_m: float, p: dict) -> str:
    if d_m <= p['d1']:
        return f"Região 1 (n={p['n1']:.1f}, d≤{p['d1']:.0f}m)"
    elif d_m <= p['d2']:
        return f"Região 2 (n={p['n2']:.1f}, {p['d1']:.0f}<d≤{p['d2']:.0f}m)"
    else:
        return f"Região 3 (n={p['n3']:.1f}, d>{p['d2']:.0f}m)"


def ds_distancia_maxima(p: dict) -> float:
    """Busca binária da distância máxima onde PL(d) = Link Budget."""
    try:
        lb = p['pt'] - p['sens']
        lo, hi = 0.1, 1e5
        for _ in range(60):
            mid = (lo + hi) / 2
            if ds_pl_total(mid, p) < lb:
                lo = mid
            else:
                hi = mid
        return round(lo, 1)
    except Exception:
        return 0.0


def ds_atualizar_grafico(fig, canvas):
    global hist_ds_medida, hist_ds_pl_dl, hist_ds_pl_ul
    global hist_ds_pl_modelo, hist_ds_margem_dl, hist_ds_margem_ul, ultima_medida_ds

    raw = c231_ler_gerencia()
    p   = ds_capturar_params()

    # Atualiza espelhos
    sf, bw, cr = p['sf'], p['bw'], p['cr']
    str_ds_mirror_d.set(f"d = {p['d_m']:.1f} m   (aba Multi-Wall)")
    str_ds_mirror_pt.set(f"Pt = {p['pt']:.0f} dBm   (aba Multi-Wall)")
    str_ds_mirror_sf.set(f"SF={sf}  BW={bw} kHz  CR=4/{cr}  (Gerência)")
    str_ds_mirror_sens.set(f"Sens. estimada = {p['sens']:.1f} dBm")

    if raw['valido'] and raw['medida'] != ultima_medida_ds:
        ultima_medida_ds = raw['medida']
        Pt = raw['pw']
        pl_dl = Pt - raw['rssi_dl']
        pl_ul = Pt - raw['rssi_ul']
        pl_mod = ds_pl_total(p['d_m'], p)
        lb    = Pt - p['sens']
        mg_dl = lb - pl_dl
        mg_ul = lb - pl_ul

        hist_ds_medida.append(raw['medida'])
        hist_ds_pl_dl.append(pl_dl)
        hist_ds_pl_ul.append(pl_ul)
        hist_ds_pl_modelo.append(pl_mod)
        hist_ds_margem_dl.append(mg_dl)
        hist_ds_margem_ul.append(mg_ul)

        JANELA = 200
        if len(hist_ds_medida) > JANELA:
            for lst in [hist_ds_medida, hist_ds_pl_dl, hist_ds_pl_ul,
                        hist_ds_pl_modelo, hist_ds_margem_dl, hist_ds_margem_ul]:
                lst.pop(0)

        dmax = ds_distancia_maxima(p)
        mg_pior = min(mg_dl, mg_ul)
        qual_txt, qual_cor = c231_qualidade(mg_pior)
        reg = ds_regime(p['d_m'], p)

        str_ds_pl_modelo.set(f"PL modelo : {pl_mod:.1f} dB")
        str_ds_pl_dl.set(    f"PL medido DL: {pl_dl:.1f} dB")
        str_ds_pl_ul.set(    f"PL medido UL: {pl_ul:.1f} dB")
        str_ds_margem.set(   f"Margem pior: {mg_pior:.1f} dB")
        str_ds_dmax.set(     f"d_max modelo: {dmax:.1f} m")
        str_ds_regime.set(   reg)
        str_ds_qualidade.set(qual_txt)
        lbl_ds_qualidade.config(fg=qual_cor)
        lbl_ds_status.config(
            text=(f"Med.{raw['medida']} | d₁={p['d1']:.0f}m d₂={p['d2']:.0f}m | "
                  f"n₁={p['n1']:.1f} n₂={p['n2']:.1f} n₃={p['n3']:.1f}"),
            fg="green"
        )

    # ── Plotagem ─────────────────────────────────────────────────────────────
    fig.clear()
    fig.patch.set_facecolor('white')
    xs = hist_ds_medida

    if len(xs) < 2:
        ax = fig.add_subplot(111)
        ax.set_facecolor('#F8F8F8')
        ax.text(0.5, 0.5, 'Aguardando dados do Nível 3...',
                ha='center', va='center', fontsize=13, color='#888888',
                transform=ax.transAxes)
        ax.set_axis_off()
        canvas.draw()
        janela_principal.after(REFRESH_MS, ds_atualizar_grafico, fig, canvas)
        return

    p_cur = ds_capturar_params()

    # Subplot 1 – PL temporal
    ax1 = fig.add_subplot(311)
    ax1.set_facecolor('#F8F8F8')
    ax1.plot(xs, hist_ds_pl_dl,     color='#1565C0', lw=1.6, label='PL medido DL')
    ax1.plot(xs, hist_ds_pl_ul,     color='#B71C1C', lw=1.6, label='PL medido UL')
    ax1.plot(xs, hist_ds_pl_modelo, color='#E65100', lw=2.0, linestyle='--',
             label='Dual-Slope modelo')
    if p_cur['sigma'] > 0:
        ax1.fill_between(xs,
                         [v - p_cur['sigma'] for v in hist_ds_pl_modelo],
                         [v + p_cur['sigma'] for v in hist_ds_pl_modelo],
                         color='#E65100', alpha=0.12, label=f'±σ={p_cur["sigma"]:.1f} dB')
    ax1.set_ylabel('Path Loss [dB]', fontsize=9)
    ax1.set_title(
        f'Path Loss – Dual-Slope (d₁={p_cur["d1"]:.0f} m, d₂={p_cur["d2"]:.0f} m) @ 915 MHz',
        fontsize=10, fontweight='bold')
    ax1.legend(loc='upper right', fontsize='x-small', ncol=2)
    ax1.grid(True, linestyle=':', alpha=0.5)

    # Subplot 2 – Margem
    ax2 = fig.add_subplot(312)
    ax2.set_facecolor('#F8F8F8')
    ax2.plot(xs, hist_ds_margem_dl, color='#1565C0', lw=1.5, label='Margem DL')
    ax2.plot(xs, hist_ds_margem_ul, color='#B71C1C', lw=1.5, label='Margem UL')
    ax2.axhline(y=30, color='#2E7D32', lw=0.8, linestyle='--', label='Excelente (30 dB)')
    ax2.axhline(y=20, color='#F9A825', lw=0.8, linestyle='--', label='Bom (20 dB)')
    ax2.axhline(y=10, color='#E65100', lw=0.8, linestyle='--', label='Regular (10 dB)')
    ax2.axhline(y=0,  color='#B71C1C', lw=1.2, linestyle='-',  label='Limite crítico')
    ax2.fill_between(xs, hist_ds_margem_dl, 0,
                     where=[v >= 0 for v in hist_ds_margem_dl],
                     color='#1565C0', alpha=0.08)
    ax2.fill_between(xs, hist_ds_margem_ul, 0,
                     where=[v >= 0 for v in hist_ds_margem_ul],
                     color='#B71C1C', alpha=0.08)
    ax2.set_ylabel('Margem [dB]', fontsize=9)
    ax2.set_title('Margem de enlace (Link Budget – PL medido)', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize='x-small', ncol=3)
    ax2.grid(True, linestyle=':', alpha=0.5)

    # Subplot 3 – Curva PL × distância (com zonas de cor por regime)
    ax3 = fig.add_subplot(313)
    ax3.set_facecolor('#F8F8F8')
    d_range = [0.1 + i * 0.5 for i in range(200)]   # 0.1…100 m

    pl_ds_curve = [ds_pl_total(d, p_cur) for d in d_range]
    pl_fs_curve = [c231_pl_espaco_livre(d) for d in d_range]
    pl_ld_curve = [ld_pl_total(d, {'n': p_cur['n1'], 'd0': p_cur['d0'],
                                   'pt': p_cur['pt'], 'sens': p_cur['sens']})
                   for d in d_range]

    # Zonas coloridas por regime
    d1, d2 = p_cur['d1'], p_cur['d2']
    dr_r1 = [d for d in d_range if d <= d1]
    pl_r1 = [ds_pl_total(d, p_cur) for d in dr_r1]
    dr_r2 = [d for d in d_range if d1 < d <= d2]
    pl_r2 = [ds_pl_total(d, p_cur) for d in dr_r2]
    dr_r3 = [d for d in d_range if d > d2]
    pl_r3 = [ds_pl_total(d, p_cur) for d in dr_r3]

    if dr_r1: ax3.fill_between(dr_r1, pl_r1, alpha=0.08, color='#6A0DAD')
    if dr_r2: ax3.fill_between(dr_r2, pl_r2, alpha=0.08, color='#1565C0')
    if dr_r3: ax3.fill_between(dr_r3, pl_r3, alpha=0.08, color='#E65100')

    ax3.plot(d_range, pl_ds_curve, color='#E65100', lw=2.5,
             label=f'Dual-Slope (n₁={p_cur["n1"]:.1f} / n₂={p_cur["n2"]:.1f} / n₃={p_cur["n3"]:.1f})')
    ax3.plot(d_range, pl_fs_curve, color='#888888', lw=1.2, linestyle=':',
             label='Espaço livre (n=2)')
    ax3.plot(d_range, pl_ld_curve, color='#6A0DAD', lw=1.2, linestyle='-.',
             label=f'Log-Distance n₁={p_cur["n1"]:.1f} (ref.)')

    ax3.axvline(x=d1, color='#6A0DAD', lw=1.2, linestyle='--',
                label=f'Breakpoint d₁={d1:.0f} m')
    ax3.axvline(x=d2, color='#1565C0', lw=1.2, linestyle='--',
                label=f'Breakpoint d₂={d2:.0f} m')
    ax3.axhline(y=p_cur['pt'] - p_cur['sens'], color='#B71C1C', lw=1.2,
                linestyle='--',
                label=f'Link budget ({p_cur["pt"]:.0f} – {p_cur["sens"]:.0f} dBm)')

    if p_cur['sigma'] > 0:
        ax3.fill_between(d_range,
                         [v - p_cur['sigma'] for v in pl_ds_curve],
                         [v + p_cur['sigma'] for v in pl_ds_curve],
                         color='#E65100', alpha=0.10,
                         label=f'±σ={p_cur["sigma"]:.1f} dB')

    pl_real_ds = ds_pl_total(p_cur['d_m'], p_cur)
    ax3.axvline(x=p_cur['d_m'], color='gray', lw=0.8, linestyle=':')
    ax3.scatter([p_cur['d_m']], [pl_real_ds], color='#E65100', s=45, zorder=6,
                label=f"d={p_cur['d_m']:.1f} m → PL={pl_real_ds:.1f} dB")
    if hist_ds_pl_dl:
        ax3.scatter([p_cur['d_m']], [hist_ds_pl_dl[-1]], marker='D',
                    color='#1565C0', s=35, zorder=7,
                    label=f"PL_DL={hist_ds_pl_dl[-1]:.1f} dB")
        ax3.scatter([p_cur['d_m']], [hist_ds_pl_ul[-1]], marker='D',
                    color='#B71C1C', s=35, zorder=7,
                    label=f"PL_UL={hist_ds_pl_ul[-1]:.1f} dB")

    dmax_ds = ds_distancia_maxima(p_cur)
    if 0 < dmax_ds < 200:
        ax3.axvline(x=dmax_ds, color='#E65100', lw=1.0, linestyle=':',
                    label=f'd_max ≈ {dmax_ds:.1f} m')

    ax3.set_xlabel('Distância [m]', fontsize=9)
    ax3.set_ylabel('Path Loss [dB]', fontsize=9)
    ax3.set_title(
        f'Curva PL × d – Dual-Slope (d₀={p_cur["d0"]:.1f} m  d₁={d1:.0f} m  d₂={d2:.0f} m)',
        fontsize=10, fontweight='bold')
    ax3.legend(loc='lower right', fontsize='x-small', ncol=2)
    ax3.set_xlim(0, 105)
    ax3.grid(True, linestyle=':', alpha=0.5)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.08, hspace=0.52)
    canvas.draw()
    janela_principal.after(REFRESH_MS, ds_atualizar_grafico, fig, canvas)


ds_atualizar_grafico(fig_ds, canvas_ds)


# =============================================================================
# ABA 6: CONEXÃO SERIAL
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

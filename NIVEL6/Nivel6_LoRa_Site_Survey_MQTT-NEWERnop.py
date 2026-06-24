# =============================================================================
# NÍVEL 6 - SISTEMA UNIFICADO COM ABAS
# Versão: Unificado - Aplicação + Gerência + Gerência Completa + Taxas de Dados
# Aba 1: Aplicação (Luminosidade + LED Amarelo com feedback UL)
# Aba 2: Gerência (LoRa Site Survey - RSSI, PSR, Taxa) + Conexão Serial/Parâmetros
# Aba 3: Gerência Completa (RSSI/SNR DL/UL em tempo real - dados do Nível 5)
# Aba 4: Taxas de Dados (PSR%, PER, Taxa Teórica/Efetiva - dados do Nível 5)
# =============================================================================

import time
import os
import tkinter.messagebox as tkMessageBox
import tkinter.filedialog as tkFileDialog
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

# Arquivo intermediário gravado pelo Nível 5 (gerência estatística em tempo
# real). Consumido pela Aba 3 (Gerência Completa) e Aba 4 (Taxas de Dados).
ARQUIVO_N5_GERENCIA = os.path.join(dir_nivel4, 'dados_nivel5.tmp')

# Arquivo intermediário gravado pelo Nível 5 de Aplicação (média móvel da
# luminosidade). Consumido pela Aba 1 (Aplicação).
ARQUIVO_N5_APLICACAO = os.path.join(dir_nivel4, 'dados_nivel5_aplicacao.tmp')

# =============================================================================
# REFRESH das telas
# =============================================================================

REFRESH_MS = 200   # Intervalo de atualização dos gráficos [ms] (200 ms)

# =============================================================================
# ARQUIVO DE COMANDO LED AMARELO
# =============================================================================
CMD_LED_FILE = os.path.join(dir_nivel4, 'cmd_led_amarelo.txt')
if not os.path.exists(CMD_LED_FILE):
    with open(CMD_LED_FILE, "w") as f:
        f.write("0")

# =============================================================================
# ARQUIVO DE FEEDBACK DO LED AMARELO (escrito pelo Nível 3 via UL Byte 39)
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
led_amarelo_feedback = 0        # Feedback do UL Byte 39 (0/1)


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
    """Lê o arquivo de confirmação do LED Amarelo (escrito pelo Nível 3 - UL Byte 39)."""
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
                activebackground="#D3D3D3"
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
# LEITURA DO ARQUIVO DE NÍVEL 5 (dados_nivel5.tmp)
# =============================================================================
# Colunas gravadas pelo Nivel5_Gerencia.py em dados_nivel5.tmp (com cabeçalho
# na primeira linha). Usamos o cabeçalho real do arquivo para montar o índice
# de colunas, assim a leitura não depende de uma ordem fixa "hard-coded".
COLUNAS_N5_PADRAO = (
    "medida;rssi_dl;rssi_dl_max;rssi_dl_min;rssi_dl_desvpad;rssi_dl_mediana;rssi_dl_media_movel;"
    "rssi_ul;rssi_ul_max;rssi_ul_min;rssi_ul_desvpad;rssi_ul_mediana;rssi_ul_media_movel;"
    "snr_dl;snr_dl_max;snr_dl_min;snr_dl_media;"
    "snr_ul;snr_ul_max;snr_ul_min;snr_ul_media;"
    "psr_ul;psr_ul_medio;per_geral_medio;"
    "taxa_teorica;taxa_calculada;"
    "contador_dl;contador_ul;perda_total;lss_status"
).split(';')


def le_dados_nivel5():
    """
    Lê por completo o arquivo dados_nivel5.tmp gravado pelo Nível 5 e retorna
    um dicionário {nome_coluna: [lista_de_valores_float_ou_str]}.
    Caso o arquivo não exista ainda (Nível 5 não iniciado), retorna listas
    vazias para todas as colunas - a interface mostra "--" nesse caso.
    """
    dados = {nome: [] for nome in COLUNAS_N5_PADRAO}

    if not os.path.exists(ARQUIVO_N5_GERENCIA):
        return dados

    try:
        with open(ARQUIVO_N5_GERENCIA, 'r') as f:
            linhas = f.readlines()
    except Exception:
        return dados

    if not linhas:
        return dados

    # A primeira linha é o cabeçalho real gravado pelo Nível 5
    cabecalho = linhas[0].strip().split(';')

    for linha in linhas[1:]:
        linha = linha.strip()
        if not linha:
            continue
        campos = linha.split(';')
        if len(campos) != len(cabecalho):
            continue
        for nome_col, valor in zip(cabecalho, campos):
            if nome_col not in dados:
                continue
            if nome_col == 'lss_status':
                dados[nome_col].append(valor)
            else:
                try:
                    dados[nome_col].append(float(valor))
                except ValueError:
                    dados[nome_col].append(0.0)

    return dados


# =============================================================================
# BOTÃO "SALVAR PNG" - utilitário reutilizado pelas 4 telas gráficas
# =============================================================================
def salvar_grafico_png(fig, nome_sugerido):
    """
    Abre um diálogo "Salvar como" e exporta a figura matplotlib indicada
    para um arquivo PNG no caminho escolhido pelo operador.
    """
    caminho = tkFileDialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("Imagem PNG", "*.png"), ("Todos os arquivos", "*.*")],
        initialfile=nome_sugerido,
        title="Salvar gráfico como PNG"
    )
    if not caminho:
        return  # operador cancelou o diálogo

    try:
        fig.savefig(caminho, dpi=150, facecolor='white', bbox_inches='tight')
        tkMessageBox.showinfo("Salvo com sucesso", f"Gráfico salvo em:\n{caminho}")
    except Exception as e:
        tkMessageBox.showerror("Erro ao salvar", f"Não foi possível salvar o gráfico:\n{e}")


def criar_botao_salvar_png(parent, fig, nome_sugerido, x, y, width=160):
    """
    Cria, na posição (x, y) do frame `parent`, um botão "💾 Salvar PNG" que
    exporta a figura `fig` para PNG. `nome_sugerido` é o nome de arquivo
    padrão oferecido no diálogo "Salvar como" (sem necessidade de extensão).
    """
    btn = Button(
        parent, text="💾 Salvar PNG", font=("Arial", 9, "bold"),
        width=18, bg="#4A6FA5", fg="white", activebackground="#3A5A8C",
        cursor="hand2", relief="raised", bd=2,
        command=lambda: salvar_grafico_png(fig, nome_sugerido)
    )
    btn.place(x=x, y=y, width=width)
    return btn


# =============================================================================
# JANELA PRINCIPAL
# =============================================================================
janela_principal = Tk()
janela_principal.title("SISTEMA LORA SITE SURVEY - MQTT")
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
notebook.add(aba_aplicacao, text="  📊 Aplicação - Luminosidade ")

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
lbl_feedback_led = Label(reg_dados_app, font=("Arial", 10), text="UL Byte[39]: --",
                         fg="gray", bg="#F0F0F0")
lbl_feedback_led.place(x=150, y=330, anchor="center")

# --- GRÁFICO APLICAÇÃO ---
reg_grafico_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken')
reg_grafico_app.place(x=320, y=45, width=700, height=685)

style.use("ggplot")

fig_app = Figure(figsize=(8.5, 7.5), facecolor='white')
canvas_app = FigureCanvasTkAgg(fig_app, master=reg_grafico_app)
canvas_app.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

criar_botao_salvar_png(aba_aplicacao, fig_app, "grafico_aplicacao_luminosidade", x=870, y=10)


def grafico_aplicacao(f, c):
    f.clear()
    x_medidas = []
    y_lum = []
    y_lum_mm = []

    # --- Leitura do dados_nivel5_aplicacao.tmp (Nível 5 - média móvel) ---
    # Preferencial: se o Nível 5 de Aplicação já estiver gerando dados, usa
    # ele como fonte única (luminosidade bruta + média móvel já calculada).
    if os.path.exists(ARQUIVO_N5_APLICACAO):
        try:
            with open(ARQUIVO_N5_APLICACAO, 'r') as dados:
                linhas = dados.readlines()
            for line in linhas[1:]:  # ignora o cabeçalho
                line = line.strip()
                colunas = line.split(';')
                if len(colunas) >= 3 and colunas[0] != '':
                    x_medidas.append(int(float(colunas[0])))
                    y_lum.append(float(colunas[1]))
                    y_lum_mm.append(float(colunas[2]))
        except Exception:
            pass

    # --- Fallback: Nível 5 de Aplicação ainda não iniciado/disponível ---
    # Lê diretamente o dados_aplicacao.tmp (Nível 4) para não deixar o
    # gráfico vazio enquanto o processo Nivel5_Aplicacao.py não é executado.
    if not x_medidas:
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
    if y_lum_mm:
        axis.plot(x_medidas, y_lum_mm, label='Média Móvel', color='darkorange',
                  linewidth=1.8, linestyle='--')
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

    # Atualiza LED: lê feedback do UL Byte 39
    fb = ler_feedback_led()
    lbl_feedback_led.config(
        text=f"UL Byte[39]: {fb}",
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
'''
# Status LSS
lss_status_texto = StringVar()
lss_status_texto.set("TESTE LSS PARADO")

Label(reg_parametrizacao, font=("Arial", 12, "bold"), text="STATUS LSS :",
      fg="blue", padx=5, pady=5, bg="#F0F0F0").place(x=20, y=325)
label_lss_status = Label(reg_parametrizacao, textvariable=lss_status_texto,
                         font=("Arial", 12, "bold"), fg="green", padx=5, pady=5, bg="#F0F0F0")
label_lss_status.place(x=20, y=350)
'''

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
reg_grafico_ger.place(x=320, y=45, width=740, height=695)

fig_ger = Figure(figsize=(8.5, 7.5), facecolor='white')
canvas_ger = FigureCanvasTkAgg(fig_ger, master=reg_grafico_ger)
canvas_ger.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

criar_botao_salvar_png(aba_gerencia, fig_ger, "grafico_gerencia_lora", x=900, y=10)


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
    """
    if lss_status == "1":
        lss_status_texto.set("LSS EM ANDAMENTO"); label_lss_status.config(fg="green")
    elif lss_status == "2":
        lss_status_texto.set("LSS TESTE ENLACE"); label_lss_status.config(fg="green")
    elif lss_status == "3":
        lss_status_texto.set("LSS MUDA RÁDIO"); label_lss_status.config(fg="blue")
    elif lss_status == "4":
        lss_status_texto.set("LSS ENLACE PERDIDO"); label_lss_status.config(fg="red")
    """
    
    path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    if os.path.exists(path_param):
        try:
            pp = open(path_param, 'r')
            status_lido = pp.readline().strip()
            pp.close()
            if status_lido == '0' and status_texto_ger.get() == "TESTE EM ANDAMENTO...":
                status_texto_ger.set("TESTE LSS FINALIZADO")
                label_status_ger.config(fg="green")
            #if lss_status == "0":
            #    lss_status_texto.set("LSS PARADO")
            #    label_lss_status.config(fg="green")
        except Exception:
            pass

    f.subplots_adjust(left=0.12, bottom=0.20, right=0.95, top=0.95, hspace=0.6)
    c.draw()
    janela_principal.after(800, grafico_rssi, f, c)


grafico_rssi(fig_ger, canvas_ger)


# =============================================================================
# ABA 3: GERÊNCIA COMPLETA (RSSI/SNR em tempo real - dados do Nível 5)
# =============================================================================
aba_gerencia_completa = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia_completa, text="  📶 Gerência Completa  ")

# --- COLUNA ESQUERDA: TEXTO (sem gráficos) RSSI e SNR DL/UL ---
reg_texto_ger5 = Frame(master=aba_gerencia_completa, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_texto_ger5.place(x=10, y=10, width=230, height=730)

Label(reg_texto_ger5, font=("Arial", 12, "bold"), text="DADOS NUMÉRICOS",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

# ---- RSSI DOWNLINK ----
Label(reg_texto_ger5, font=("Arial", 11, "bold"), text="RSSI DOWNLINK",
      fg="blue", bg="#F0F0F0").place(x=10, y=35)

str5_rssi_dl_atual = StringVar(value="Atual: -- dBm")
str5_rssi_dl_max = StringVar(value="Máx: -- dBm")
str5_rssi_dl_min = StringVar(value="Mín: -- dBm")
str5_rssi_dl_mm = StringVar(value="Méd. Móvel: -- dBm")
str5_rssi_dl_dp = StringVar(value="Desv. Padrão: -- dB")

for i, var in enumerate([str5_rssi_dl_atual, str5_rssi_dl_max, str5_rssi_dl_min,
                         str5_rssi_dl_mm, str5_rssi_dl_dp]):
    Label(reg_texto_ger5, font=("Arial", 9), textvariable=var,
          bg="#F0F0F0", anchor="w", justify=LEFT).place(x=15, y=58 + i * 20)

# ---- RSSI UPLINK ----
Label(reg_texto_ger5, font=("Arial", 11, "bold"), text="RSSI UPLINK",
      fg="green", bg="#F0F0F0").place(x=10, y=170)

str5_rssi_ul_atual = StringVar(value="Atual: -- dBm")
str5_rssi_ul_max = StringVar(value="Máx: -- dBm")
str5_rssi_ul_min = StringVar(value="Mín: -- dBm")
str5_rssi_ul_mm = StringVar(value="Méd. Móvel: -- dBm")
str5_rssi_ul_dp = StringVar(value="Desv. Padrão: -- dB")

for i, var in enumerate([str5_rssi_ul_atual, str5_rssi_ul_max, str5_rssi_ul_min,
                         str5_rssi_ul_mm, str5_rssi_ul_dp]):
    Label(reg_texto_ger5, font=("Arial", 9), textvariable=var,
          bg="#F0F0F0", anchor="w", justify=LEFT).place(x=15, y=193 + i * 20)

# ---- SNR DOWNLINK ----
Label(reg_texto_ger5, font=("Arial", 11, "bold"), text="SNR DOWNLINK",
      fg="blue", bg="#F0F0F0").place(x=10, y=310)

str5_snr_dl_atual = StringVar(value="Atual: -- dB")
str5_snr_dl_max = StringVar(value="Máx: -- dB")
str5_snr_dl_min = StringVar(value="Mín: -- dB")
str5_snr_dl_media = StringVar(value="Média: -- dB")

for i, var in enumerate([str5_snr_dl_atual, str5_snr_dl_max, str5_snr_dl_min, str5_snr_dl_media]):
    Label(reg_texto_ger5, font=("Arial", 9), textvariable=var,
          bg="#F0F0F0", anchor="w", justify=LEFT).place(x=15, y=333 + i * 20)

# ---- SNR UPLINK ----
Label(reg_texto_ger5, font=("Arial", 11, "bold"), text="SNR UPLINK",
      fg="green", bg="#F0F0F0").place(x=10, y=425)

str5_snr_ul_atual = StringVar(value="Atual: -- dB")
str5_snr_ul_max = StringVar(value="Máx: -- dB")
str5_snr_ul_min = StringVar(value="Mín: -- dB")
str5_snr_ul_media = StringVar(value="Média: -- dB")

for i, var in enumerate([str5_snr_ul_atual, str5_snr_ul_max, str5_snr_ul_min, str5_snr_ul_media]):
    Label(reg_texto_ger5, font=("Arial", 9), textvariable=var,
          bg="#F0F0F0", anchor="w", justify=LEFT).place(x=15, y=448 + i * 20)

# --- ÁREA CENTRAL: 4 GRÁFICOS (RSSI DL, RSSI UL, SNR DL, SNR UL) ---
reg_grafico_ger5 = Frame(master=aba_gerencia_completa, borderwidth=1, relief='sunken')
reg_grafico_ger5.place(x=250, y=45, width=790, height=695)

fig_ger5 = Figure(figsize=(9.2, 7.5), facecolor='white')
canvas_ger5 = FigureCanvasTkAgg(fig_ger5, master=reg_grafico_ger5)
canvas_ger5.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

criar_botao_salvar_png(aba_gerencia_completa, fig_ger5, "grafico_gerencia_completa", x=440, y=10)

# --- COLUNA DIREITA: LIMIARES AJUSTÁVEIS (RSSI x6 + SNR x2) ---
reg_limiares = Frame(master=aba_gerencia_completa, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_limiares.place(x=1050, y=10, width=290, height=730)

Label(reg_limiares, font=("Arial", 12, "bold"), text="LIMIARES (THRESHOLDS)",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

Label(reg_limiares, font=("Arial", 9), text="RSSI: Ruim (acima do limiar 'Ruim'),\n"
                                             "Boa (entre os 2 limiares),\n"
                                             "Excelente (abaixo do limiar 'Excelente')",
      bg="#F0F0F0", justify=LEFT, fg="gray25").place(x=10, y=35)

def _campo_limiar(parent, texto, y_pos, valor_inicial, cor="black"):
    Label(parent, font=("Arial", 10, "bold"), text=texto, fg=cor,
          bg="#F0F0F0").place(x=10, y=y_pos)
    entrada = Entry(parent, width=8, font=("Arial", 10), justify=CENTER)
    entrada.place(x=220, y=y_pos)
    entrada.insert(0, str(valor_inicial))
    return entrada


# --- Limiares RSSI Downlink ---
Label(reg_limiares, font=("Arial", 11, "bold"), text="RSSI DOWNLINK", fg="blue",
      bg="#F0F0F0").place(x=10, y=105)
entry_rssi_dl_ruim = _campo_limiar(reg_limiares, "Ruim (≥)", 130, -100, "red")
entry_rssi_dl_boa = _campo_limiar(reg_limiares, "Boa (≥)", 155, -100, "orange")
entry_rssi_dl_exc = _campo_limiar(reg_limiares, "Excelente (≥)", 180, -75, "green")

# --- Limiares RSSI Uplink ---
Label(reg_limiares, font=("Arial", 11, "bold"), text="RSSI UPLINK", fg="green",
      bg="#F0F0F0").place(x=10, y=215)
entry_rssi_ul_ruim = _campo_limiar(reg_limiares, "Ruim (≥)", 240, -100, "red")
entry_rssi_ul_boa = _campo_limiar(reg_limiares, "Boa (≥)", 265, -100, "orange")
entry_rssi_ul_exc = _campo_limiar(reg_limiares, "Excelente (≥)", 290, -75, "green")

# --- Limiares SNR ---
Label(reg_limiares, font=("Arial", 11, "bold"), text="LIMIAR SNR (dB)", fg="purple",
      bg="#F0F0F0").place(x=10, y=325)
entry_snr_dl_limiar = _campo_limiar(reg_limiares, "SNR Downlink", 350, 0, "blue")
entry_snr_ul_limiar = _campo_limiar(reg_limiares, "SNR Uplink", 375, 0, "green")

lbl_limiar_status = Label(reg_limiares, text="Limiares aplicados aos gráficos\nem tempo real.",
                           font=("Arial", 8), fg="gray30", bg="#F0F0F0", justify=LEFT)
lbl_limiar_status.place(x=10, y=410)


def _ler_float_seguro(entry_widget, default):
    try:
        return float(entry_widget.get())
    except (ValueError, TclError):
        return default


def grafico_gerencia_completa(f, c):
    dados5 = le_dados_nivel5()

    medidas = dados5['medida']
    rssi_dl = dados5['rssi_dl']
    rssi_dl_mm = dados5['rssi_dl_media_movel']
    rssi_ul = dados5['rssi_ul']
    rssi_ul_mm = dados5['rssi_ul_media_movel']
    snr_dl = dados5['snr_dl']
    snr_ul = dados5['snr_ul']
    snr_dl_media = dados5['snr_dl_media']
    snr_ul_media = dados5['snr_ul_media']

    # Lê os limiares atuais inseridos pelo operador
    lim_dl_ruim = _ler_float_seguro(entry_rssi_dl_ruim, -100)
    lim_dl_boa = _ler_float_seguro(entry_rssi_dl_boa, -100)
    lim_dl_exc = _ler_float_seguro(entry_rssi_dl_exc, -75)
    lim_ul_ruim = _ler_float_seguro(entry_rssi_ul_ruim, -100)
    lim_ul_boa = _ler_float_seguro(entry_rssi_ul_boa, -100)
    lim_ul_exc = _ler_float_seguro(entry_rssi_ul_exc, -75)
    lim_snr_dl = _ler_float_seguro(entry_snr_dl_limiar, 0)
    lim_snr_ul = _ler_float_seguro(entry_snr_ul_limiar, 0)

    f.clear()

    # --- Gráfico 1: RSSI Downlink + Limiares ---
    # (a média móvel é mostrada apenas em formato de texto na coluna esquerda)
    ax1 = f.add_subplot(411)
    ax1.plot(medidas, rssi_dl, color='blue', linewidth=1, label='RSSI DL')
    ax1.axhline(lim_dl_exc, color='green', linewidth=0.9, linestyle=':', label='Excelente')
    ax1.axhline(lim_dl_boa, color='orange', linewidth=0.9, linestyle=':', label='Boa')
    ax1.axhline(lim_dl_ruim, color='red', linewidth=0.9, linestyle=':', label='Ruim')
    ax1.set_ylabel('RSSI DL\n(dBm)', fontsize=8)
    ax1.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax1.tick_params(axis='both', labelsize=8)

    # --- Gráfico 2: RSSI Uplink + Limiares ---
    ax2 = f.add_subplot(412)
    ax2.plot(medidas, rssi_ul, color='red', linewidth=1, label='RSSI UL')
    ax2.axhline(lim_ul_exc, color='green', linewidth=0.9, linestyle=':', label='Excelente')
    ax2.axhline(lim_ul_boa, color='orange', linewidth=0.9, linestyle=':', label='Boa')
    ax2.axhline(lim_ul_ruim, color='red', linewidth=0.9, linestyle=':', label='Ruim')
    ax2.set_ylabel('RSSI UL\n(dBm)', fontsize=8)
    ax2.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax2.tick_params(axis='both', labelsize=8)

    # --- Gráfico 3: SNR Downlink + Limiar ---
    ax3 = f.add_subplot(413)
    ax3.plot(medidas, snr_dl, color='blue', linewidth=1, label='SNR DL')
    ax3.axhline(lim_snr_dl, color='purple', linewidth=0.9, linestyle=':', label='Limiar')
    ax3.set_ylabel('SNR DL\n(dB)', fontsize=8)
    ax3.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax3.tick_params(axis='both', labelsize=8)

    # --- Gráfico 4: SNR Uplink + Limiar ---
    ax4 = f.add_subplot(414)
    ax4.plot(medidas, snr_ul, color='green', linewidth=1, label='SNR UL')
    ax4.axhline(lim_snr_ul, color='purple', linewidth=0.9, linestyle=':', label='Limiar')
    ax4.set_ylabel('SNR UL\n(dB)', fontsize=8)
    ax4.set_xlabel('Medida', fontsize=8)
    ax4.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax4.tick_params(axis='both', labelsize=8)

    f.subplots_adjust(left=0.10, bottom=0.07, right=0.97, top=0.97, hspace=0.55)
    c.draw()

    # --- Atualiza coluna de texto à esquerda ---
    if rssi_dl:
        str5_rssi_dl_atual.set(f"Atual: {rssi_dl[-1]:.2f} dBm")
        str5_rssi_dl_max.set(f"Máx: {dados5['rssi_dl_max'][-1]:.2f} dBm")
        str5_rssi_dl_min.set(f"Mín: {dados5['rssi_dl_min'][-1]:.2f} dBm")
        str5_rssi_dl_mm.set(f"Méd. Móvel: {dados5['rssi_dl_media_movel'][-1]:.2f} dBm")
        str5_rssi_dl_dp.set(f"Desv. Padrão: {dados5['rssi_dl_desvpad'][-1]:.3f} dB")

    if rssi_ul:
        str5_rssi_ul_atual.set(f"Atual: {rssi_ul[-1]:.2f} dBm")
        str5_rssi_ul_max.set(f"Máx: {dados5['rssi_ul_max'][-1]:.2f} dBm")
        str5_rssi_ul_min.set(f"Mín: {dados5['rssi_ul_min'][-1]:.2f} dBm")
        str5_rssi_ul_mm.set(f"Méd. Móvel: {dados5['rssi_ul_media_movel'][-1]:.2f} dBm")
        str5_rssi_ul_dp.set(f"Desv. Padrão: {dados5['rssi_ul_desvpad'][-1]:.3f} dB")

    if snr_dl:
        str5_snr_dl_atual.set(f"Atual: {snr_dl[-1]:.2f} dB")
        str5_snr_dl_max.set(f"Máx: {dados5['snr_dl_max'][-1]:.2f} dB")
        str5_snr_dl_min.set(f"Mín: {dados5['snr_dl_min'][-1]:.2f} dB")
        str5_snr_dl_media.set(f"Média: {dados5['snr_dl_media'][-1]:.2f} dB")

    if snr_ul:
        str5_snr_ul_atual.set(f"Atual: {snr_ul[-1]:.2f} dB")
        str5_snr_ul_max.set(f"Máx: {dados5['snr_ul_max'][-1]:.2f} dB")
        str5_snr_ul_min.set(f"Mín: {dados5['snr_ul_min'][-1]:.2f} dB")
        str5_snr_ul_media.set(f"Média: {dados5['snr_ul_media'][-1]:.2f} dB")

    janela_principal.after(REFRESH_MS, grafico_gerencia_completa, f, c)


grafico_gerencia_completa(fig_ger5, canvas_ger5)


# =============================================================================
# ABA 4: TAXAS DE DADOS (PSR% / Taxa Efetiva)
# =============================================================================
aba_taxas = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_taxas, text="  📈 Taxas de Dados  ")

# --- COLUNA ESQUERDA: AMOSTRAGEM EM TEXTO ---
reg_texto_taxas = Frame(master=aba_taxas, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_texto_taxas.place(x=10, y=10, width=270, height=730)

Label(reg_texto_taxas, font=("Arial", 12, "bold"), text="AMOSTRAGEM",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

str4_psr_geral = StringVar(value="-- %")
str4_per_geral = StringVar(value="-- %")
str4_taxa_teorica = StringVar(value="-- bps")
str4_taxa_efetiva = StringVar(value="-- bps")
str4_contador_dl = StringVar(value="-- pacotes")
str4_contador_ul = StringVar(value="-- pacotes")
str4_perdidos = StringVar(value="-- pacotes")


def _campo_texto_taxa(parent, texto, var, y_pos, cor="black"):
    Label(parent, font=("Arial", 11, "bold"), text=texto, fg=cor,
          bg="#F0F0F0").place(x=10, y=y_pos)
    Label(parent, font=("Arial", 13, "bold"), textvariable=var, fg="black",
          bg="#F0F0F0").place(x=10, y=y_pos + 22)


_campo_texto_taxa(reg_texto_taxas, "PSR (Geral)",        str4_psr_geral,    40,  "blue")
_campo_texto_taxa(reg_texto_taxas, "PER (Geral)",        str4_per_geral,    105, "red")
_campo_texto_taxa(reg_texto_taxas, "Taxa Teórica",       str4_taxa_teorica, 170, "purple")
_campo_texto_taxa(reg_texto_taxas, "Taxa Efetiva",       str4_taxa_efetiva, 235, "purple")
_campo_texto_taxa(reg_texto_taxas, "Pacotes Downlink",   str4_contador_dl,  300, "blue")
_campo_texto_taxa(reg_texto_taxas, "Pacotes Uplink",     str4_contador_ul,  365, "green")
_campo_texto_taxa(reg_texto_taxas, "Pacotes Perdidos",   str4_perdidos,     430, "red")

# --- LIMIAR AJUSTÁVEL DE PSR ---
Label(reg_texto_taxas, font=("Arial", 11, "bold"), text="LIMIAR PSR (%)",
      fg="black", bg="#F0F0F0").place(x=10, y=510)
entry_psr_limiar = Entry(reg_texto_taxas, width=8, font=("Arial", 11), justify=CENTER)
entry_psr_limiar.place(x=10, y=535)
entry_psr_limiar.insert(0, "90")

Label(reg_texto_taxas, font=("Arial", 8), fg="gray30", bg="#F0F0F0",
      text="Linha de referência\nno gráfico de PSR.",
      justify=LEFT).place(x=100, y=535)

# --- ÁREA DE GRÁFICOS: PSR% e Taxa Efetiva ---
reg_grafico_taxas = Frame(master=aba_taxas, borderwidth=1, relief='sunken')
reg_grafico_taxas.place(x=290, y=45, width=1050, height=695)

fig_taxas = Figure(figsize=(11.5, 7.5), facecolor='white')
canvas_taxas = FigureCanvasTkAgg(fig_taxas, master=reg_grafico_taxas)
canvas_taxas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

criar_botao_salvar_png(aba_taxas, fig_taxas, "grafico_taxas_dados", x=750, y=10)


def grafico_taxas_dados(f, c):
    dados5 = le_dados_nivel5()

    medidas = dados5['medida']
    psr_ul = dados5['psr_ul']
    psr_ul_medio = dados5['psr_ul_medio']
    per_geral_medio = dados5['per_geral_medio']
    taxa_teorica = dados5['taxa_teorica']
    taxa_calculada = dados5['taxa_calculada']
    contador_dl = dados5['contador_dl']
    contador_ul = dados5['contador_ul']
    perda_total = dados5['perda_total']

    limiar_psr = _ler_float_seguro(entry_psr_limiar, 90)

    f.clear()

    # --- Gráfico 1: PSR% Uplink + Limiar ajustável ---
    # (a média de PSR é mostrada apenas em formato de texto, no painel à esquerda)
    ax1 = f.add_subplot(211)
    ax1.plot(medidas, psr_ul, color='green', linewidth=1, label='PSR UL (%)')
    ax1.axhline(limiar_psr, color='red', linewidth=1.1, linestyle=':', label=f'Limiar ({limiar_psr:.0f}%)')
    ax1.set_ylabel('PSR Uplink (%)')
    ax1.set_ylim(-5, 105)
    ax1.legend(loc='lower right', fontsize='x-small', ncol=2)

    # --- Gráfico 2: Taxa Efetiva (bps) + Limiar Teórico ---
    ax2 = f.add_subplot(212)
    ax2.plot(medidas, taxa_calculada, color='blue', linewidth=1, label='Taxa Efetiva (bps)')
    if taxa_teorica:
        ax2.axhline(taxa_teorica[-1], color='orange', linewidth=1.1, linestyle=':',
                    label=f'Taxa Teórica ({taxa_teorica[-1]:.1f} bps)')
    ax2.set_ylabel('Taxa de Dados (bps)')
    ax2.set_xlabel('Medida')
    ax2.legend(loc='lower right', fontsize='x-small')

    f.subplots_adjust(left=0.08, bottom=0.08, right=0.97, top=0.96, hspace=0.35)
    c.draw()

    # --- Atualiza painel de texto ---
    if psr_ul_medio:
        str4_psr_geral.set(f"{psr_ul_medio[-1]:.2f} %")
    if per_geral_medio:
        str4_per_geral.set(f"{per_geral_medio[-1]:.2f} %")
    if taxa_teorica:
        str4_taxa_teorica.set(f"{taxa_teorica[-1]:.2f} bps")
    if taxa_calculada:
        str4_taxa_efetiva.set(f"{taxa_calculada[-1]:.2f} bps")
    if contador_dl:
        str4_contador_dl.set(f"{int(contador_dl[-1])} pacotes")
    if contador_ul:
        str4_contador_ul.set(f"{int(contador_ul[-1])} pacotes")
    if perda_total:
        str4_perdidos.set(f"{int(perda_total[-1])} pacotes")

    janela_principal.after(REFRESH_MS, grafico_taxas_dados, f, c)


grafico_taxas_dados(fig_taxas, canvas_taxas)




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

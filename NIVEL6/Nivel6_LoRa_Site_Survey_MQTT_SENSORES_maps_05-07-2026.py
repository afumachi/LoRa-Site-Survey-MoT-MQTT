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
from matplotlib.lines import Line2D
import math
import serial
import serial.tools.list_ports
import webbrowser

# Mapa 2D real (tiles OpenStreetMap) para a aba "Mapa Calor LoRa". Dependência
# opcional: se não estiver instalada (`pip install tkintermapview`), a aba usa
# automaticamente o mapa de cobertura em modo alternativo (projeção local
# X/Y em metros, sem tiles de mapa real).
try:
    from tkintermapview import TkinterMapView
    MAPA_REAL_DISPONIVEL = True
except ImportError:
    MAPA_REAL_DISPONIVEL = False



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

# Arquivo intermediário gravado pelo Nível 5 de GPS (distância Gateway-Sensor
# + previsão do modelo Shadowing). Consumido pela Aba "Mapa Calor LoRa".
ARQUIVO_N5_COBERTURA = os.path.join(dir_nivel4, 'N5_log_cobertura.txt')

# Arquivo de configuração do Gateway LoRa (fixo, sem GPS próprio), gravado
# por esta própria tela (aba "Mapa Calor LoRa") e lido pelo Nível5_cobertura.py.
# Formato: 1 valor por linha -> latitude / longitude / altitude / expoente
# 'n' do modelo de propagação Shadowing.
ARQUIVO_GPS_GATEWAY = os.path.join(dir_nivel4, 'gps_gateway.txt')

# Valores padrão do Gateway (instalação fixa em campo, sem sensor GPS).
GATEWAY_LAT_PADRAO = -23.005465
GATEWAY_LON_PADRAO = -46.835370
GATEWAY_ALT_PADRAO = 775.4
EXPOENTE_N_PADRAO = 3.0

# Filtro defensivo: descarta, na leitura, qualquer medida com distância
# acima deste valor. Protege a Aba "Mapa Calor LoRa" contra arquivos
# N5_log_cobertura.txt antigos, gravados antes da validação de GPS ter
# sido implementada no Nível5_cobertura.py (ex.: leituras de altitude
# corrompidas, de "fix" inválido do GPS do sensor).
DISTANCIA_MAXIMA_VALIDA_M = 20000.0

# =============================================================================
# REFRESH das telas
# =============================================================================

REFRESH_MS = 500   # Intervalo de atualização dos gráficos [ms] (200 ms)

# Intervalo de atualização do status/contador de medidas da aba "Mapa Calor
# LoRa" (verificação de PARAMETROS.txt + leitura de N5_log_cobertura.txt).
# Essa aba não exibe telemetria em tempo real (o mapa só é (re)desenhado
# quando o operador clica em "Gerar Mapa de Calor"), então não precisa do
# mesmo ritmo de 500 ms das abas de gráficos ao vivo. Um intervalo mais
# longo aqui reduz a carga de I/O + parsing de arquivo repetida, que
# estava competindo por CPU com as demais atualizações e causando
# lentidão perceptível na interface (inclusive no cursor do mouse).
REFRESH_MAPA_MS = 2000

# Número de medidas amostradas nos gráficos por padrão (ajustável pelo
# operador no campo "Amostragem" da aba Gerência LoRa). Todas as 4 abas
# gráficas (Aplicação, Gerência, Gerência Completa, Taxas de Dados) usam
# esse mesmo valor para decidir quantas das medidas mais recentes exibir.
JANELA_AMOSTRAGEM_PADRAO = 1000

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

'''
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


'''

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
# JANELA DE AMOSTRAGEM - campo ajustável pelo operador (aba Gerência LoRa)
# =============================================================================
# O widget Entry (entry_janela_amostragem) é criado mais abaixo, na aba
# Gerência LoRa, e tem um bind de evento que chama _on_amostragem_editada()
# sempre que o operador efetivamente edita o campo (tecla Enter ou ao saiR
# do campo). Isso é o que permite distinguir com certeza uma edição manual
# de um auto-ajuste feito pelo próprio código.
#
# IMPORTANTE: o valor MOSTRADO no campo pode ser auto-ajustado para baixo
# quando o teste tem menos medidas do que o desejado (regra pedida pelo
# operador). Se essa leitura auto-ajustada fosse reaproveitada como a nova
# "intenção" do operador, o campo travaria no primeiro valor pequeno (ex.:
# 1, na primeira medida do teste) e nunca mais cresceria, mesmo com o teste
# acumulando centenas de medidas depois. Por isso a intenção real do
# operador só é atualizada pelo evento de edição manual do campo - nunca
# pela leitura feita durante o auto-ajuste visual.
_ultima_intencao_amostragem = [JANELA_AMOSTRAGEM_PADRAO]


def _on_amostragem_editada(event=None):
    """
    Callback ligado a eventos reais de edição do campo de amostragem
    (Enter ou perda de foco). Só roda quando o OPERADOR interage com o
    campo, nunca quando o próprio código auto-ajusta o valor exibido -
    por isso pode atualizar a intenção real com segurança.
    """
    try:
        valor = int(float(entry_janela_amostragem.get()))
        if valor > 0:
            _ultima_intencao_amostragem[0] = valor
    except (ValueError, TclError):
        pass


def aplica_janela_amostragem(*series):
    """
    Recebe uma ou mais listas paralelas (mesma quantidade de elementos,
    uma por medida) e retorna apenas os últimos N elementos de cada uma,
    onde N = min(valor desejado pelo operador, total de medidas
    disponíveis). Também atualiza visualmente o campo de amostragem para
    refletir o total real quando este for menor que o desejado (regra:
    "se a quantidade de medidas for inferior a este número, o campo de
    amostragem de medidas será igual ao número de medidas"). A intenção
    real do operador (_ultima_intencao_amostragem) só é alterada pelo
    evento de edição manual do campo (_on_amostragem_editada) - nunca por
    esta função - então o valor desejado nunca se perde, mesmo que o
    campo seja auto-ajustado para baixo por vários ciclos seguidos.

    Uso: medidas, rssi_dl, rssi_ul = aplica_janela_amostragem(medidas, rssi_dl, rssi_ul)
    """
    total_disponivel = len(series[0]) if series else 0
    janela_desejada = _ultima_intencao_amostragem[0]
    janela_efetiva = min(janela_desejada, total_disponivel) if total_disponivel else janela_desejada

    valor_exibido_atual = None
    try:
        valor_exibido_atual = entry_janela_amostragem.get()
    except (NameError, TclError):
        pass

    if valor_exibido_atual is not None:
        novo_valor_exibido = str(min(janela_desejada, total_disponivel)) if total_disponivel else str(janela_desejada)
        if valor_exibido_atual != novo_valor_exibido:
            try:
                entry_janela_amostragem.delete(0, END)
                entry_janela_amostragem.insert(0, novo_valor_exibido)
            except (NameError, TclError):
                pass

    if janela_efetiva <= 0:
        return tuple(series)

    return tuple(serie[-janela_efetiva:] for serie in series)


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


def _aplica_janela_silenciosa(*series):
    """
    Igual a aplica_janela_amostragem, mas sem tocar no campo visual
    entry_janela_amostragem. Usada para séries auxiliares (ex.: temperatura)
    que são lidas de uma fonte separada (dados_aplicacao.tmp bruto do
    Nível 3) e não devem competir com a série principal (luminosidade,
    que pode vir do Nível 5) pela atualização do campo de amostragem.
    """
    total_disponivel = len(series[0]) if series else 0
    janela_desejada = _ultima_intencao_amostragem[0]
    janela_efetiva = min(janela_desejada, total_disponivel) if total_disponivel else janela_desejada
    if janela_efetiva <= 0:
        return tuple(series)
    return tuple(serie[-janela_efetiva:] for serie in series)


# =============================================================================
# GPS - COORDENADAS ATUAIS + BOTÃO "ABRIR NO MAPS"
# =============================================================================
# Guarda a última latitude/longitude válida recebida (lida do
# dados_aplicacao.tmp) para o botão "Abrir no Google Maps" da Aba Aplicação.
_gps_coords_atuais = [None, None]  # [latitude, longitude]


def abrir_no_maps():
    """
    Abre o navegador padrão do sistema no Google Maps, centralizado na
    última coordenada GPS recebida do Nó Sensor (Nível 3).
    """
    lat, lon = _gps_coords_atuais
    if lat is None or lon is None:
        tkMessageBox.showwarning(
            "GPS indisponível",
            "Ainda não há coordenadas GPS recebidas do Nó Sensor."
        )
        return
    url = f"https://www.google.com/maps?q={lat},{lon}"
    webbrowser.open(url)


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
notebook.add(aba_aplicacao, text="  📊 Aplicação - SENSORES ")

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
reg_dados_app.place(x=10, y=120, width=300, height=400)

Label(reg_dados_app, font=("Arial", 14, "bold"), text="DADOS APLICAÇÃO",
      padx=5, pady=3, bg="#F0F0F0").pack(side=TOP, anchor="n")

Label(reg_dados_app, font=("Arial", 11, "bold"), text="LUMINOSIDADE",
      fg="orange", bg="#F0F0F0").place(x=150, y=48, anchor="center")

str_atual_lum = StringVar()
str_atual_lum.set("--")
Label(reg_dados_app, font=("Arial", 20, "bold"), textvariable=str_atual_lum,
      bg="#F0F0F0").place(x=150, y=72, anchor="center")

Label(reg_dados_app, font=("Arial", 11, "bold"), text="TEMPERATURA",
      fg="#D32F2F", bg="#F0F0F0").place(x=150, y=100, anchor="center")

str_atual_temp = StringVar()
str_atual_temp.set("--")
Label(reg_dados_app, font=("Arial", 16, "bold"), textvariable=str_atual_temp,
      bg="#F0F0F0").place(x=150, y=122, anchor="center")

Label(reg_dados_app, font=("Arial", 11, "bold"), text="UMIDADE",
      fg="#1976D2", bg="#F0F0F0").place(x=150, y=148, anchor="center")

str_atual_umid = StringVar()
str_atual_umid.set("--")
Label(reg_dados_app, font=("Arial", 16, "bold"), textvariable=str_atual_umid,
      bg="#F0F0F0").place(x=150, y=170, anchor="center")

# --- LED AMARELO ---
Label(reg_dados_app, font=("Arial", 10, "bold"), text="COMANDA LED AMARELO",
      fg="black", bg="#F0F0F0").place(x=150, y=200, anchor="center")

Label(reg_dados_app, font=("Arial", 8), text="(fundo amarelo = confirmado pelo nó)",
      fg="gray", bg="#F0F0F0").place(x=150, y=218, anchor="center")

led_amarelo_estado = ler_estado_led()

btn_led = Button(reg_dados_app, text="", font=("Arial", 11, "bold"),
                 width=20, height=1, cursor="hand2", relief="raised", bd=3,
                 command=toggle_led)
btn_led.place(x=30, y=232)

# Feedback label
lbl_feedback_led = Label(reg_dados_app, font=("Arial", 9), text="UL Byte[39]: --",
                         fg="gray", bg="#F0F0F0")
lbl_feedback_led.place(x=150, y=270, anchor="center")

# --- COORDENADAS GPS ---
reg_gps_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_gps_app.place(x=10, y=525, width=300, height=180)

Label(reg_gps_app, font=("Arial", 13, "bold"), text="COORDENADAS GPS",
      padx=5, pady=3, bg="#F0F0F0").pack(side=TOP, anchor="n")

Label(reg_gps_app, font=("Arial", 9, "bold"), text="Latitude:",
      fg="black", bg="#F0F0F0").place(x=20, y=45)
str_gps_lat = StringVar()
str_gps_lat.set("--")
Label(reg_gps_app, font=("Arial", 9), textvariable=str_gps_lat,
      bg="#F0F0F0").place(x=105, y=45)

Label(reg_gps_app, font=("Arial", 9, "bold"), text="Longitude:",
      fg="black", bg="#F0F0F0").place(x=20, y=67)
str_gps_lon = StringVar()
str_gps_lon.set("--")
Label(reg_gps_app, font=("Arial", 9), textvariable=str_gps_lon,
      bg="#F0F0F0").place(x=105, y=67)

Label(reg_gps_app, font=("Arial", 9, "bold"), text="Altitude:",
      fg="black", bg="#F0F0F0").place(x=20, y=89)
str_gps_alt = StringVar()
str_gps_alt.set("--")
Label(reg_gps_app, font=("Arial", 9), textvariable=str_gps_alt,
      bg="#F0F0F0").place(x=105, y=89)

btn_maps = Button(reg_gps_app, text="🗺️ Abrir no Google Maps", font=("Arial", 9, "bold"),
                  bg="#2E7D32", fg="white", activebackground="#1B5E20",
                  cursor="hand2", relief="raised", bd=3, command=abrir_no_maps)
btn_maps.place(x=25, y=118, width=250, height=32)

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

    # --- Aplica a janela de amostragem (últimas N medidas) ---
    if y_lum_mm and len(y_lum_mm) == len(x_medidas):
        x_medidas, y_lum, y_lum_mm = aplica_janela_amostragem(x_medidas, y_lum, y_lum_mm)
    else:
        x_medidas, y_lum = aplica_janela_amostragem(x_medidas, y_lum)

    # --- NOVO: Temperatura + Umidade + GPS (lidos direto do dados_aplicacao.tmp) ---
    # O arquivo do Nível 5 (ARQUIVO_N5_APLICACAO) só carrega luminosidade +
    # média móvel, então temperatura, umidade e GPS são lidos sempre da
    # fonte bruta gravada pelo Nível 3 (colunas: medida;luminosidade;
    # temperatura;umidade;latitude;longitude;altitude).
    x_medidas_temp = []
    y_temp = []
    y_umid = []
    lat_atual = lon_atual = alt_atual = None
    path_tmp_raw = os.path.join(dir_nivel4, 'dados_aplicacao.tmp')
    if os.path.exists(path_tmp_raw):
        try:
            with open(path_tmp_raw, 'r') as dados:
                linhas = dados.readlines()
            for line in linhas:
                line = line.strip()
                if not line:
                    continue
                colunas = line.split(';')
                if len(colunas) >= 7 and colunas[0] != '':
                    x_medidas_temp.append(int(colunas[0]))
                    y_temp.append(float(colunas[2]))
                    y_umid.append(float(colunas[3]))
                    lat_atual = float(colunas[4])
                    lon_atual = float(colunas[5])
                    alt_atual = float(colunas[6])
        except Exception:
            pass

    if y_temp:
        str_atual_temp.set(f"{y_temp[-1]:.2f} °C")

    if y_umid:
        str_atual_umid.set(f"{y_umid[-1]:.2f} %")

    if lat_atual is not None and lon_atual is not None:
        str_gps_lat.set(f"{lat_atual:.6f}")
        str_gps_lon.set(f"{lon_atual:.6f}")
        str_gps_alt.set(f"{alt_atual:.2f} m" if alt_atual is not None else "--")
        _gps_coords_atuais[0] = lat_atual
        _gps_coords_atuais[1] = lon_atual

    x_medidas_temp, y_temp, y_umid = _aplica_janela_silenciosa(x_medidas_temp, y_temp, y_umid)

    # --- Subplot 1: Luminosidade ---
    axis = f.add_subplot(311)
    axis.plot(x_medidas, y_lum, label='Luminosidade', color='orange')
    if y_lum_mm:
        axis.plot(x_medidas, y_lum_mm, label='Média Móvel', color='darkorange',
                  linewidth=1.8, linestyle='--')
    axis.set_ylabel('Luminosidade\n(0-4095)', fontsize=8)
    axis.tick_params(axis='both', labelsize=7, labelbottom=False)
    axis.set_ylim(0, 4095)
    axis.legend(loc='upper right', fontsize='x-small')

    # --- Subplot 2: Temperatura (gráfico individual) ---
    axis_temp = f.add_subplot(312, sharex=axis)
    axis_temp.plot(x_medidas_temp, y_temp, label='Temperatura', color='#D32F2F')
    axis_temp.set_ylabel('Temperatura\n(°C)', fontsize=8)
    axis_temp.tick_params(axis='both', labelsize=7, labelbottom=False)
    axis_temp.legend(loc='upper right', fontsize='x-small')

    # --- Subplot 3: Umidade (gráfico individual) ---
    axis_umid = f.add_subplot(313, sharex=axis)
    axis_umid.plot(x_medidas_temp, y_umid, label='Umidade', color='#1976D2')
    axis_umid.set_ylabel('Umidade\n(%)', fontsize=8)
    axis_umid.set_xlabel('Medida', fontsize=8)
    axis_umid.tick_params(axis='both', labelsize=7)
    axis_umid.legend(loc='upper right', fontsize='x-small')

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

    f.subplots_adjust(left=0.13, bottom=0.08, right=0.95, top=0.97, hspace=0.30)
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
valor_potencia_radio.insert(0, "14")

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

# --- AMOSTRAGEM DE MEDIDAS NOS GRÁFICOS ---
# Define quantas das medidas MAIS RECENTES são exibidas nos gráficos das
# 4 abas (Aplicação, Gerência, Gerência Completa, Taxas de Dados). Não
# altera o teste em si (apenas a janela de visualização). Se o teste tiver
# menos medidas do que o valor digitado aqui, o campo é ajustado
# automaticamente para refletir o total real disponível.
Label(reg_parametrizacao, text="Amostragem (qtde. medidas)", font=("Arial", 10, "bold"),
      bg="#F0F0F0", fg="#4A6FA5").place(x=20, y=335)
entry_janela_amostragem = Entry(reg_parametrizacao, width=10, font=("Arial", 12), justify=CENTER)
entry_janela_amostragem.place(x=170, y=333)
entry_janela_amostragem.insert(0, str(JANELA_AMOSTRAGEM_PADRAO))
# Captura a intenção real do operador apenas quando ele de fato edita o
# campo (tecla Enter ou ao clicar fora) - nunca durante o auto-ajuste
# visual feito pelos próprios gráficos.
entry_janela_amostragem.bind("<Return>", _on_amostragem_editada)
entry_janela_amostragem.bind("<FocusOut>", _on_amostragem_editada)

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
srt_atual_taxa_canal = StringVar();      srt_atual_taxa_canal.set("-- kbps") #aaf era bps
srt_atual_taxa_real_canal = StringVar(); srt_atual_taxa_real_canal.set("-- kbps") #aaf era bps
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
    taxa_canal_teorica_str = "0"; taxa_canal_calculada_str = "0"
    taxa_canal_teorica = 0; taxa_canal_calculada = 0
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
                taxa_canal_teorica_str    = y[i][13]
                taxa_canal_calculada_str  = y[i][14]
                snr_DL      = y[i][15]
                snr_UL      = y[i][16]
                counter_DL  = y[i][17]
                counter_UL  = y[i][18]
                perda_total_UL = y[i][19]
                lss_status  = y[i][20]

    taxa_canal_teorica = (float(taxa_canal_teorica_str))/1000
    taxa_canal_calculada = (float(taxa_canal_calculada_str))/1000
    if x:     str_atual_dl.set(f"Atual: {x[-1]} dBm")
    if xUP:   str_atual_ul.set(f"Atual: {xUP[-1]} dBm")
    if psr_dl: str_atual_psr.set(f"Atual: {psr_dl[-1]} %")

    # --- Aplica a janela de amostragem (últimas N medidas) ---
    z, x, xUP, psr_dl = aplica_janela_amostragem(z, x, xUP, psr_dl)

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
    #srt_atual_taxa_canal.set(taxa_canal_teorica + " kbps")#aaf era bps
    srt_atual_taxa_canal.set(f"{taxa_canal_teorica:.3f} kbps")
    #srt_atual_taxa_real_canal.set(taxa_canal_calculada + " kbps")#aaf era bps
    srt_atual_taxa_real_canal.set(f"{taxa_canal_calculada:.3f} kbps")
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
entry_rssi_dl_ruim = _campo_limiar(reg_limiares, "Ruim (≥)", 130, -110, "red")
entry_rssi_dl_boa = _campo_limiar(reg_limiares, "Boa (≥)", 155, -90, "orange")
entry_rssi_dl_exc = _campo_limiar(reg_limiares, "Excelente (≥)", 180, -70, "green")

# --- Limiares RSSI Uplink ---
Label(reg_limiares, font=("Arial", 11, "bold"), text="RSSI UPLINK", fg="green",
      bg="#F0F0F0").place(x=10, y=215)
entry_rssi_ul_ruim = _campo_limiar(reg_limiares, "Ruim (≥)", 240, -110, "red")
entry_rssi_ul_boa = _campo_limiar(reg_limiares, "Boa (≥)", 265, -90, "orange")
entry_rssi_ul_exc = _campo_limiar(reg_limiares, "Excelente (≥)", 290, -70, "green")

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
    lim_dl_ruim = _ler_float_seguro(entry_rssi_dl_ruim, -110)
    lim_dl_boa = _ler_float_seguro(entry_rssi_dl_boa, -90)
    lim_dl_exc = _ler_float_seguro(entry_rssi_dl_exc, -70)
    lim_ul_ruim = _ler_float_seguro(entry_rssi_ul_ruim, -110)
    lim_ul_boa = _ler_float_seguro(entry_rssi_ul_boa, -90)
    lim_ul_exc = _ler_float_seguro(entry_rssi_ul_exc, -70)
    lim_snr_dl = _ler_float_seguro(entry_snr_dl_limiar, 0)
    lim_snr_ul = _ler_float_seguro(entry_snr_ul_limiar, 0)

    # --- Aplica a janela de amostragem (últimas N medidas) apenas nas
    # curvas plotadas. Os agregados (máx/mín/desvio padrão/média/mediana)
    # continuam vindo de dados5 (intocado), pois representam o teste
    # completo, não a janela visível no gráfico.
    medidas_plot, rssi_dl_plot, rssi_ul_plot, snr_dl_plot, snr_ul_plot = (
        aplica_janela_amostragem(medidas, rssi_dl, rssi_ul, snr_dl, snr_ul)
    )

    f.clear()

    # --- Gráfico 1: RSSI Downlink + Limiares ---
    # (a média móvel é mostrada apenas em formato de texto na coluna esquerda)
    ax1 = f.add_subplot(411)
    ax1.plot(medidas_plot, rssi_dl_plot, color='blue', linewidth=1, label='RSSI DL')
    ax1.axhline(lim_dl_exc, color='green', linewidth=0.9, linestyle=':', label='Excelente')
    ax1.axhline(lim_dl_boa, color='orange', linewidth=0.9, linestyle=':', label='Boa')
    ax1.axhline(lim_dl_ruim, color='red', linewidth=0.9, linestyle=':', label='Ruim')
    ax1.set_ylabel('RSSI DL\n(dBm)', fontsize=8)
    ax1.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax1.tick_params(axis='both', labelsize=8)

    # --- Gráfico 2: RSSI Uplink + Limiares ---
    ax2 = f.add_subplot(412)
    ax2.plot(medidas_plot, rssi_ul_plot, color='red', linewidth=1, label='RSSI UL')
    ax2.axhline(lim_ul_exc, color='green', linewidth=0.9, linestyle=':', label='Excelente')
    ax2.axhline(lim_ul_boa, color='orange', linewidth=0.9, linestyle=':', label='Boa')
    ax2.axhline(lim_ul_ruim, color='red', linewidth=0.9, linestyle=':', label='Ruim')
    ax2.set_ylabel('RSSI UL\n(dBm)', fontsize=8)
    ax2.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax2.tick_params(axis='both', labelsize=8)

    # --- Gráfico 3: SNR Downlink + Limiar ---
    ax3 = f.add_subplot(413)
    ax3.plot(medidas_plot, snr_dl_plot, color='blue', linewidth=1, label='SNR DL')
    ax3.axhline(lim_snr_dl, color='purple', linewidth=0.9, linestyle=':', label='Limiar')
    ax3.set_ylabel('SNR DL\n(dB)', fontsize=8)
    ax3.legend(loc='upper right', fontsize='xx-small', ncol=2)
    ax3.tick_params(axis='both', labelsize=8)

    # --- Gráfico 4: SNR Uplink + Limiar ---
    ax4 = f.add_subplot(414)
    ax4.plot(medidas_plot, snr_ul_plot, color='green', linewidth=1, label='SNR UL')
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
str4_taxa_teorica = StringVar(value="-- kbps")#aaf era bps
str4_taxa_efetiva = StringVar(value="-- kbps")#aaf era bps
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
    fundo_eixo_y = 0
    topo_eixo_y = 0
    
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

    # --- Aplica a janela de amostragem (últimas N medidas) apenas nas
    # curvas plotadas. Os agregados (PSR médio, PER médio, taxa teórica
    # atual, contadores) continuam vindo de dados5 (intocado), pois
    # representam o teste completo, não a janela visível no gráfico.
    medidas_plot, psr_ul_plot, taxa_calculada_plot = aplica_janela_amostragem(
        medidas, psr_ul, taxa_calculada
    )

    f.clear()

    # --- Gráfico 1: PSR% Uplink + Limiar ajustável ---
    # (a média de PSR é mostrada apenas em formato de texto, no painel à esquerda)
    ax1 = f.add_subplot(211)
    ax1.plot(medidas_plot, psr_ul_plot, color='green', linewidth=1, label='PSR UL (%)')
    ax1.axhline(limiar_psr, color='red', linewidth=1.1, linestyle=':', label=f'Limiar ({limiar_psr:.0f}%)')
    ax1.set_ylabel('PSR Uplink (%)')
    ax1.set_ylim(-5, 105)
    ax1.legend(loc='lower right', fontsize='x-small', ncol=2)

    """
    # --- Gráfico 2: Taxa Efetiva (kbps) + Limiar Teórico ---#aaf era bps
    ax2 = f.add_subplot(212)
    ax2.plot(medidas_plot, taxa_calculada_plot, color='blue', linewidth=1, label='Taxa Efetiva (kbps)')#aaf era bps
    if taxa_teorica:
        ax2.axhline(taxa_teorica[-1], color='orange', linewidth=1.1, linestyle=':',
                    #label=f'Taxa Teórica ({taxa_teorica[-1]:.1f} bps)')#aaf era bps
                    label=f'Taxa Teórica ({taxa_teorica[-1] / 1000:.3f} kbps)')#aaf era bps
    ax2.set_ylabel('Taxa de Dados (kbps)')#aaf era bps
    ax2.set_xlabel('Medida')
    ax2.legend(loc='lower right', fontsize='x-small')

    f.subplots_adjust(left=0.08, bottom=0.08, right=0.97, top=0.96, hspace=0.35)
    c.draw()
    """
    # --- Gráfico 2: Taxa Efetiva (kbps) + Limiar Teórico ---#aaf era bps
    ax2 = f.add_subplot(212)
    
    # Converte toda a lista de bps para kbps usando list comprehension
    taxa_calculada_kbps = [valor / 1000 for valor in taxa_calculada_plot]
    ax2.plot(medidas_plot, taxa_calculada_kbps, color='blue', linewidth=1, label='Taxa Efetiva (kbps)')
    
    if taxa_teorica:
        # Calcula o valor teórico em kbps uma vez para usar na linha e na legenda
        taxa_teorica_kbps = taxa_teorica[-1] / 1000
        
        # Passa o valor já convertido (taxa_teorica_kbps) para a linha horizontal
        ax2.axhline(taxa_teorica_kbps, color='orange', linewidth=1.1, linestyle=':',
                    label=f'Taxa Teórica ({taxa_teorica_kbps:.3f} kbps)')

    # 2. Define o limite superior (Topo: 5% acima da taxa teórica)
    if taxa_teorica:
        topo_eixo_y = taxa_teorica_kbps * 1.01
        ax2.set_ylim(top=topo_eixo_y)

    if taxa_calculada_kbps:
        menor_taxa = min(taxa_calculada_kbps)
        fundo_eixo_y = menor_taxa * 0.95  # Subtrai 5% (ou seja, mantém 95% do valor)


    ax2.set_ylim(bottom=fundo_eixo_y)    
    ax2.set_ylabel('Taxa de Dados (kbps)')
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
        #str4_taxa_teorica.set(f"{taxa_teorica[-1]:.2f} bps")#aaf era bps
        str4_taxa_teorica.set(f"{taxa_teorica[-1] / 1000:.3f} kbps")
    if taxa_calculada:
        #str4_taxa_efetiva.set(f"{taxa_calculada[-1]:.2f} bps")#aaf era bps
        str4_taxa_efetiva.set(f"{taxa_calculada[-1] / 1000:.3f} kbps")        
    if contador_dl:
        str4_contador_dl.set(f"{int(contador_dl[-1])} pacotes")
    if contador_ul:
        str4_contador_ul.set(f"{int(contador_ul[-1])} pacotes")
    if perda_total:
        str4_perdidos.set(f"{int(perda_total[-1])} pacotes")

    janela_principal.after(REFRESH_MS, grafico_taxas_dados, f, c)


grafico_taxas_dados(fig_taxas, canvas_taxas)


# =============================================================================
# ABA 5: MAPA CALOR LORA (Cobertura RSSI Downlink + Modelo Shadowing)
# =============================================================================
aba_mapa_calor = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_mapa_calor, text="  🗺️ Mapa Calor LoRa  ")

# --- CONFIGURAÇÃO DO GATEWAY (fixo, sem GPS próprio) ---
reg_config_gw = Frame(master=aba_mapa_calor, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_config_gw.place(x=10, y=10, width=300, height=320)

Label(reg_config_gw, font=("Arial", 13, "bold"), text="GATEWAY LORA (FIXO)",
      padx=5, pady=3, bg="#F0F0F0").pack(side=TOP, anchor="n")

Label(reg_config_gw, font=("Arial", 8), justify=LEFT, fg="gray25", bg="#F0F0F0",
      text="Gateway não possui sensor GPS próprio:\ninforme manualmente as coordenadas fixas\nde instalação e o expoente 'n' do modelo\nde propagação Shadowing.").place(x=10, y=28)


def ler_config_gateway():
    """
    Lê o arquivo NIVEL4/gps_gateway.txt (1 valor por linha: latitude,
    longitude, altitude, expoente 'n'). Se ainda não existir (1ª execução),
    retorna os valores padrão definidos acima.
    """
    valores = [GATEWAY_LAT_PADRAO, GATEWAY_LON_PADRAO, GATEWAY_ALT_PADRAO, EXPOENTE_N_PADRAO]
    if os.path.exists(ARQUIVO_GPS_GATEWAY):
        try:
            with open(ARQUIVO_GPS_GATEWAY, 'r') as arq:
                linhas = [l.strip() for l in arq.readlines() if l.strip() != '']
            for i in range(min(len(linhas), 4)):
                valores[i] = float(linhas[i])
        except Exception:
            pass
    return valores


_lat_gw0, _lon_gw0, _alt_gw0, _n0 = ler_config_gateway()


def _campo_gateway(parent, texto, y_pos, valor_inicial):
    Label(parent, font=("Arial", 10, "bold"), text=texto, bg="#F0F0F0").place(x=10, y=y_pos)
    entrada = Entry(parent, width=12, font=("Arial", 10), justify=CENTER)
    entrada.place(x=170, y=y_pos)
    entrada.insert(0, str(valor_inicial))
    return entrada


entry_gw_lat = _campo_gateway(reg_config_gw, "Latitude:", 92, _lat_gw0)
entry_gw_lon = _campo_gateway(reg_config_gw, "Longitude:", 117, _lon_gw0)
entry_gw_alt = _campo_gateway(reg_config_gw, "Altitude (m):", 142, _alt_gw0)

Label(reg_config_gw, font=("Arial", 10, "bold"), text="Expoente 'n' (Shadowing):",
      bg="#F0F0F0").place(x=10, y=175)
entry_gw_n = Entry(reg_config_gw, width=8, font=("Arial", 10), justify=CENTER)
entry_gw_n.place(x=10, y=197)
entry_gw_n.insert(0, str(_n0))

lbl_status_config_gw = Label(reg_config_gw, text="", font=("Arial", 9), bg="#F0F0F0")
lbl_status_config_gw.place(x=15, y=270)


def salvar_config_gateway():
    """
    Valida e grava latitude/longitude/altitude/expoente do Gateway em
    NIVEL4/gps_gateway.txt (1 valor por linha), lido pelo
    Nível5_cobertura.py a cada ciclo.
    """
    try:
        lat_gw = float(entry_gw_lat.get())
        lon_gw = float(entry_gw_lon.get())
        alt_gw = float(entry_gw_alt.get())
        n_exp = float(entry_gw_n.get())
    except (ValueError, TclError):
        tkMessageBox.showerror(
            "Valor inválido",
            "Verifique se latitude, longitude, altitude e o expoente 'n'\nsão números válidos."
        )
        return
    try:
        with open(ARQUIVO_GPS_GATEWAY, 'w') as arq:
            arq.write(f"{lat_gw}\n{lon_gw}\n{alt_gw}\n{n_exp}\n")
        lbl_status_config_gw.config(text="Configuração salva ✔", fg="green")
    except Exception as e:
        tkMessageBox.showerror("Erro ao salvar", f"Não foi possível salvar a configuração do Gateway:\n{e}")


btn_salvar_gw = Button(reg_config_gw, text="💾 Salvar Configuração Gateway",
                       font=("Arial", 9, "bold"), bg="#4A6FA5", fg="white",
                       activebackground="#3A5A8C", cursor="hand2", relief="raised",
                       bd=2, command=salvar_config_gateway)
btn_salvar_gw.place(x=15, y=227, width=270, height=32)

Label(reg_config_gw, font=("Arial", 8), fg="gray30", bg="#F0F0F0", justify=LEFT,
      text="Arquivo: NIVEL4/gps_gateway.txt").place(x=15, y=295)

# Grava a configuração inicial (defaults) caso o arquivo ainda não exista,
# para que o Nível5_cobertura.py já tenha um arquivo válido para ler desde o
# primeiro ciclo.
if not os.path.exists(ARQUIVO_GPS_GATEWAY):
    salvar_config_gateway()

# --- STATUS DO TESTE + BOTÃO "GERAR MAPA DE CALOR" ---
reg_status_mapa = Frame(master=aba_mapa_calor, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_status_mapa.place(x=10, y=340, width=300, height=200)

Label(reg_status_mapa, font=("Arial", 13, "bold"), text="STATUS DO TESTE",
      padx=5, pady=3, bg="#F0F0F0").pack(side=TOP, anchor="n")

status_texto_mapa = StringVar()
status_texto_mapa.set("AGUARDANDO...")
label_status_mapa = Label(reg_status_mapa, textvariable=status_texto_mapa,
                          font=("Arial", 13, "bold"), fg="gray", bg="#F0F0F0")
label_status_mapa.place(x=150, y=45, anchor="center")

lbl_medidas_disponiveis = Label(reg_status_mapa, font=("Arial", 9), text="Medidas disponíveis: --",
                                fg="gray30", bg="#F0F0F0")
lbl_medidas_disponiveis.place(x=150, y=72, anchor="center")


def le_dados_n5_cobertura():
    """
    Lê NIVEL4/N5_log_cobertura.txt, gerado pelo Nível5_cobertura.py: medida;
    latitude;longitude;altitude;distancia_3d_m;rssi_dl_medido;rssi_previsto.

    Linhas com distância acima de DISTANCIA_MAXIMA_VALIDA_M são descartadas
    (proteção contra arquivos gravados antes da validação de GPS ter sido
    implementada no Nível5_cobertura.py, ou contra qualquer corrupção
    residual do arquivo).
    """
    resultado = {'medida': [], 'lat': [], 'lon': [], 'alt': [],
                 'distancia': [], 'rssi_dl': [], 'rssi_previsto': []}
    if os.path.exists(ARQUIVO_N5_COBERTURA):
        try:
            with open(ARQUIVO_N5_COBERTURA, 'r') as arq:
                linhas = arq.readlines()
            for line in linhas[1:]:  # ignora o cabeçalho
                line = line.strip()
                if not line:
                    continue
                c = line.split(';')
                if len(c) >= 7 and c[0] != '':
                    try:
                        distancia = float(c[4])
                    except ValueError:
                        continue
                    if distancia > DISTANCIA_MAXIMA_VALIDA_M:
                        continue
                    resultado['medida'].append(int(float(c[0])))
                    resultado['lat'].append(float(c[1]))
                    resultado['lon'].append(float(c[2]))
                    resultado['alt'].append(float(c[3]))
                    resultado['distancia'].append(distancia)
                    resultado['rssi_dl'].append(float(c[5]))
                    resultado['rssi_previsto'].append(float(c[6]))
        except Exception:
            pass
    return resultado


reg_grafico_mapa = Frame(master=aba_mapa_calor, borderwidth=1, relief='sunken')
reg_grafico_mapa.place(x=320, y=45, width=700, height=685)

if MAPA_REAL_DISPONIVEL:
    # --- Mapa 2D real (tiles OpenStreetMap) no topo + gráfico Shadowing embaixo ---
    frame_mapa_real = Frame(reg_grafico_mapa, height=370)
    frame_mapa_real.pack(side=TOP, fill=BOTH, expand=False)
    frame_mapa_real.pack_propagate(False)

    map_widget_cobertura = TkinterMapView(frame_mapa_real, corner_radius=0)
    map_widget_cobertura.pack(fill=BOTH, expand=True)
    map_widget_cobertura.set_position(GATEWAY_LAT_PADRAO, GATEWAY_LON_PADRAO)
    map_widget_cobertura.set_zoom(16)

    frame_grafico_shadow = Frame(reg_grafico_mapa)
    frame_grafico_shadow.pack(side=TOP, fill=BOTH, expand=True)

    fig_mapa = Figure(figsize=(8.5, 3.1), facecolor='white')
    canvas_mapa = FigureCanvasTkAgg(fig_mapa, master=frame_grafico_shadow)
    canvas_mapa.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)
else:
    # --- Sem tkintermapview instalado (pip install tkintermapview): usa o
    # modo alternativo, com o mapa de cobertura desenhado por projeção
    # local X/Y (metros relativos ao Gateway) na mesma figura do Shadowing.
    map_widget_cobertura = None

    fig_mapa = Figure(figsize=(8.5, 7.5), facecolor='white')
    canvas_mapa = FigureCanvasTkAgg(fig_mapa, master=reg_grafico_mapa)
    canvas_mapa.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

    Label(reg_grafico_mapa, font=("Arial", 8), fg="#B71C1C", bg="white", justify=LEFT,
          text="tkintermapview não instalado (pip install tkintermapview) - "
               "usando mapa de cobertura em modo alternativo (sem tiles reais).").place(x=5, y=5)

criar_botao_salvar_png(aba_mapa_calor, fig_mapa, "shadowing_lora", x=870, y=10)


def _cor_por_rssi_dl(rssi):
    """
    Classifica o RSSI Downlink usando os MESMOS limiares (Ruim/Boa/
    Excelente) configurados pelo operador na aba "Gerência Completa"
    (entry_rssi_dl_ruim / _boa / _exc), para manter os dois painéis
    sempre coerentes entre si.
    """
    lim_ruim = _ler_float_seguro(entry_rssi_dl_ruim, -110)
    lim_boa = _ler_float_seguro(entry_rssi_dl_boa, -90)
    lim_exc = _ler_float_seguro(entry_rssi_dl_exc, -70)
    if rssi >= lim_exc:
        return '#2E7D32'   # verde - excelente
    elif rssi >= lim_boa:
        return '#F9A825'   # amarelo - boa
    elif rssi >= lim_ruim:
        return '#E64A19'   # laranja escuro - ruim
    else:
        return '#616161'   # cinza - sem sinal (abaixo do limiar "Ruim")


def _desenhar_shadowing(ax_shadow, dados, cores, n_exp):
    """Desenha o gráfico do modelo Shadowing (RSSI medido x distância +
    curva teórica prevista), usado tanto no modo com mapa real quanto no
    modo alternativo (fallback)."""
    ax_shadow.scatter(dados['distancia'], dados['rssi_dl'], c=cores, s=30,
                      edgecolors='black', linewidths=0.3, label='RSSI DL medido', zorder=3)

    pares = sorted(zip(dados['distancia'], dados['rssi_previsto']))
    if pares:
        d_ord, rssi_ord = zip(*pares)
        ax_shadow.plot(d_ord, rssi_ord, color='purple', linewidth=1.6, linestyle='--',
                       label=f"Shadowing previsto (n={n_exp:.2f})", zorder=2)

    ax_shadow.set_xlabel('Distância Gateway-Sensor (m)', fontsize=8)
    ax_shadow.set_ylabel('RSSI Downlink (dBm)', fontsize=8)
    ax_shadow.tick_params(axis='both', labelsize=7)
    ax_shadow.legend(loc='best', fontsize='x-small')
    ax_shadow.grid(True, linestyle=':', alpha=0.5)


def gerar_mapa_calor():
    """
    Chamada pelo botão "🔥 Gerar Mapa de Calor". Lê o resultado consolidado
    do Nível5_cobertura.py e desenha:
      (1) o mapa de cobertura - com tiles reais via tkintermapview (marcador
          por medida, colorido pelo RSSI Downlink, mais o marcador fixo do
          Gateway) quando disponível, ou por projeção local X/Y em metros
          caso contrário;
      (2) o gráfico do modelo Shadowing (RSSI medido x distância + curva
          teórica prevista).
    """
    dados = le_dados_n5_cobertura()
    if not dados['medida']:
        tkMessageBox.showwarning(
            "Sem dados",
            "Nenhum dado do Nível5_cobertura.py foi encontrado ainda.\n"
            "Verifique se o Nível5_cobertura.py está em execução e se o teste já foi finalizado."
        )
        return

    lat_gw = _ler_float_seguro(entry_gw_lat, GATEWAY_LAT_PADRAO)
    lon_gw = _ler_float_seguro(entry_gw_lon, GATEWAY_LON_PADRAO)
    n_exp = _ler_float_seguro(entry_gw_n, EXPOENTE_N_PADRAO)

    cores = [_cor_por_rssi_dl(r) for r in dados['rssi_dl']]

    if MAPA_REAL_DISPONIVEL:
        # --- Mapa 2D real: um marcador por medida + marcador do Gateway ---
        map_widget_cobertura.delete_all_marker()
        map_widget_cobertura.set_marker(
            lat_gw, lon_gw, text="Gateway",
            marker_color_circle="#0D47A1", marker_color_outside="#1565C0"
        )
        for lat, lon, cor in zip(dados['lat'], dados['lon'], cores):
            map_widget_cobertura.set_marker(
                lat, lon, text="",
                marker_color_circle=cor, marker_color_outside=cor
            )

        lats_todos = dados['lat'] + [lat_gw]
        lons_todos = dados['lon'] + [lon_gw]
        lat_topo, lat_base = max(lats_todos), min(lats_todos)
        lon_dir, lon_esq = max(lons_todos), min(lons_todos)
        margem_lat = max((lat_topo - lat_base) * 0.15, 0.0008)
        margem_lon = max((lon_dir - lon_esq) * 0.15, 0.0008)
        try:
            map_widget_cobertura.fit_bounding_box(
                (lat_topo + margem_lat, lon_esq - margem_lon),
                (lat_base - margem_lat, lon_dir + margem_lon)
            )
        except Exception:
            map_widget_cobertura.set_position(lat_gw, lon_gw)
            map_widget_cobertura.set_zoom(15)

        # --- Figura contém somente o gráfico Shadowing ---
        fig_mapa.clear()
        ax_shadow = fig_mapa.add_subplot(111)
        _desenhar_shadowing(ax_shadow, dados, cores, n_exp)
        fig_mapa.subplots_adjust(left=0.12, bottom=0.18, right=0.95, top=0.92)

    else:
        # --- Modo alternativo: mapa de cobertura por projeção local X/Y
        # (metros relativos ao Gateway, aproximação equiretangular -
        # adequada para a escala de um Site Survey, tipicamente poucos km) ---
        R_TERRA = 6371000.0
        xs, ys = [], []
        for lat, lon in zip(dados['lat'], dados['lon']):
            x = math.radians(lon - lon_gw) * R_TERRA * math.cos(math.radians(lat_gw))
            y = math.radians(lat - lat_gw) * R_TERRA
            xs.append(x)
            ys.append(y)

        fig_mapa.clear()

        ax_mapa = fig_mapa.add_subplot(211)
        ax_mapa.scatter(xs, ys, c=cores, s=45, edgecolors='black', linewidths=0.4, zorder=3)
        ax_mapa.scatter([0], [0], marker='*', s=260, c='blue', edgecolors='black',
                        linewidths=0.8, zorder=4)
        ax_mapa.set_xlabel('Distância Leste-Oeste (m)', fontsize=8)
        ax_mapa.set_ylabel('Distância Norte-Sul (m)', fontsize=8)
        ax_mapa.tick_params(axis='both', labelsize=7)
        ax_mapa.set_aspect('equal', adjustable='datalim')
        ax_mapa.grid(True, linestyle=':', alpha=0.5)
        ax_mapa.set_title('Mapa de Cobertura LoRa - RSSI Downlink', fontsize=9, fontweight='bold')

        legenda_cores = [
            Line2D([0], [0], marker='o', color='w', label='Excelente',
                   markerfacecolor='#2E7D32', markersize=8),
            Line2D([0], [0], marker='o', color='w', label='Boa',
                   markerfacecolor='#F9A825', markersize=8),
            Line2D([0], [0], marker='o', color='w', label='Ruim',
                   markerfacecolor='#E64A19', markersize=8),
            Line2D([0], [0], marker='o', color='w', label='Sem sinal',
                   markerfacecolor='#616161', markersize=8),
            Line2D([0], [0], marker='*', color='w', label='Gateway',
                   markerfacecolor='blue', markersize=13),
        ]
        ax_mapa.legend(handles=legenda_cores, loc='best', fontsize='xx-small', ncol=2)

        ax_shadow = fig_mapa.add_subplot(212)
        _desenhar_shadowing(ax_shadow, dados, cores, n_exp)

        fig_mapa.subplots_adjust(left=0.12, bottom=0.08, right=0.95, top=0.94, hspace=0.35)

    canvas_mapa.draw()


btn_gerar_mapa = Button(reg_status_mapa, text="🔥 Gerar Mapa de Calor",
                        font=("Arial", 11, "bold"), bg="#B0B0B0", fg="white",
                        activebackground="#8C8C8C", cursor="hand2", relief="raised",
                        bd=3, state=DISABLED,
                        command=gerar_mapa_calor)
btn_gerar_mapa.place(x=25, y=100, width=250, height=40)

Label(reg_status_mapa, font=("Arial", 8), fg="gray30", bg="#F0F0F0", justify=LEFT,
      text="Habilitado somente após o teste ser\nfinalizado (LSS parado) e com medidas\ndisponíveis do Nível5_cobertura.py.").place(x=15, y=150)


def contar_medidas_n5_cobertura():
    """
    Conta rapidamente quantas linhas de dados válidas existem em
    N5_log_cobertura.txt, sem fazer o parse completo (conversão para
    float de todas as colunas) feito por le_dados_n5_cobertura(). Usada
    apenas para o contador/status periódico da tela, que não precisa dos
    valores em si - só da quantidade de medidas disponíveis.
    """
    if not os.path.exists(ARQUIVO_N5_COBERTURA):
        return 0
    try:
        with open(ARQUIVO_N5_COBERTURA, 'r') as arq:
            linhas = arq.readlines()
    except Exception:
        return 0
    return sum(1 for l in linhas[1:] if l.strip())


def atualizar_status_mapa_calor():
    """
    Verifica periodicamente (a cada REFRESH_MAPA_MS) se o teste está em
    andamento (PARAMETROS.txt) e se há dados prontos do Nível5_cobertura.py,
    habilitando o botão "Gerar Mapa de Calor" apenas quando o teste estiver
    finalizado e houver ao menos uma medida disponível.
    """
    status_lido = '0'
    path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    if os.path.exists(path_param):
        try:
            with open(path_param, 'r') as pp:
                status_lido = pp.readline().strip()
        except Exception:
            pass

    n_medidas = contar_medidas_n5_cobertura()
    lbl_medidas_disponiveis.config(text=f"Medidas disponíveis: {n_medidas}")

    if status_lido == '1':
        status_texto_mapa.set("TESTE EM ANDAMENTO")
        label_status_mapa.config(fg="green")
        btn_gerar_mapa.config(state=DISABLED, bg="#B0B0B0")
    else:
        status_texto_mapa.set("TESTE FINALIZADO" if n_medidas > 0 else "AGUARDANDO TESTE")
        label_status_mapa.config(fg="blue" if n_medidas > 0 else "gray")
        if n_medidas > 0:
            btn_gerar_mapa.config(state=NORMAL, bg="#C62828")
        else:
            btn_gerar_mapa.config(state=DISABLED, bg="#B0B0B0")

    janela_principal.after(REFRESH_MAPA_MS, atualizar_status_mapa_calor)


atualizar_status_mapa_calor()


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

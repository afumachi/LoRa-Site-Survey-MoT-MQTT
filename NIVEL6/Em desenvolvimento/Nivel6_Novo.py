# =============================================================================
# NÍVEL 6 (NOVO) – SISTEMA UNIFICADO COM ABAS
# Versão: 2.0 – Integração com Nível 5
#
# Aba 1: Aplicação       (Luminosidade + LED Amarelo)
# Aba 2: Gerência LoRa   (RSSI, PSR, Taxa + salvar gráfico)
# Aba 3: Multi-Wall      (lê resultado_multiwall.txt do N5 + salvar gráfico)
# Aba 4: Log-Distance PL (lê resultado_logdistance.txt do N5 + salvar gráfico)
# Aba 5: Dual-Slope PL   (lê resultado_dualslope.txt do N5 + salvar gráfico)
# Aba 6: Conexão Serial  (porta COM)
#
# Fluxo:
#   1. Operador ajusta parâmetros nas abas de modelos.
#   2. Nível 6 grava parametros_modelos.txt em NIVEL4/ a cada mudança.
#   3. Nível 5 (processo separado) lê gerência, calcula e grava TXTs.
#   4. Nível 6 lê TXTs e exibe gráficos a cada REFRESH_MS ms.
#   5. Ao iniciar novo teste: Nível 5 apaga TXTs antigos e recria.
# =============================================================================

import time
import os
import tkinter.messagebox as tkMessageBox
import tkinter.filedialog as filedialog
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

CMD_LED_FILE        = os.path.join(dir_nivel4, 'cmd_led_amarelo.txt')
CONF_CMD_LED_FILE   = os.path.join(dir_nivel4, 'conf_cmd_led_amarelo.txt')
SERIAL_CONFIG_FILE  = os.path.join(dir_nivel4, 'serial_config.txt')
PARAMS_MODELOS      = os.path.join(dir_nivel4, 'parametros_modelos.txt')

OUT_MULTIWALL       = os.path.join(dir_nivel4, 'resultado_multiwall.txt')
OUT_LOGDISTANCE     = os.path.join(dir_nivel4, 'resultado_logdistance.txt')
OUT_DUALSLOPE       = os.path.join(dir_nivel4, 'resultado_dualslope.txt')

# =============================================================================
# INICIALIZA ARQUIVOS NECESSÁRIOS
# =============================================================================
for _arq, _val in [(CMD_LED_FILE, "0"), (CONF_CMD_LED_FILE, "0")]:
    if not os.path.exists(_arq):
        with open(_arq, "w") as _f:
            _f.write(_val)

# =============================================================================
# REFRESH
# =============================================================================
REFRESH_MS = 800

# =============================================================================
# CONSTANTES FÍSICAS (para curvas teóricas exibidas pelo N6)
# =============================================================================
FREQ_MHZ       = 915.0
VELOCIDADE_LUZ = 3e8
B_EMPIRICO     = 0.46

# =============================================================================
# VARIÁVEIS GLOBAIS
# =============================================================================
led_amarelo_estado  = 0
led_amarelo_feedback = 0


# =============================================================================
# FUNÇÕES AUXILIARES FÍSICAS (curvas teóricas nos gráficos)
# =============================================================================

def pl_espaco_livre(d_m):
    if d_m <= 0: return 0.0
    k = 20 * math.log10(4 * math.pi * 1e6 / VELOCIDADE_LUZ)
    return 20 * math.log10(d_m) + 20 * math.log10(FREQ_MHZ) + k

def mw_pl_curva(d_m, p):
    waf = p['k1']*p['lw1'] + p['k2']*p['lw2'] + p['k3']*p['lw3'] + p['k4']*p['lw4']
    nf, lf = p['nf'], p['lf']
    faf = 0.0
    if nf > 0 and lf > 0:
        faf = (nf ** ((nf+2)/(nf+1) - B_EMPIRICO)) * lf
    return pl_espaco_livre(d_m) + p['lc'] + waf + faf

def ld_pl_curva(d_m, p):
    d0 = p['ld_d0']
    if d_m <= 0: return 0.0
    return pl_espaco_livre(d0) + 10*p['ld_n']*math.log10(max(d_m/d0, 1e-9))

def ds_pl_curva(d_m, p):
    if d_m <= 0: return 0.0
    pl0  = pl_espaco_livre(p['ds_d0'])
    pl_d1 = pl0  + 10*p['ds_n1']*math.log10(max(p['ds_d1']/p['ds_d0'], 1e-9))
    pl_d2 = pl_d1 + 10*p['ds_n2']*math.log10(max(p['ds_d2']/p['ds_d1'], 1e-9))
    if d_m <= p['ds_d1']:
        return pl0 + 10*p['ds_n1']*math.log10(max(d_m/p['ds_d0'], 1e-9))
    elif d_m <= p['ds_d2']:
        return pl_d1 + 10*p['ds_n2']*math.log10(max(d_m/p['ds_d1'], 1e-9))
    else:
        return pl_d2 + 10*p['ds_n3']*math.log10(max(d_m/p['ds_d2'], 1e-9))

def cor_qualidade(qual):
    m = {'EXCELENTE': 'green', 'BOM': '#1a7a1a', 'REGULAR': 'orange',
         'RUIM': 'red', 'CRITICO': 'darkred'}
    return m.get(qual, 'gray')


# =============================================================================
# LEITURA DO ARQUIVO DE RESULTADOS DO NÍVEL 5
# =============================================================================

def ler_resultado_txt(caminho):
    """Retorna lista de listas de strings para cada linha do TXT."""
    if not os.path.exists(caminho):
        return []
    linhas = []
    try:
        with open(caminho, 'r') as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    linhas.append(ln.split(';'))
    except Exception:
        pass
    return linhas


# =============================================================================
# GRAVAÇÃO DE parametros_modelos.txt (lido pelo Nível 5)
# =============================================================================

def gravar_parametros_modelos(p: dict):
    try:
        with open(PARAMS_MODELOS, 'w', encoding='utf-8') as f:
            f.write("# Parâmetros dos Modelos de Propagação – gerado pelo Nível 6\n")
            f.write(f"d_m={p['d_m']:.2f}\n")
            f.write(f"pt={p['pt']:.1f}\n")
            f.write(f"sf={p['sf']}\n")
            f.write(f"bw={p['bw']}\n")
            f.write(f"cr={p['cr']}\n")
            f.write("# Multi-Wall\n")
            f.write(f"k1={p['k1']}  lw1={p['lw1']:.2f}\n")
            f.write(f"k2={p['k2']}  lw2={p['lw2']:.2f}\n")
            f.write(f"k3={p['k3']}  lw3={p['lw3']:.2f}\n")
            f.write(f"k4={p['k4']}  lw4={p['lw4']:.2f}\n")
            f.write(f"nf={p['nf']}  lf={p['lf']:.2f}\n")
            f.write(f"lc={p['lc']:.2f}\n")
            f.write(f"sens={p['sens']:.1f}\n")
            f.write("# Log-Distance\n")
            f.write(f"ld_n={p['ld_n']:.2f}\n")
            f.write(f"ld_d0={p['ld_d0']:.2f}\n")
            f.write(f"ld_sigma={p['ld_sigma']:.2f}\n")
            f.write("# Dual-Slope\n")
            f.write(f"ds_d0={p['ds_d0']:.2f}\n")
            f.write(f"ds_d1={p['ds_d1']:.2f}\n")
            f.write(f"ds_d2={p['ds_d2']:.2f}\n")
            f.write(f"ds_n1={p['ds_n1']:.2f}\n")
            f.write(f"ds_n2={p['ds_n2']:.2f}\n")
            f.write(f"ds_n3={p['ds_n3']:.2f}\n")
            f.write(f"ds_sigma={p['ds_sigma']:.2f}\n")
    except Exception as e:
        print(f"[N6] Erro ao gravar parametros_modelos.txt: {e}")


def apagar_resultados_n5():
    """Apaga os TXTs de resultado do N5 (chamado ao iniciar novo teste)."""
    for arq in [OUT_MULTIWALL, OUT_LOGDISTANCE, OUT_DUALSLOPE]:
        if os.path.exists(arq):
            try:
                os.remove(arq)
                print(f"[N6] Removido: {os.path.basename(arq)}")
            except Exception as e:
                print(f"[N6] Erro ao remover {arq}: {e}")


# =============================================================================
# LED AMARELO
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
        print(f"Erro cmd_led_amarelo.txt: {e}")

def ler_feedback_led():
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

def atualizar_visual_led():
    fb = ler_feedback_led()
    if fb == 1:
        btn_led.config(text="LED AMARELO: ON ✔", bg="#FFD700", fg="#333333",
                       activebackground="#FFC200")
    else:
        if led_amarelo_estado == 1:
            btn_led.config(text="LED AMARELO: CMD ON", bg="#FFA500", fg="#FFFFFF",
                           activebackground="#FF8C00")
        else:
            btn_led.config(text="LED AMARELO: OFF", bg="#555555", fg="#FFFFFF",
                           activebackground="#444444")


# =============================================================================
# PORTA SERIAL
# =============================================================================

def listar_portas():
    ports = serial.tools.list_ports.comports()
    lista = [f"{p.device} - {p.description}" for p in ports]
    return lista if lista else ["Nenhuma porta encontrada"]

def atualizar_lista_portas():
    portas = listar_portas()
    combo_portas['values'] = portas
    if portas and portas[0] != "Nenhuma porta encontrada":
        combo_portas.current(0)
    lbl_serial_status.config(text="Lista atualizada.", fg="blue")

def salvar_porta_serial():
    selecao = combo_portas.get()
    if not selecao or selecao == "Nenhuma porta encontrada":
        lbl_serial_status.config(text="Nenhuma porta válida selecionada.", fg="red")
        return
    porta = selecao.split(" - ")[0].strip()
    try:
        with open(SERIAL_CONFIG_FILE, "w") as f:
            f.write(porta + "\n")
        lbl_serial_status.config(text=f"Porta '{porta}' salva! Reinicie o Nível 3.", fg="green")
        lbl_porta_ativa.config(text=f"Porta ativa: {porta}", fg="green")
    except Exception as e:
        lbl_serial_status.config(text=f"Erro ao salvar: {e}", fg="red")

def ler_porta_ativa():
    try:
        with open(SERIAL_CONFIG_FILE, "r") as f:
            return f.read().strip()
    except Exception:
        return "Não configurada"


# =============================================================================
# SALVAR GRÁFICO (função genérica)
# =============================================================================

def salvar_grafico(fig, nome_sugerido="grafico"):
    """Abre diálogo para salvar o figura matplotlib como PNG ou PDF."""
    caminho = filedialog.asksaveasfilename(
        defaultextension=".png",
        filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
        initialfile=nome_sugerido,
        title="Salvar gráfico"
    )
    if not caminho:
        return
    try:
        fig.savefig(caminho, dpi=150, bbox_inches='tight')
        tkMessageBox.showinfo("Gráfico salvo", f"Arquivo salvo em:\n{caminho}")
        print(f"[N6] Gráfico salvo: {caminho}")
    except Exception as e:
        tkMessageBox.showerror("Erro", f"Não foi possível salvar:\n{e}")


# =============================================================================
# JANELA PRINCIPAL
# =============================================================================
janela_principal = Tk()
janela_principal.title("SISTEMA LORA - NÍVEL 6 UNIFICADO v2.0")
janela_principal.geometry('1380x800')
janela_principal.resizable(True, True)

notebook = ttk.Notebook(janela_principal)
notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)

style_ttk = ttk.Style()
style_ttk.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=[12, 6])


# =============================================================================
# ABA 1: APLICAÇÃO
# =============================================================================
aba_aplicacao = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_aplicacao, text="  📊 Aplicação  ")

reg_status_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_status_app.place(x=10, y=10, width=300, height=100)
Label(reg_status_app, font=("Arial", 14, "bold"), text="STATUS DO SISTEMA",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")
status_texto_app = StringVar(); status_texto_app.set("AGUARDANDO...")
label_status_app = Label(reg_status_app, textvariable=status_texto_app,
                         font=("Arial", 16, "bold"), fg="gray", bg="#F0F0F0")
label_status_app.place(x=150, y=55, anchor="center")

reg_dados_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_dados_app.place(x=10, y=120, width=300, height=420)
Label(reg_dados_app, font=("Arial", 16, "bold"), text="DADOS APLICAÇÃO",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")
Label(reg_dados_app, font=("Arial", 13, "bold"), text="LUMINOSIDADE",
      fg="orange", padx=5, pady=5, bg="#F0F0F0").place(x=150, y=100, anchor="center")
str_atual_lum = StringVar(); str_atual_lum.set("--")
Label(reg_dados_app, font=("Arial", 30, "bold"), textvariable=str_atual_lum,
      padx=5, pady=2, bg="#F0F0F0").place(x=150, y=150, anchor="center")
Label(reg_dados_app, font=("Arial", 11, "bold"), text="COMANDA LED AMARELO",
      fg="black", padx=5, pady=5, bg="#F0F0F0").place(x=150, y=235, anchor="center")
Label(reg_dados_app, font=("Arial", 9), text="(fundo amarelo = confirmado pelo nó)",
      fg="gray", bg="#F0F0F0").place(x=150, y=258, anchor="center")
led_amarelo_estado = ler_estado_led()
btn_led = Button(reg_dados_app, text="", font=("Arial", 12, "bold"),
                 width=20, height=1, cursor="hand2", relief="raised", bd=3,
                 command=toggle_led)
btn_led.place(x=30, y=270)
lbl_feedback_led = Label(reg_dados_app, font=("Arial", 10), text="UL Byte[34]: --",
                         fg="gray", bg="#F0F0F0")
lbl_feedback_led.place(x=150, y=330, anchor="center")

reg_grafico_app = Frame(master=aba_aplicacao, borderwidth=1, relief='sunken')
reg_grafico_app.place(x=320, y=10, width=700, height=720)
style.use("ggplot")
fig_app = Figure(figsize=(8.5, 7.5), facecolor='white')
canvas_app = FigureCanvasTkAgg(fig_app, master=reg_grafico_app)
canvas_app.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

# Botão salvar gráfico Aplicação
btn_save_app = Button(aba_aplicacao, text="💾 Salvar Gráfico Aplicação",
                      font=("Arial", 10, "bold"), bg="#2dc653", fg="white",
                      activebackground="#1fa83e", cursor="hand2", relief="flat",
                      command=lambda: salvar_grafico(fig_app, "grafico_aplicacao"),
                      padx=8, pady=4)
btn_save_app.place(x=320, y=738)

def grafico_aplicacao(f, c):
    f.clear()
    x_medidas = []; y_lum = []
    path_tmp = os.path.join(dir_nivel4, 'dados_aplicacao.tmp')
    if os.path.exists(path_tmp):
        try:
            with open(path_tmp, 'r') as dados:
                for line in dados:
                    colunas = line.strip().split(';')
                    if len(colunas) >= 2 and colunas[0]:
                        x_medidas.append(int(colunas[0]))
                        y_lum.append(int(colunas[1]))
        except Exception:
            pass
    if y_lum:
        str_atual_lum.set(f"{y_lum[-1]}")
    axis = f.add_subplot(111)
    axis.plot(x_medidas, y_lum, label='Luminosidade', color='orange')
    axis.set_ylabel('Luminosidade (0-4095)')
    axis.set_xlabel('Medida')
    axis.set_ylim(0, 4095)
    axis.legend(loc='upper right', fontsize='medium')
    path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    if os.path.exists(path_param):
        try:
            with open(path_param, 'r') as pp:
                st = pp.readline().strip()
            if st == '1':
                status_texto_app.set("EM ANDAMENTO"); label_status_app.config(fg="green")
            else:
                status_texto_app.set("PARADO"); label_status_app.config(fg="red")
        except Exception:
            pass
    fb = ler_feedback_led()
    lbl_feedback_led.config(text=f"UL Byte[34]: {fb}", fg="green" if fb == 1 else "gray")
    atualizar_visual_led()
    f.subplots_adjust(left=0.10, bottom=0.10, right=0.95, top=0.95)
    c.draw()
    janela_principal.after(800, grafico_aplicacao, f, c)

grafico_aplicacao(fig_app, canvas_app)


# =============================================================================
# ABA 2: GERÊNCIA LORA
# =============================================================================
aba_gerencia = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_gerencia, text="  📡 Gerência LoRa  ")

reg_parametrizacao = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_parametrizacao.place(x=10, y=10, width=300, height=380)
Label(reg_parametrizacao, font=("Arial", 14, "bold"), text="Configurações LoRa",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")

def _entry_ger(label, hint, x_lbl, y_lbl, default, w=10):
    Label(reg_parametrizacao, text=label, font=("Arial", 12), bg="#F0F0F0").place(x=20, y=y_lbl)
    if hint:
        Label(reg_parametrizacao, text=hint, font=("Arial", 8), bg="#F0F0F0").place(x=30, y=y_lbl+20)
    e = Entry(reg_parametrizacao, width=w, font=("Arial", 12))
    e.place(x=170, y=y_lbl); e.insert(0, default)
    return e

valor_intervalo        = _entry_ger("Qtde. de Medidas", None, 20, 40, "0")
valor_tempo_tx_rx      = _entry_ger("Tempo de Rádio", "Em segundos", 20, 75, "8")
valor_spreadingfactor  = _entry_ger("Spreading Factor", "7 a 12", 20, 110, "12")
valor_bandwidth        = _entry_ger("Bandwidth", "125, 250, 500 kHz", 20, 145, "125")
valor_codingrate       = _entry_ger("CodingRate", "5 a 8", 20, 180, "8")
valor_potencia_radio   = _entry_ger("Potência de Rádio", "2 a 20 dBm", 20, 215, "20")

status_texto_ger = StringVar(); status_texto_ger.set("AGUARDANDO...")
label_status_ger = Label(reg_parametrizacao, textvariable=status_texto_ger,
                         font=("Arial", 10, "bold"), fg="gray", bg="#F0F0F0")
label_status_ger.place(x=25, y=300)
lss_status_texto = StringVar(); lss_status_texto.set("TESTE LSS PARADO")
Label(reg_parametrizacao, font=("Arial", 12, "bold"), text="STATUS LSS :",
      fg="blue", padx=5, pady=5, bg="#F0F0F0").place(x=20, y=325)
label_lss_status = Label(reg_parametrizacao, textvariable=lss_status_texto,
                         font=("Arial", 12, "bold"), fg="green", padx=5, pady=5, bg="#F0F0F0")
label_lss_status.place(x=20, y=350)

def captura_sf():
    try: return max(7, min(12, int(valor_spreadingfactor.get())))
    except: return 12
def captura_bw():
    try:
        n = int(valor_bandwidth.get())
        return 125 if n < 200 else (250 if n < 350 else 500)
    except: return 125
def captura_cr():
    try: return max(5, min(8, int(valor_codingrate.get())))
    except: return 8
def captura_pt():
    try: return max(2, min(20, int(valor_potencia_radio.get())))
    except: return 20

def grava_comandos(cond):
    arq = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    try:
        with open(arq, 'w') as s:
            for v in [cond,
                      int(valor_intervalo.get()) if valor_intervalo.get() else 10,
                      captura_sf(), captura_bw(), captura_cr(), captura_pt(),
                      int(valor_tempo_tx_rx.get()) if valor_tempo_tx_rx.get() else 8]:
                s.write(str(v) + "\n")
    except Exception as e:
        print(f"[N6] Erro grava_comandos: {e}")

def iniciar_teste():
    # Apaga resultados do N5 antes de iniciar novo teste
    apagar_resultados_n5()
    grava_comandos(1)
    status_texto_ger.set("TESTE EM ANDAMENTO...")
    label_status_ger.config(fg="green")
    print("[N6] Novo teste iniciado – TXTs do N5 apagados.")

btn_iniciar = Button(reg_parametrizacao, text="INICIAR TESTE",
                     font=("Arial", 13, "bold"), width=20, command=iniciar_teste)
btn_iniciar.place(x=25, y=260)

# Desempenho
reg_desempenho = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
reg_desempenho.place(x=10, y=400, width=300, height=340)
Label(reg_desempenho, font=("Arial", 13, "bold"), text="Intensidade do Sinal",
      padx=5, pady=5, bg="#F0F0F0").pack(side=TOP, anchor="n")
Label(reg_desempenho, font=("Arial", 12, "bold"), text="RSSI DOWNLINK",
      fg="blue", padx=5, pady=5, bg="#F0F0F0").place(x=10, y=45, anchor="w")
Label(reg_desempenho, font=("Arial", 12, "bold"), text="RSSI UPLINK",
      fg="green", padx=5, pady=5, bg="#F0F0F0").place(x=10, y=150, anchor="w")

str_atual_dl  = StringVar(); str_atual_dl.set("Atual: -- dBm")
str_max_dl    = StringVar(); str_max_dl.set("Máx: 0 dBm")
str_min_dl    = StringVar(); str_min_dl.set("Mín: 0 dBm")
str_atual_ul  = StringVar(); str_atual_ul.set("Atual: -- dBm")
str_max_ul    = StringVar(); str_max_ul.set("Máx: 0 dBm")
str_min_ul    = StringVar(); str_min_ul.set("Mín: 0 dBm")
str_atual_psr = StringVar(); str_atual_psr.set("Atual: -- %")
str_atual_per = StringVar(); str_atual_per.set("Atual: -- %")
srt_atual_taxa_canal      = StringVar(); srt_atual_taxa_canal.set("-- bps")
srt_atual_taxa_real_canal = StringVar(); srt_atual_taxa_real_canal.set("-- bps")
srt_snr_DL   = StringVar(); srt_snr_DL.set("-- dB")
srt_snr_UL   = StringVar(); srt_snr_UL.set("-- dB")
srt_medida_atual_DL = StringVar(); srt_medida_atual_DL.set("-- Pacotes")
srt_counter_UL      = StringVar(); srt_counter_UL.set("-- Pacotes")
srt_perda_total_UL  = StringVar(); srt_perda_total_UL.set("-- Pacotes")

for _v, _y in [(str_atual_dl,60),(str_max_dl,85),(str_min_dl,110),
               (str_atual_ul,165),(str_max_ul,190),(str_min_ul,215)]:
    Label(reg_desempenho, font=("Arial", 11, "bold"), textvariable=_v,
          padx=5, pady=2, bg="#F0F0F0").place(x=10, y=_y)

# Métricas
frm_metricas = Frame(master=aba_gerencia, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_metricas.place(x=1070, y=10, width=270, height=730)
def _lbl_m(texto, var, cor="blue", y_pos=0):
    Label(frm_metricas, font=("Arial", 12, "bold"), text=texto, fg=cor, bg="#F0F0F0").place(x=10, y=y_pos)
    Label(frm_metricas, font=("Arial", 12, "bold"), textvariable=var, fg="black", bg="#F0F0F0").place(x=10, y=y_pos+22)
_lbl_m("PSR (Geral)",      str_atual_psr,          "blue",  10)
_lbl_m("Taxa Teórica",     srt_atual_taxa_canal,   "blue",  80)
_lbl_m("Taxa Efetiva",     srt_atual_taxa_real_canal,"blue",150)
_lbl_m("SNR Downlink",     srt_snr_DL,             "blue",  220)
_lbl_m("SNR Uplink",       srt_snr_UL,             "green", 290)
_lbl_m("Downlinks",        srt_medida_atual_DL,    "blue",  360)
_lbl_m("Uplinks",          srt_counter_UL,         "green", 430)
_lbl_m("Pacotes Perdidos", srt_perda_total_UL,     "red",   500)
_lbl_m("PER (Geral)",      str_atual_per,          "red",   570)

# Gráfico Gerência
reg_grafico_ger = Frame(master=aba_gerencia, borderwidth=1, relief='sunken')
reg_grafico_ger.place(x=320, y=10, width=740, height=710)
fig_ger = Figure(figsize=(8.5, 7.5), facecolor='white')
canvas_ger = FigureCanvasTkAgg(fig_ger, master=reg_grafico_ger)
canvas_ger.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

# Botão salvar gráfico Gerência
btn_save_ger = Button(aba_gerencia, text="💾 Salvar Gráfico Gerência",
                      font=("Arial", 10, "bold"), bg="#2dc653", fg="white",
                      activebackground="#1fa83e", cursor="hand2", relief="flat",
                      command=lambda: salvar_grafico(fig_ger, "grafico_gerencia"),
                      padx=8, pady=4)
btn_save_ger.place(x=320, y=726)

def grafico_rssi(f, c):
    f.clear()
    x=[]; xUP=[]; z=[]; psr_dl=[]
    ult_max_dl="0"; ult_min_dl="0"; ult_max_ul="0"; ult_min_ul="0"
    taxa_teo="0"; taxa_real="0"; snr_dl="0"; snr_ul="0"
    med_dl="0"; cnt_ul="0"; perda_ul="0"; lss_status="0"

    path_tmp = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
    if os.path.exists(path_tmp):
        try:
            with open(path_tmp, 'r') as dados:
                for line in dados:
                    Y = line.strip().split(';')
                    if len(Y) >= 15 and Y[0]:
                        z.append(int(Y[0]));  x.append(float(Y[1]))
                        psr_dl.append(float(Y[2])); xUP.append(float(Y[4]))
                        med_dl=Y[0]; ult_max_dl=Y[5]; ult_min_dl=Y[6]
                        ult_max_ul=Y[7]; ult_min_ul=Y[8]
                        taxa_teo=Y[13]; taxa_real=Y[14]
                        if len(Y)>15: snr_dl=Y[15]
                        if len(Y)>16: snr_ul=Y[16]
                        if len(Y)>17: cnt_ul=Y[18]
                        if len(Y)>19: perda_ul=Y[19]
                        if len(Y)>20: lss_status=Y[20]
        except Exception:
            pass

    if x:      str_atual_dl.set(f"Atual: {x[-1]} dBm")
    if xUP:    str_atual_ul.set(f"Atual: {xUP[-1]} dBm")
    if psr_dl: str_atual_psr.set(f"Atual: {psr_dl[-1]} %")
    str_max_dl.set("Máx: "+ult_max_dl+" dBm"); str_min_dl.set("Mín: "+ult_min_dl+" dBm")
    str_max_ul.set("Máx: "+ult_max_ul+" dBm"); str_min_ul.set("Mín: "+ult_min_ul+" dBm")
    srt_atual_taxa_canal.set(taxa_teo+" bps"); srt_atual_taxa_real_canal.set(taxa_real+" bps")
    srt_snr_DL.set(snr_dl+" dB"); srt_snr_UL.set(snr_ul+" dB")
    srt_medida_atual_DL.set(med_dl+" Pacotes"); srt_counter_UL.set(cnt_ul+" Pacotes")
    srt_perda_total_UL.set(perda_ul+" Pacotes")
    if psr_dl: str_atual_per.set(f"Atual: {round(100-psr_dl[-1],2)} %")

    for st_code, txt, cor in [("1","LSS EM ANDAMENTO","green"),("2","LSS TESTE ENLACE","green"),
                               ("3","LSS MUDA RÁDIO","blue"),("4","LSS ENLACE PERDIDO","red"),
                               ("0","LSS PARADO","green")]:
        if lss_status == st_code:
            lss_status_texto.set(txt); label_lss_status.config(fg=cor)

    ax1 = f.add_subplot(311); ax1.plot(z, x, label='RSSI DL', color='blue')
    ax1.set_ylabel('RSSI DL (dBm)'); ax1.legend(loc='upper right', fontsize='x-small')
    ax2 = f.add_subplot(312); ax2.plot(z, xUP, label='RSSI UL', color='red')
    ax2.set_ylabel('RSSI UL (dBm)'); ax2.legend(loc='upper right', fontsize='x-small')
    ax3 = f.add_subplot(313); ax3.plot(z, psr_dl, label='PSR (%)', color='green')
    ax3.set_ylabel('PSR (%)'); ax3.set_xlabel('Medida'); ax3.set_ylim(-5, 105)
    ax3.legend(loc='upper right', fontsize='x-small')

    path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
    if os.path.exists(path_param):
        try:
            with open(path_param, 'r') as pp:
                st = pp.readline().strip()
            if st == '0' and status_texto_ger.get() == "TESTE EM ANDAMENTO...":
                status_texto_ger.set("TESTE LSS FINALIZADO"); label_status_ger.config(fg="green")
        except Exception:
            pass

    f.subplots_adjust(left=0.12, bottom=0.20, right=0.95, top=0.95, hspace=0.6)
    c.draw()
    janela_principal.after(REFRESH_MS, grafico_rssi, f, c)

grafico_rssi(fig_ger, canvas_ger)


# =============================================================================
# FUNÇÕES DE COLETA DE PARÂMETROS DOS MODELOS (campos de interface)
# =============================================================================

def coletar_params_todos() -> dict:
    """Coleta todos os parâmetros dos campos de entrada dos modelos."""
    def fv(e, d):
        try: return float(e.get())
        except: return d
    def iv(e, d):
        try: return max(0, int(e.get()))
        except: return d

    d1 = max(0.5, fv(ent_ds_d1, 10.0))
    d2 = max(d1+0.1, fv(ent_ds_d2, 30.0))
    return {
        'd_m':  max(0.1, fv(ent_distancia, 6.0)),
        'pt':   fv(ent_pt, 20.0),
        'sf':   captura_sf(), 'bw': captura_bw(), 'cr': captura_cr(),
        'k1': iv(ent_k1,1), 'lw1': fv(ent_lw1,9.0),
        'k2': iv(ent_k2,1), 'lw2': fv(ent_lw2,4.0),
        'k3': iv(ent_k3,0), 'lw3': fv(ent_lw3,2.0),
        'k4': iv(ent_k4,0), 'lw4': fv(ent_lw4,15.0),
        'nf': iv(ent_nf,0), 'lf':  fv(ent_lf,0.0),
        'lc': fv(ent_lc, 37.0), 'sens': fv(ent_sens, -137.0),
        'ld_n': max(1.0, fv(ent_ld_n, 3.0)),
        'ld_d0': max(0.1, fv(ent_ld_d0, 1.0)),
        'ld_sigma': fv(ent_ld_sigma, 0.0),
        'ds_d0': max(0.1, fv(ent_ds_d0, 1.0)),
        'ds_d1': d1, 'ds_d2': d2,
        'ds_n1': max(1.0, fv(ent_ds_n1, 2.0)),
        'ds_n2': max(1.0, fv(ent_ds_n2, 3.5)),
        'ds_n3': max(1.0, fv(ent_ds_n3, 5.0)),
        'ds_sigma': fv(ent_ds_sigma, 0.0),
    }

def aplicar_e_salvar_params():
    """Grava parametros_modelos.txt e apaga resultados anteriores do N5."""
    p = coletar_params_todos()
    gravar_parametros_modelos(p)
    apagar_resultados_n5()
    print("[N6] Parâmetros gravados e resultados N5 apagados.")
    return p


# =============================================================================
# ABA 3: MULTI-WALL
# =============================================================================
aba_propagacao = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_propagacao, text="  📶 Propagação Multi-Wall  ")

frm_params = Frame(aba_propagacao, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_params.place(x=8, y=8, width=318, height=750)
Label(frm_params, text="Parâmetros COST 231 Multi-Wall",
      font=("Arial", 13, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=10)
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=32, width=295)

Label(frm_params, text="Distância d [m]", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=45)
ent_distancia = Entry(frm_params, width=10, font=("Arial", 12)); ent_distancia.place(x=220, y=45); ent_distancia.insert(0,"6.0")
Label(frm_params, text="Potência TX [dBm]", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=85)
ent_pt = Entry(frm_params, width=10, font=("Arial", 12)); ent_pt.place(x=220, y=85); ent_pt.insert(0,"20")
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=122, width=295)
Label(frm_params, text="Paredes atravessadas", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=130)
Label(frm_params, text="Qtde", font=("Arial", 9, "bold"), bg="#F0F0F0").place(x=220, y=150)
Label(frm_params, text="Aten.[dB]", font=("Arial", 9, "bold"), bg="#F0F0F0").place(x=255, y=150)

def _mw_parede(label, y, k_def, lw_def):
    Label(frm_params, text=label, font=("Arial", 10), bg="#F0F0F0").place(x=10, y=y)
    ek = Entry(frm_params, width=4, font=("Arial", 11)); ek.place(x=220, y=y); ek.insert(0, str(k_def))
    el = Entry(frm_params, width=6, font=("Arial", 11)); el.place(x=258, y=y); el.insert(0, str(lw_def))
    return ek, el

ent_k1,ent_lw1 = _mw_parede("Parede tipo 1 (alvenaria)", 168, 1, 9.0)
ent_k2,ent_lw2 = _mw_parede("Parede tipo 2 (drywall)",   200, 1, 4.0)
ent_k3,ent_lw3 = _mw_parede("Parede tipo 3 (vidro)",     232, 0, 2.0)
ent_k4,ent_lw4 = _mw_parede("Parede tipo 4 (concreto)",  264, 0, 15.0)

Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=298, width=295)
Label(frm_params, text="Pisos atravessados", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=306)
Label(frm_params, text="Nº de pisos (n_f)", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=328)
ent_nf = Entry(frm_params, width=6, font=("Arial", 11)); ent_nf.place(x=220, y=328); ent_nf.insert(0,"0")
Label(frm_params, text="Aten. por piso (L_f) [dB]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=356)
ent_lf = Entry(frm_params, width=6, font=("Arial", 11)); ent_lf.place(x=220, y=356); ent_lf.insert(0,"0.0")
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=390, width=295)
Label(frm_params, text="Constante indoor L_c [dB]", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=398)
ent_lc = Entry(frm_params, width=6, font=("Arial", 11)); ent_lc.place(x=220, y=398); ent_lc.insert(0,"37.0")
Label(frm_params, text="Sensibilidade RX [dBm]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=438)
ent_sens = Entry(frm_params, width=8, font=("Arial", 11)); ent_sens.place(x=220, y=438); ent_sens.insert(0,"-137.0")
Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=476, width=295)

str_c231_pl_modelo = StringVar(); str_c231_pl_modelo.set("PL modelo : -- dB")
str_c231_pl_dl     = StringVar(); str_c231_pl_dl.set("PL medido DL: -- dB")
str_c231_pl_ul     = StringVar(); str_c231_pl_ul.set("PL medido UL: -- dB")
str_c231_margem    = StringVar(); str_c231_margem.set("Margem pior: -- dB")
str_c231_dmax      = StringVar(); str_c231_dmax.set("d_max modelo: -- m")
str_c231_waf_tot   = StringVar(); str_c231_waf_tot.set("WAF+FAF total: -- dB")
str_c231_qualidade = StringVar(); str_c231_qualidade.set("Qualidade: --")
lbl_c231_status    = Label(frm_params, text="Aguardando Nível 5...",
                           font=("Arial", 9), fg="gray", bg="#F0F0F0", wraplength=290)
lbl_c231_status.place(x=10, y=710)

def aplicar_parametros_c231():
    aplicar_e_salvar_params()
    lbl_c231_status.config(text="Parâmetros aplicados – aguardando N5...", fg="blue")

btn_aplicar_mw = Button(frm_params, text="▶  APLICAR PARÂMETROS",
                        font=("Arial", 12, "bold"), bg="#185FA5", fg="white",
                        activebackground="#0C447C", cursor="hand2", relief="flat",
                        command=aplicar_parametros_c231, padx=8, pady=5)
btn_aplicar_mw.place(x=10, y=485, width=294)

Frame(frm_params, bg="#AAAAAA", height=1).place(x=10, y=520, width=295)
Label(frm_params, text="Resultados (via Nível 5)", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=528)
for _v, _y, _c in [(str_c231_pl_modelo,548,"#185FA5"),(str_c231_pl_dl,566,"#3B6D11"),
                   (str_c231_pl_ul,584,"#993C1D"),(str_c231_margem,602,"#854F0B"),
                   (str_c231_dmax,620,"#533"),(str_c231_waf_tot,638,"#555")]:
    Label(frm_params, textvariable=_v, font=("Arial", 10, "bold"), fg=_c, bg="#F0F0F0").place(x=14, y=_y)
lbl_c231_qualidade = Label(frm_params, textvariable=str_c231_qualidade,
                           font=("Arial", 13, "bold"), fg="gray", bg="#F0F0F0")
lbl_c231_qualidade.place(x=14, y=660)

frm_graf_c231 = Frame(aba_propagacao, borderwidth=1, relief='sunken')
frm_graf_c231.place(x=334, y=8, width=1000, height=730)
fig_c231 = Figure(facecolor='white')
canvas_c231 = FigureCanvasTkAgg(fig_c231, master=frm_graf_c231)
canvas_c231.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

# Botão salvar gráfico Multi-Wall
btn_save_mw = Button(aba_propagacao, text="💾 Salvar Gráfico Multi-Wall",
                     font=("Arial", 10, "bold"), bg="#2dc653", fg="white",
                     activebackground="#1fa83e", cursor="hand2", relief="flat",
                     command=lambda: salvar_grafico(fig_c231, "grafico_multiwall"),
                     padx=8, pady=4)
btn_save_mw.place(x=334, y=743)

def atualizar_grafico_c231(fig, canvas):
    linhas = ler_resultado_txt(OUT_MULTIWALL)
    p = coletar_params_todos()

    if linhas:
        ult = linhas[-1]
        # Campos: medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;pl_minimo;
        #         margem_dl;margem_ul;dmax;waf;faf;lc;qualidade
        try:
            pl_mod = float(ult[6]); pl_min = float(ult[7])
            mg_dl  = float(ult[8]); mg_ul  = float(ult[9])
            dmax   = float(ult[10]); waf   = float(ult[11])
            faf    = float(ult[12]); lc    = float(ult[13])
            qual   = ult[14] if len(ult)>14 else "--"
            pl_dl_v= float(ult[4]); pl_ul_v= float(ult[5])
            str_c231_pl_modelo.set(f"PL modelo : {pl_mod:.1f} dB")
            str_c231_pl_dl.set(    f"PL medido DL: {pl_dl_v:.1f} dB")
            str_c231_pl_ul.set(    f"PL medido UL: {pl_ul_v:.1f} dB")
            str_c231_margem.set(   f"Margem pior: {min(mg_dl,mg_ul):.1f} dB")
            str_c231_dmax.set(     f"d_max modelo: {dmax:.1f} m")
            str_c231_waf_tot.set(  f"WAF={waf:.1f}  FAF={faf:.1f}  L_c={lc:.1f} dB")
            str_c231_qualidade.set(qual)
            lbl_c231_qualidade.config(fg=cor_qualidade(qual))
            lbl_c231_status.config(text=f"Med.{ult[0]} | RSSI_DL={ult[1]} | RSSI_UL={ult[2]} dBm", fg="green")
        except Exception:
            pass

    fig.clear(); fig.patch.set_facecolor('white')
    xs=[]; pl_dl=[]; pl_ul=[]; pl_mod=[]; pl_min=[]
    mg_dl=[]; mg_ul=[]
    for ln in linhas:
        try:
            xs.append(int(ln[0])); pl_dl.append(float(ln[4])); pl_ul.append(float(ln[5]))
            pl_mod.append(float(ln[6])); pl_min.append(float(ln[7]))
            mg_dl.append(float(ln[8])); mg_ul.append(float(ln[9]))
        except Exception:
            continue

    if len(xs) < 2:
        ax = fig.add_subplot(111); ax.set_facecolor('#F8F8F8')
        ax.text(0.5, 0.5, 'Aguardando dados do Nível 5...', ha='center', va='center',
                fontsize=13, color='#888888', transform=ax.transAxes); ax.set_axis_off()
        canvas.draw()
        janela_principal.after(REFRESH_MS, atualizar_grafico_c231, fig, canvas); return

    ax1 = fig.add_subplot(311); ax1.set_facecolor('#F8F8F8')
    ax1.plot(xs, pl_dl,  color='#1565C0', lw=1.6, label='PL medido DL')
    ax1.plot(xs, pl_ul,  color='#B71C1C', lw=1.6, label='PL medido UL')
    ax1.plot(xs, pl_mod, color='#2E7D32', lw=2.0, linestyle='--', label='PL COST231 modelo')
    ax1.plot(xs, pl_min, color='#888888', lw=1.0, linestyle=':', label='PL mín (livre+Lc)')
    ax1.fill_between(xs,[v-3 for v in pl_mod],[v+3 for v in pl_mod],color='#2E7D32',alpha=0.10,label='±3 dB')
    ax1.set_ylabel('Path Loss [dB]', fontsize=9)
    ax1.set_title('Path Loss – COST 231 Multi-Wall @ 915 MHz', fontsize=10, fontweight='bold')
    ax1.legend(loc='upper right', fontsize='x-small', ncol=2); ax1.grid(True, linestyle=':', alpha=0.5)

    ax2 = fig.add_subplot(312); ax2.set_facecolor('#F8F8F8')
    ax2.plot(xs, mg_dl, color='#1565C0', lw=1.5, label='Margem DL')
    ax2.plot(xs, mg_ul, color='#B71C1C', lw=1.5, label='Margem UL')
    for yh, lbl_h, cor_h in [(30,'Excelente','#2E7D32'),(20,'Bom','#F9A825'),(10,'Regular','#E65100'),(0,'Crítico','#B71C1C')]:
        ax2.axhline(y=yh, color=cor_h, lw=0.8, linestyle='--', label=f'{lbl_h} ({yh} dB)')
    ax2.fill_between(xs,mg_dl,0,where=[v>=0 for v in mg_dl],color='#1565C0',alpha=0.08)
    ax2.fill_between(xs,mg_ul,0,where=[v>=0 for v in mg_ul],color='#B71C1C',alpha=0.08)
    ax2.set_ylabel('Margem [dB]', fontsize=9)
    ax2.set_title('Margem de enlace (Link Budget – PL medido)', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize='x-small', ncol=3); ax2.grid(True, linestyle=':', alpha=0.5)

    ax3 = fig.add_subplot(313); ax3.set_facecolor('#F8F8F8')
    d_range = [0.5+i*0.5 for i in range(200)]
    ax3.plot(d_range, [mw_pl_curva(d,p) for d in d_range], color='#2E7D32', lw=2.0, label='COST231 Multi-Wall')
    ax3.plot(d_range, [mw_pl_curva(d,{**p,'k1':0,'k2':0,'k3':0,'k4':0,'nf':0}) for d in d_range],
             color='#888888', lw=1.2, linestyle=':', label='Espaço livre + Lc')
    ax3.axhline(y=p['pt']-p['sens'], color='#B71C1C', lw=1.2, linestyle='--',
                label=f'Link budget ({p["pt"]:.0f} – {p["sens"]:.0f} dBm)')
    ax3.scatter([p['d_m']], [mw_pl_curva(p['d_m'],p)], color='#1565C0', s=40, zorder=5,
                label=f"d={p['d_m']:.1f}m")
    if pl_dl: ax3.scatter([p['d_m']], [pl_dl[-1]], marker='D', color='#1565C0', s=35, zorder=6, label=f"PL_DL={pl_dl[-1]:.1f}")
    if pl_ul: ax3.scatter([p['d_m']], [pl_ul[-1]], marker='D', color='#B71C1C', s=35, zorder=6, label=f"PL_UL={pl_ul[-1]:.1f}")
    ax3.set_xlabel('Distância [m]', fontsize=9); ax3.set_ylabel('Path Loss [dB]', fontsize=9)
    ax3.set_title('Curva PL × d – COST 231', fontsize=10, fontweight='bold')
    ax3.legend(loc='lower right', fontsize='x-small', ncol=2); ax3.set_xlim(0,105); ax3.grid(True, linestyle=':', alpha=0.5)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.08, hspace=0.52)
    canvas.draw()
    janela_principal.after(REFRESH_MS, atualizar_grafico_c231, fig, canvas)

atualizar_grafico_c231(fig_c231, canvas_c231)


# =============================================================================
# ABA 4: LOG-DISTANCE PATH LOSS
# =============================================================================
aba_logdist = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_logdist, text="  📉 Log-Distance PL  ")

frm_ld_params = Frame(aba_logdist, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_ld_params.place(x=8, y=8, width=318, height=750)
Label(frm_ld_params, text="Log-Distance Path Loss",
      font=("Arial", 13, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=10)
Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=32, width=295)
Label(frm_ld_params, text="Parâmetros do Modelo", font=("Arial", 11, "bold"),
      bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=40)

Label(frm_ld_params, text="Expoente PL  n", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=65)
Label(frm_ld_params, text="Espaço livre=2 / Indoor≈3-4", font=("Arial", 8), fg="#888", bg="#F0F0F0").place(x=10, y=82)
ent_ld_n = Entry(frm_ld_params, width=8, font=("Arial", 12)); ent_ld_n.place(x=210, y=65); ent_ld_n.insert(0,"3.0")
Label(frm_ld_params, text="Distância ref. d₀ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=100)
ent_ld_d0 = Entry(frm_ld_params, width=8, font=("Arial", 12)); ent_ld_d0.place(x=210, y=100); ent_ld_d0.insert(0,"1.0")
Label(frm_ld_params, text="Desvio Shadowing σ [dB]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=135)
ent_ld_sigma = Entry(frm_ld_params, width=8, font=("Arial", 12)); ent_ld_sigma.place(x=210, y=135); ent_ld_sigma.insert(0,"0.0")
Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=170, width=295)
Label(frm_ld_params, text="Parâmetros lidos da aba Multi-Wall / Gerência",
      font=("Arial", 9, "bold"), fg="#444", bg="#F0F0F0").place(x=10, y=178)
str_ld_mirror_d    = StringVar(); str_ld_mirror_d.set("d = -- m")
str_ld_mirror_pt   = StringVar(); str_ld_mirror_pt.set("Pt = -- dBm")
str_ld_mirror_sf   = StringVar(); str_ld_mirror_sf.set("SF=--  BW=-- kHz")
str_ld_mirror_sens = StringVar(); str_ld_mirror_sens.set("Sens. estimada = -- dBm")
for _v, _y, _c in [(str_ld_mirror_d,198,"#185FA5"),(str_ld_mirror_pt,216,"#185FA5"),
                   (str_ld_mirror_sf,234,"#2E7D32"),(str_ld_mirror_sens,252,"#993C1D")]:
    Label(frm_ld_params, textvariable=_v, font=("Arial", 10), fg=_c, bg="#F0F0F0").place(x=14, y=_y)
Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=270, width=295)

str_ld_pl_modelo = StringVar(); str_ld_pl_modelo.set("PL modelo : -- dB")
str_ld_pl_dl     = StringVar(); str_ld_pl_dl.set("PL medido DL: -- dB")
str_ld_pl_ul     = StringVar(); str_ld_pl_ul.set("PL medido UL: -- dB")
str_ld_margem    = StringVar(); str_ld_margem.set("Margem pior: -- dB")
str_ld_dmax      = StringVar(); str_ld_dmax.set("d_max modelo: -- m")
str_ld_qualidade = StringVar(); str_ld_qualidade.set("Qualidade: --")
lbl_ld_status    = Label(frm_ld_params, text="Aguardando Nível 5...",
                         font=("Arial", 9), fg="gray", bg="#F0F0F0", wraplength=290)
lbl_ld_status.place(x=10, y=710)

def aplicar_parametros_ld():
    aplicar_e_salvar_params()
    lbl_ld_status.config(text="Parâmetros aplicados – aguardando N5...", fg="blue")

btn_ld_aplicar = Button(frm_ld_params, text="▶  APLICAR PARÂMETROS",
                        font=("Arial", 12, "bold"), bg="#185FA5", fg="white",
                        activebackground="#0C447C", cursor="hand2", relief="flat",
                        command=aplicar_parametros_ld, padx=8, pady=5)
btn_ld_aplicar.place(x=10, y=280, width=294)

Frame(frm_ld_params, bg="#AAAAAA", height=1).place(x=10, y=320, width=295)
Label(frm_ld_params, text="Resultados (via Nível 5)", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=328)
for _v, _y, _c in [(str_ld_pl_modelo,348,"#185FA5"),(str_ld_pl_dl,366,"#3B6D11"),
                   (str_ld_pl_ul,384,"#993C1D"),(str_ld_margem,402,"#854F0B"),(str_ld_dmax,420,"#533")]:
    Label(frm_ld_params, textvariable=_v, font=("Arial", 10, "bold"), fg=_c, bg="#F0F0F0").place(x=14, y=_y)
lbl_ld_qualidade = Label(frm_ld_params, textvariable=str_ld_qualidade,
                          font=("Arial", 13, "bold"), fg="gray", bg="#F0F0F0")
lbl_ld_qualidade.place(x=14, y=448)

frm_ld_graf = Frame(aba_logdist, borderwidth=1, relief='sunken')
frm_ld_graf.place(x=334, y=8, width=1000, height=730)
fig_ld    = Figure(facecolor='white')
canvas_ld = FigureCanvasTkAgg(fig_ld, master=frm_ld_graf)
canvas_ld.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

btn_save_ld = Button(aba_logdist, text="💾 Salvar Gráfico Log-Distance",
                     font=("Arial", 10, "bold"), bg="#2dc653", fg="white",
                     activebackground="#1fa83e", cursor="hand2", relief="flat",
                     command=lambda: salvar_grafico(fig_ld, "grafico_logdistance"),
                     padx=8, pady=4)
btn_save_ld.place(x=334, y=743)

def ld_atualizar_grafico(fig, canvas):
    linhas = ler_resultado_txt(OUT_LOGDISTANCE)
    p = coletar_params_todos()
    sens = -174 + 10*math.log10(p['bw']*1e3) + 6 + {7:-7.5,8:-10.0,9:-12.5,10:-15.0,11:-17.5,12:-20.0}.get(p['sf'],-20.0)

    str_ld_mirror_d.set(f"d = {p['d_m']:.1f} m")
    str_ld_mirror_pt.set(f"Pt = {p['pt']:.0f} dBm")
    str_ld_mirror_sf.set(f"SF={p['sf']}  BW={p['bw']} kHz  CR=4/{p['cr']}")
    str_ld_mirror_sens.set(f"Sens. estimada = {sens:.1f} dBm")

    if linhas:
        ult = linhas[-1]
        # Campos: medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;
        #         margem_dl;margem_ul;dmax;sens;n;d0;sigma;qualidade
        try:
            str_ld_pl_modelo.set(f"PL modelo : {float(ult[6]):.1f} dB")
            str_ld_pl_dl.set(    f"PL medido DL: {float(ult[4]):.1f} dB")
            str_ld_pl_ul.set(    f"PL medido UL: {float(ult[5]):.1f} dB")
            str_ld_margem.set(   f"Margem pior: {min(float(ult[7]),float(ult[8])):.1f} dB")
            str_ld_dmax.set(     f"d_max modelo: {float(ult[9]):.1f} m")
            qual = ult[14] if len(ult)>14 else "--"
            str_ld_qualidade.set(qual); lbl_ld_qualidade.config(fg=cor_qualidade(qual))
            lbl_ld_status.config(text=f"Med.{ult[0]} | n={ult[11]} | d₀={ult[12]} m | σ={ult[13]} dB", fg="green")
        except Exception:
            pass

    fig.clear(); fig.patch.set_facecolor('white')
    xs=[]; pl_dl=[]; pl_ul=[]; pl_mod=[]; mg_dl=[]; mg_ul=[]
    for ln in linhas:
        try:
            xs.append(int(ln[0])); pl_dl.append(float(ln[4])); pl_ul.append(float(ln[5]))
            pl_mod.append(float(ln[6])); mg_dl.append(float(ln[7])); mg_ul.append(float(ln[8]))
        except Exception:
            continue

    if len(xs) < 2:
        ax = fig.add_subplot(111); ax.set_facecolor('#F8F8F8')
        ax.text(0.5, 0.5, 'Aguardando dados do Nível 5...', ha='center', va='center',
                fontsize=13, color='#888888', transform=ax.transAxes); ax.set_axis_off()
        canvas.draw(); janela_principal.after(REFRESH_MS, ld_atualizar_grafico, fig, canvas); return

    ax1 = fig.add_subplot(311); ax1.set_facecolor('#F8F8F8')
    ax1.plot(xs, pl_dl,  color='#1565C0', lw=1.6, label='PL medido DL')
    ax1.plot(xs, pl_ul,  color='#B71C1C', lw=1.6, label='PL medido UL')
    ax1.plot(xs, pl_mod, color='#6A0DAD', lw=2.0, linestyle='--', label=f'Log-Distance n={p["ld_n"]:.1f}')
    if p['ld_sigma'] > 0:
        ax1.fill_between(xs,[v-p['ld_sigma'] for v in pl_mod],[v+p['ld_sigma'] for v in pl_mod],
                         color='#6A0DAD',alpha=0.12,label=f'±σ={p["ld_sigma"]:.1f} dB')
    ax1.set_ylabel('Path Loss [dB]', fontsize=9)
    ax1.set_title(f'Path Loss – Log-Distance (n={p["ld_n"]:.1f}, d₀={p["ld_d0"]:.1f} m) @ 915 MHz',
                  fontsize=10, fontweight='bold')
    ax1.legend(loc='upper right', fontsize='x-small', ncol=2); ax1.grid(True,linestyle=':',alpha=0.5)

    ax2 = fig.add_subplot(312); ax2.set_facecolor('#F8F8F8')
    ax2.plot(xs, mg_dl, color='#1565C0', lw=1.5, label='Margem DL')
    ax2.plot(xs, mg_ul, color='#B71C1C', lw=1.5, label='Margem UL')
    for yh,lbl_h,cor_h in [(30,'Excelente','#2E7D32'),(20,'Bom','#F9A825'),(10,'Regular','#E65100'),(0,'Crítico','#B71C1C')]:
        ax2.axhline(y=yh, color=cor_h, lw=0.8, linestyle='--', label=f'{lbl_h} ({yh} dB)')
    ax2.fill_between(xs,mg_dl,0,where=[v>=0 for v in mg_dl],color='#1565C0',alpha=0.08)
    ax2.fill_between(xs,mg_ul,0,where=[v>=0 for v in mg_ul],color='#B71C1C',alpha=0.08)
    ax2.set_ylabel('Margem [dB]', fontsize=9); ax2.set_title('Margem de enlace', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize='x-small', ncol=3); ax2.grid(True,linestyle=':',alpha=0.5)

    ax3 = fig.add_subplot(313); ax3.set_facecolor('#F8F8F8')
    d_range = [0.5+i*0.5 for i in range(200)]
    ax3.plot(d_range, [ld_pl_curva(d,p) for d in d_range], color='#6A0DAD', lw=2.0,
             label=f'Log-Distance n={p["ld_n"]:.1f}')
    ax3.plot(d_range, [pl_espaco_livre(d) for d in d_range], color='#888888', lw=1.2, linestyle=':', label='Espaço livre')
    ax3.axhline(y=p['pt']-sens, color='#B71C1C', lw=1.2, linestyle='--',
                label=f'Link budget ({p["pt"]:.0f} – {sens:.0f} dBm)')
    if p['ld_sigma'] > 0:
        pl_cv = [ld_pl_curva(d,p) for d in d_range]
        ax3.fill_between(d_range,[v-p['ld_sigma'] for v in pl_cv],[v+p['ld_sigma'] for v in pl_cv],
                         color='#6A0DAD',alpha=0.12,label=f'±σ={p["ld_sigma"]:.1f} dB')
    ax3.scatter([p['d_m']],[ld_pl_curva(p['d_m'],p)],color='#1565C0',s=40,zorder=5,label=f"d={p['d_m']:.1f}m")
    if pl_dl: ax3.scatter([p['d_m']],[pl_dl[-1]],marker='D',color='#1565C0',s=35,zorder=6,label=f"PL_DL={pl_dl[-1]:.1f}")
    if pl_ul: ax3.scatter([p['d_m']],[pl_ul[-1]],marker='D',color='#B71C1C',s=35,zorder=6,label=f"PL_UL={pl_ul[-1]:.1f}")
    ax3.set_xlabel('Distância [m]', fontsize=9); ax3.set_ylabel('Path Loss [dB]', fontsize=9)
    ax3.set_title(f'Curva PL × d – Log-Distance', fontsize=10, fontweight='bold')
    ax3.legend(loc='lower right', fontsize='x-small', ncol=2); ax3.set_xlim(0,105); ax3.grid(True,linestyle=':',alpha=0.5)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.08, hspace=0.52)
    canvas.draw()
    janela_principal.after(REFRESH_MS, ld_atualizar_grafico, fig, canvas)

ld_atualizar_grafico(fig_ld, canvas_ld)


# =============================================================================
# ABA 5: DUAL-SLOPE PATH LOSS
# =============================================================================
aba_dualslope = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_dualslope, text="  📊 Dual-Slope PL  ")

frm_ds_params = Frame(aba_dualslope, borderwidth=1, relief='sunken', bg="#F0F0F0")
frm_ds_params.place(x=8, y=8, width=318, height=750)
Label(frm_ds_params, text="Dual-Slope Path Loss",
      font=("Arial", 13, "bold"), bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=10)
Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=32, width=295)
Label(frm_ds_params, text="Parâmetros do Modelo", font=("Arial", 11, "bold"),
      bg="#F0F0F0", fg="#1a1a2e").place(x=10, y=40)

Label(frm_ds_params, text="Distância ref. d₀ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=62)
ent_ds_d0 = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_d0.place(x=210, y=62); ent_ds_d0.insert(0,"1.0")

Frame(frm_ds_params, bg="#CCAAFF", height=1).place(x=10, y=98, width=295)
Label(frm_ds_params, text="Região 1  (d ≤ d₁)", font=("Arial", 10, "bold"),
      fg="#6A0DAD", bg="#F0F0F0").place(x=10, y=104)
Label(frm_ds_params, text="Breakpoint d₁ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=124)
ent_ds_d1 = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_d1.place(x=210, y=124); ent_ds_d1.insert(0,"10.0")
Label(frm_ds_params, text="Expoente n₁", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=152)
ent_ds_n1 = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_n1.place(x=210, y=152); ent_ds_n1.insert(0,"2.0")

Frame(frm_ds_params, bg="#AACCFF", height=1).place(x=10, y=180, width=295)
Label(frm_ds_params, text="Região 2  (d₁ < d ≤ d₂)", font=("Arial", 10, "bold"),
      fg="#1565C0", bg="#F0F0F0").place(x=10, y=186)
Label(frm_ds_params, text="Breakpoint d₂ [m]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=206)
ent_ds_d2 = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_d2.place(x=210, y=206); ent_ds_d2.insert(0,"30.0")
Label(frm_ds_params, text="Expoente n₂", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=234)
ent_ds_n2 = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_n2.place(x=210, y=234); ent_ds_n2.insert(0,"3.5")

Frame(frm_ds_params, bg="#AAFFCC", height=1).place(x=10, y=262, width=295)
Label(frm_ds_params, text="Região 3  (d > d₂)", font=("Arial", 10, "bold"),
      fg="#2E7D32", bg="#F0F0F0").place(x=10, y=268)
Label(frm_ds_params, text="Expoente n₃", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=288)
ent_ds_n3 = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_n3.place(x=210, y=288); ent_ds_n3.insert(0,"5.0")

Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=314, width=295)
Label(frm_ds_params, text="Desvio Shadowing σ [dB]", font=("Arial", 10), bg="#F0F0F0").place(x=10, y=322)
ent_ds_sigma = Entry(frm_ds_params, width=8, font=("Arial", 12)); ent_ds_sigma.place(x=210, y=322); ent_ds_sigma.insert(0,"0.0")

Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=348, width=295)
Label(frm_ds_params, text="Parâmetros lidos automaticamente",
      font=("Arial", 9, "bold"), fg="#444", bg="#F0F0F0").place(x=10, y=356)
str_ds_mirror_d    = StringVar(); str_ds_mirror_d.set("d = -- m")
str_ds_mirror_pt   = StringVar(); str_ds_mirror_pt.set("Pt = -- dBm")
str_ds_mirror_sf   = StringVar(); str_ds_mirror_sf.set("SF=--  BW=-- kHz")
str_ds_mirror_sens = StringVar(); str_ds_mirror_sens.set("Sens. estimada = -- dBm")
for _v, _y, _c in [(str_ds_mirror_d,374,"#185FA5"),(str_ds_mirror_pt,392,"#185FA5"),
                   (str_ds_mirror_sf,410,"#2E7D32"),(str_ds_mirror_sens,428,"#993C1D")]:
    Label(frm_ds_params, textvariable=_v, font=("Arial", 10), fg=_c, bg="#F0F0F0").place(x=14, y=_y)

Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=450, width=295)

str_ds_pl_modelo = StringVar(); str_ds_pl_modelo.set("PL modelo : -- dB")
str_ds_pl_dl     = StringVar(); str_ds_pl_dl.set("PL medido DL: -- dB")
str_ds_pl_ul     = StringVar(); str_ds_pl_ul.set("PL medido UL: -- dB")
str_ds_margem    = StringVar(); str_ds_margem.set("Margem pior: -- dB")
str_ds_dmax      = StringVar(); str_ds_dmax.set("d_max modelo: -- m")
str_ds_regime    = StringVar(); str_ds_regime.set("Regime: --")
str_ds_qualidade = StringVar(); str_ds_qualidade.set("Qualidade: --")
lbl_ds_status    = Label(frm_ds_params, text="Aguardando Nível 5...",
                         font=("Arial", 9), fg="gray", bg="#F0F0F0", wraplength=290)
lbl_ds_status.place(x=10, y=714)

def aplicar_parametros_ds():
    aplicar_e_salvar_params()
    lbl_ds_status.config(text="Parâmetros aplicados – aguardando N5...", fg="blue")

btn_ds_aplicar = Button(frm_ds_params, text="▶  APLICAR PARÂMETROS",
                        font=("Arial", 12, "bold"), bg="#185FA5", fg="white",
                        activebackground="#0C447C", cursor="hand2", relief="flat",
                        command=aplicar_parametros_ds, padx=8, pady=5)
btn_ds_aplicar.place(x=10, y=458, width=294)

Frame(frm_ds_params, bg="#AAAAAA", height=1).place(x=10, y=496, width=295)
Label(frm_ds_params, text="Resultados (via Nível 5)", font=("Arial", 11, "bold"), bg="#F0F0F0").place(x=10, y=504)
for _v, _y, _c in [(str_ds_pl_modelo,524,"#185FA5"),(str_ds_pl_dl,542,"#3B6D11"),
                   (str_ds_pl_ul,560,"#993C1D"),(str_ds_margem,578,"#854F0B"),
                   (str_ds_dmax,596,"#533"),(str_ds_regime,614,"#6A0DAD")]:
    Label(frm_ds_params, textvariable=_v, font=("Arial", 10, "bold"), fg=_c, bg="#F0F0F0").place(x=14, y=_y)
lbl_ds_qualidade = Label(frm_ds_params, textvariable=str_ds_qualidade,
                          font=("Arial", 12, "bold"), fg="gray", bg="#F0F0F0")
lbl_ds_qualidade.place(x=14, y=638)

frm_ds_graf = Frame(aba_dualslope, borderwidth=1, relief='sunken')
frm_ds_graf.place(x=334, y=8, width=1000, height=730)
fig_ds    = Figure(facecolor='white')
canvas_ds = FigureCanvasTkAgg(fig_ds, master=frm_ds_graf)
canvas_ds.get_tk_widget().pack(side=TOP, fill=BOTH, expand=True)

btn_save_ds = Button(aba_dualslope, text="💾 Salvar Gráfico Dual-Slope",
                     font=("Arial", 10, "bold"), bg="#2dc653", fg="white",
                     activebackground="#1fa83e", cursor="hand2", relief="flat",
                     command=lambda: salvar_grafico(fig_ds, "grafico_dualslope"),
                     padx=8, pady=4)
btn_save_ds.place(x=334, y=743)

def ds_atualizar_grafico(fig, canvas):
    linhas = ler_resultado_txt(OUT_DUALSLOPE)
    p = coletar_params_todos()
    sens = -174 + 10*math.log10(p['bw']*1e3) + 6 + {7:-7.5,8:-10.0,9:-12.5,10:-15.0,11:-17.5,12:-20.0}.get(p['sf'],-20.0)

    str_ds_mirror_d.set(f"d = {p['d_m']:.1f} m  (aba Multi-Wall)")
    str_ds_mirror_pt.set(f"Pt = {p['pt']:.0f} dBm  (aba Multi-Wall)")
    str_ds_mirror_sf.set(f"SF={p['sf']}  BW={p['bw']} kHz  CR=4/{p['cr']}")
    str_ds_mirror_sens.set(f"Sens. estimada = {sens:.1f} dBm")

    if linhas:
        ult = linhas[-1]
        # Campos: medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;
        #         margem_dl;margem_ul;dmax;sens;n1;n2;n3;d1;d2;regime;qualidade
        try:
            str_ds_pl_modelo.set(f"PL modelo : {float(ult[6]):.1f} dB")
            str_ds_pl_dl.set(    f"PL medido DL: {float(ult[4]):.1f} dB")
            str_ds_pl_ul.set(    f"PL medido UL: {float(ult[5]):.1f} dB")
            mg_p = min(float(ult[7]), float(ult[8]))
            str_ds_margem.set(   f"Margem pior: {mg_p:.1f} dB")
            str_ds_dmax.set(     f"d_max modelo: {float(ult[9]):.1f} m")
            str_ds_regime.set(ult[16] if len(ult)>16 else "--")
            qual = ult[17] if len(ult)>17 else "--"
            str_ds_qualidade.set(qual); lbl_ds_qualidade.config(fg=cor_qualidade(qual))
            lbl_ds_status.config(
                text=(f"Med.{ult[0]} | d₁={ult[14]}m d₂={ult[15]}m | "
                      f"n₁={ult[11]} n₂={ult[12]} n₃={ult[13]}"), fg="green")
        except Exception:
            pass

    fig.clear(); fig.patch.set_facecolor('white')
    xs=[]; pl_dl=[]; pl_ul=[]; pl_mod=[]; mg_dl=[]; mg_ul=[]
    for ln in linhas:
        try:
            xs.append(int(ln[0])); pl_dl.append(float(ln[4])); pl_ul.append(float(ln[5]))
            pl_mod.append(float(ln[6])); mg_dl.append(float(ln[7])); mg_ul.append(float(ln[8]))
        except Exception:
            continue

    if len(xs) < 2:
        ax = fig.add_subplot(111); ax.set_facecolor('#F8F8F8')
        ax.text(0.5, 0.5, 'Aguardando dados do Nível 5...', ha='center', va='center',
                fontsize=13, color='#888888', transform=ax.transAxes); ax.set_axis_off()
        canvas.draw(); janela_principal.after(REFRESH_MS, ds_atualizar_grafico, fig, canvas); return

    ax1 = fig.add_subplot(311); ax1.set_facecolor('#F8F8F8')
    ax1.plot(xs, pl_dl,  color='#1565C0', lw=1.6, label='PL medido DL')
    ax1.plot(xs, pl_ul,  color='#B71C1C', lw=1.6, label='PL medido UL')
    ax1.plot(xs, pl_mod, color='#E65100', lw=2.0, linestyle='--', label='Dual-Slope modelo')
    if p['ds_sigma'] > 0:
        ax1.fill_between(xs,[v-p['ds_sigma'] for v in pl_mod],[v+p['ds_sigma'] for v in pl_mod],
                         color='#E65100',alpha=0.12,label=f'±σ={p["ds_sigma"]:.1f} dB')
    ax1.set_ylabel('Path Loss [dB]', fontsize=9)
    ax1.set_title(f'Path Loss – Dual-Slope (d₁={p["ds_d1"]:.0f} m, d₂={p["ds_d2"]:.0f} m) @ 915 MHz',
                  fontsize=10, fontweight='bold')
    ax1.legend(loc='upper right', fontsize='x-small', ncol=2); ax1.grid(True,linestyle=':',alpha=0.5)

    ax2 = fig.add_subplot(312); ax2.set_facecolor('#F8F8F8')
    ax2.plot(xs, mg_dl, color='#1565C0', lw=1.5, label='Margem DL')
    ax2.plot(xs, mg_ul, color='#B71C1C', lw=1.5, label='Margem UL')
    for yh,lbl_h,cor_h in [(30,'Excelente','#2E7D32'),(20,'Bom','#F9A825'),(10,'Regular','#E65100'),(0,'Crítico','#B71C1C')]:
        ax2.axhline(y=yh, color=cor_h, lw=0.8, linestyle='--', label=f'{lbl_h} ({yh} dB)')
    ax2.fill_between(xs,mg_dl,0,where=[v>=0 for v in mg_dl],color='#1565C0',alpha=0.08)
    ax2.fill_between(xs,mg_ul,0,where=[v>=0 for v in mg_ul],color='#B71C1C',alpha=0.08)
    ax2.set_ylabel('Margem [dB]', fontsize=9); ax2.set_title('Margem de enlace', fontsize=10, fontweight='bold')
    ax2.legend(loc='upper right', fontsize='x-small', ncol=3); ax2.grid(True,linestyle=':',alpha=0.5)

    ax3 = fig.add_subplot(313); ax3.set_facecolor('#F8F8F8')
    d_range = [0.1+i*0.5 for i in range(200)]
    d1, d2 = p['ds_d1'], p['ds_d2']
    dr_r1 = [d for d in d_range if d<=d1]; dr_r2 = [d for d in d_range if d1<d<=d2]; dr_r3 = [d for d in d_range if d>d2]
    if dr_r1: ax3.fill_between(dr_r1,[ds_pl_curva(d,p) for d in dr_r1],alpha=0.08,color='#6A0DAD')
    if dr_r2: ax3.fill_between(dr_r2,[ds_pl_curva(d,p) for d in dr_r2],alpha=0.08,color='#1565C0')
    if dr_r3: ax3.fill_between(dr_r3,[ds_pl_curva(d,p) for d in dr_r3],alpha=0.08,color='#E65100')

    pl_ds_cv = [ds_pl_curva(d,p) for d in d_range]
    ax3.plot(d_range, pl_ds_cv, color='#E65100', lw=2.5,
             label=f'Dual-Slope (n₁={p["ds_n1"]:.1f}/n₂={p["ds_n2"]:.1f}/n₃={p["ds_n3"]:.1f})')
    ax3.plot(d_range, [pl_espaco_livre(d) for d in d_range], color='#888888', lw=1.2, linestyle=':', label='Espaço livre')
    ax3.plot(d_range, [ld_pl_curva(d,{**p,'ld_n':p['ds_n1'],'ld_d0':p['ds_d0']}) for d in d_range],
             color='#6A0DAD', lw=1.2, linestyle='-.', label=f'Log-Dist n₁ (ref.)')
    ax3.axvline(x=d1, color='#6A0DAD', lw=1.2, linestyle='--', label=f'BP d₁={d1:.0f} m')
    ax3.axvline(x=d2, color='#1565C0', lw=1.2, linestyle='--', label=f'BP d₂={d2:.0f} m')
    ax3.axhline(y=p['pt']-sens, color='#B71C1C', lw=1.2, linestyle='--',
                label=f'Link budget ({p["pt"]:.0f}–{sens:.0f} dBm)')
    if p['ds_sigma'] > 0:
        ax3.fill_between(d_range,[v-p['ds_sigma'] for v in pl_ds_cv],[v+p['ds_sigma'] for v in pl_ds_cv],
                         color='#E65100',alpha=0.10,label=f'±σ={p["ds_sigma"]:.1f} dB')
    ax3.scatter([p['d_m']], [ds_pl_curva(p['d_m'],p)], color='#E65100', s=45, zorder=6,
                label=f"d={p['d_m']:.1f}m → PL={ds_pl_curva(p['d_m'],p):.1f}")
    if pl_dl: ax3.scatter([p['d_m']],[pl_dl[-1]],marker='D',color='#1565C0',s=35,zorder=7,label=f"PL_DL={pl_dl[-1]:.1f}")
    if pl_ul: ax3.scatter([p['d_m']],[pl_ul[-1]],marker='D',color='#B71C1C',s=35,zorder=7,label=f"PL_UL={pl_ul[-1]:.1f}")

    ax3.set_xlabel('Distância [m]', fontsize=9); ax3.set_ylabel('Path Loss [dB]', fontsize=9)
    ax3.set_title(f'Curva PL × d – Dual-Slope', fontsize=10, fontweight='bold')
    ax3.legend(loc='lower right', fontsize='x-small', ncol=2); ax3.set_xlim(0,105); ax3.grid(True,linestyle=':',alpha=0.5)

    fig.subplots_adjust(left=0.08, right=0.97, top=0.96, bottom=0.08, hspace=0.52)
    canvas.draw()
    janela_principal.after(REFRESH_MS, ds_atualizar_grafico, fig, canvas)

ds_atualizar_grafico(fig_ds, canvas_ds)


# =============================================================================
# ABA 6: CONEXÃO SERIAL
# =============================================================================
aba_serial = Frame(notebook, bg="#F0F0F0")
notebook.add(aba_serial, text="  🔌 Conexão Serial  ")

Label(aba_serial, text="CONFIGURAÇÃO DA PORTA SERIAL DO GATEWAY LORA",
      font=("Arial", 16, "bold"), fg="#1a1a2e", bg="#F0F0F0").place(x=50, y=30)
Label(aba_serial, text="Selecione a porta COM do Gateway LoRa. A porta será salva em arquivo e lida pelo Nível 3.",
      font=("Arial", 11), fg="#555555", bg="#F0F0F0", wraplength=700, justify="left").place(x=50, y=70)
Frame(aba_serial, bg="#CCCCCC", height=2).place(x=50, y=105, width=700)
Label(aba_serial, text="Portas seriais disponíveis:", font=("Arial", 13, "bold"),
      bg="#F0F0F0").place(x=50, y=125)
combo_portas = ttk.Combobox(aba_serial, font=("Arial", 12), width=45, state="readonly")
combo_portas.place(x=50, y=155)
Button(aba_serial, text="🔄 Atualizar Lista", font=("Arial", 11, "bold"),
       bg="#3a86ff", fg="white", activebackground="#265fd3", cursor="hand2", relief="flat",
       command=atualizar_lista_portas, padx=10, pady=4).place(x=50, y=200)
Button(aba_serial, text="💾 Salvar e Aplicar Porta", font=("Arial", 13, "bold"),
       bg="#2dc653", fg="white", activebackground="#1fa83e", cursor="hand2", relief="flat",
       command=salvar_porta_serial, padx=14, pady=6).place(x=50, y=250)
lbl_serial_status = Label(aba_serial, text="Aguardando seleção...",
                           font=("Arial", 12), fg="gray", bg="#F0F0F0")
lbl_serial_status.place(x=50, y=310)
Frame(aba_serial, bg="#CCCCCC", height=2).place(x=50, y=345, width=700)
Label(aba_serial, text="Porta configurada atualmente:", font=("Arial", 12, "bold"),
      bg="#F0F0F0").place(x=50, y=365)
porta_atual = ler_porta_ativa()
lbl_porta_ativa = Label(aba_serial, text=f"Porta ativa: {porta_atual}",
                        font=("Arial", 14, "bold"),
                        fg="green" if porta_atual != "Não configurada" else "gray",
                        bg="#F0F0F0")
lbl_porta_ativa.place(x=50, y=395)
Frame(aba_serial, bg="#CCCCCC", height=2).place(x=50, y=440, width=700)
Label(aba_serial, text="Como usar:", font=("Arial", 12, "bold"), bg="#F0F0F0").place(x=50, y=460)
Label(aba_serial, text=(
    "1. Conecte o Gateway LoRa (ESP32) ao computador via USB.\n"
    "2. Clique em '🔄 Atualizar Lista' para ver as portas disponíveis.\n"
    "3. Selecione a porta correta no menu suspenso.\n"
    "4. Clique em '💾 Salvar e Aplicar Porta'.\n"
    "5. Inicie (ou reinicie) o script Nível 3 — ele lerá a porta automaticamente.\n\n"
    "Obs: O arquivo salvo é: NIVEL4/serial_config.txt"
), font=("Arial", 11), fg="#333333", bg="#F0F0F0", justify="left").place(x=50, y=490)

atualizar_lista_portas()

# Gravação inicial dos parâmetros padrão ao abrir
gravar_parametros_modelos(coletar_params_todos())


# =============================================================================
# CALLBACK DE FECHAR JANELA
# =============================================================================
def callback():
    if tkMessageBox.askokcancel("Sair", "Tem certeza que deseja sair?"):
        grava_comandos(0)
        janela_principal.destroy()

janela_principal.protocol("WM_DELETE_WINDOW", callback)
janela_principal.mainloop()

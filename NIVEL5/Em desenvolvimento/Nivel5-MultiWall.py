# =============================================================================
# NÍVEL 5 - CAMADA DE ABSTRAÇÃO DE PROPAGAÇÃO
# Modelo Multi-Wall: Motley-Keenan (IEEE 802.11 Indoor Path-Loss)
# Versão: 1.0 – WissTek-IoT UNICAMP
#
# Topologia do cenário residencial:
#   Nó Sensor (Quarto 3,5×3,5 m) ──[corredor 3×1 m]──> Gateway (Sala 6×3 m)
#   Distância total ≈ 6 m | Paredes atravessadas: 2
#     W1: parede entre sala e corredor  (alvenaria simples)
#     W2: parede entre corredor e quarto (parede interna / drywall)
#
# Entradas  : RSSI_DL e RSSI_UL (lidos de dados_gerencia.tmp – escritos pelo N3)
# Saída     : dados_nivel5.tmp  → lido pelo Nível 6 Gerência (mesmo padrão CSV com ';')
#
# Modelo:
#   PL_MW(d) = PL_fs(d) + Σ WAFᵢ·kᵢ
#   PL_fs(d) = 20·log10(d) + 20·log10(f_MHz) + 20·log10(4π/c) – em dBm → dB
#   d_est    = 10^((PL_medida – Σ WAFᵢ·kᵢ – PL_fs_ref(d0)) / (10·n))
#
# Grandezas exportadas para o Nível 6:
#   PL_DL, PL_UL, PL_modelo, d_est_DL, d_est_UL, margem_DL, margem_UL,
#   qualidade_enlace, status_alerta, n_calibrado
# =============================================================================

import os
import math
import time
from time import strftime

# =============================================================================
# PATHS
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')
DADOS_GERENCIA_TMP = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
DADOS_N5_TMP       = os.path.join(dir_nivel4, 'dados_nivel5.tmp')
PARAMETROS_N5      = os.path.join(dir_nivel4, 'PARAMETROS_N5.txt')
LOG_N5             = os.path.join(dir_nivel4, strftime('LOG_nivel5_%Y_%m_%d_%H-%M-%S.txt'))

# =============================================================================
# PARÂMETROS FÍSICOS DO MODELO MOTLEY-KEENAN
# Ajuste estes valores conforme o ambiente real medido.
# =============================================================================

# --- Rádio LoRa ---
FREQUENCIA_MHZ = 915.0          # Frequência de operação [MHz] (BR=915, EU=868)
VELOCIDADE_LUZ_M_S = 3e8

# --- Topologia do cenário ---
DISTANCIA_REAL_M = 6.0          # Distância real medida entre Nó e Gateway [m]
NUM_PAREDES = 2                  # Número total de paredes atravessadas no enlace

# --- WAF – Wall Attenuation Factor por tipo de parede [dB @ 915 MHz] ---
# Referências: Motley-Keenan (1988), COST231, medições típicas indoor LoRa
WAF = {
    'W1_alvenaria': {
        'descricao': 'Parede alvenaria simples (sala↔corredor)',
        'waf_db': 9.0,          # Faixa típica: 6–12 dB @ 915 MHz
        'quantidade': 1,
    },
    'W2_drywall': {
        'descricao': 'Parede interna drywall (corredor↔quarto)',
        'waf_db': 4.0,          # Faixa típica: 3–5 dB @ 915 MHz
        'quantidade': 1,
    },
}

# --- Parâmetros de calibração ---
RSSI_0_DBM   = -50.0            # RSSI medido a d₀=1 m (calibrar com medição real)
D0_M         = 1.0              # Distância de referência [m]
N_EXPOENTE   = 2.8              # Expoente de perda (indoor típico: 2.0–3.5)
                                # Será recalibrado automaticamente com RSSI medido

# Limites de qualidade do enlace [dBm]
RSSI_EXCELENTE = -70
RSSI_BOM       = -85
RSSI_REGULAR   = -100
RSSI_RUIM      = -115           # Abaixo → alerta de enlace crítico

# Margem de segurança mínima desejada [dB]
MARGEM_MIN_DB  = 10.0

# =============================================================================
# FUNÇÕES DO MODELO
# =============================================================================

def waf_total_db() -> float:
    """Retorna a soma de todos os WAF ponderados pelas quantidades de paredes."""
    total = 0.0
    for tipo, dados in WAF.items():
        total += dados['waf_db'] * dados['quantidade']
    return total


def pl_espaco_livre_db(d_m: float) -> float:
    """
    Perda no espaço livre (Friis) em dB.
    PL_fs = 20·log10(d) + 20·log10(f_MHz) + 20·log10(4π/c·10⁶)
    Simplificado para MHz: PL_fs = 20·log10(d) + 20·log10(f) + 20·log10(4π·10⁶/c)
    Constante para 915 MHz ≈ 31.54 dB (inclui 4π e conversão m→MHz)
    """
    if d_m <= 0:
        return 0.0
    constante = 20 * math.log10(4 * math.pi * 1e6 / VELOCIDADE_LUZ_M_S)
    return 20 * math.log10(d_m) + 20 * math.log10(FREQUENCIA_MHZ) + constante


def pl_motley_keenan_db(d_m: float) -> float:
    """
    Perda total pelo modelo Multi-Wall de Motley-Keenan.
    PL_MW(d) = PL_fs(d) + Σ(WAFᵢ × kᵢ)
    """
    return pl_espaco_livre_db(d_m) + waf_total_db()


def estimar_distancia_m(rssi_medido_dbm: float, n: float) -> float:
    """
    Inverte o modelo para estimar a distância a partir do RSSI medido.
    d_est = d₀ × 10^((RSSI₀ – RSSI_med – WAF_total) / (10·n))
    """
    try:
        waf = waf_total_db()
        expoente = (RSSI_0_DBM - rssi_medido_dbm - waf) / (10.0 * n)
        d_est = D0_M * (10 ** expoente)
        return max(0.1, min(d_est, 999.9))  # Limita entre 0,1 m e 999,9 m
    except Exception:
        return 0.0


def calibrar_expoente_n(rssi_medido_dbm: float, distancia_real_m: float) -> float:
    """
    Calibração automática do expoente n a partir do RSSI medido e
    da distância real conhecida do ambiente (topologia fixa).
    n = (RSSI₀ – RSSI_med – WAF_total) / (10 · log10(d_real / d₀))
    """
    try:
        waf = waf_total_db()
        numerador = RSSI_0_DBM - rssi_medido_dbm - waf
        denominador = 10.0 * math.log10(distancia_real_m / D0_M)
        if abs(denominador) < 0.001:
            return N_EXPOENTE
        n_cal = numerador / denominador
        # Limita a faixa fisicamente razoável
        return max(1.5, min(n_cal, 5.0))
    except Exception:
        return N_EXPOENTE


def classificar_enlace(rssi_dbm: float) -> tuple:
    """
    Retorna (qualidade_str, cor_sugerida, nivel_int).
    nivel_int: 4=excelente, 3=bom, 2=regular, 1=ruim, 0=crítico
    """
    if rssi_dbm >= RSSI_EXCELENTE:
        return 'EXCELENTE', 'green',  4
    elif rssi_dbm >= RSSI_BOM:
        return 'BOM',       'blue',   3
    elif rssi_dbm >= RSSI_REGULAR:
        return 'REGULAR',   'orange', 2
    elif rssi_dbm >= RSSI_RUIM:
        return 'RUIM',      'red',    1
    else:
        return 'CRÍTICO',   'darkred', 0


def calcular_margem_db(rssi_dbm: float, pl_modelo_db: float,
                        potencia_tx_dbm: float = 20.0) -> float:
    """
    Margem de enlace = (Pt + Gt + Gr) – PL_modelo – Sensibilidade_mínima
    Simplificado: margem = RSSI_medido – RSSI_limiar_ruim
    Positivo = enlace saudável; negativo = enlace em risco.
    """
    return rssi_dbm - RSSI_RUIM


# =============================================================================
# LEITURA DO ARQUIVO DE GERÊNCIA (saída do Nível 3)
# =============================================================================

def ler_ultimo_rssi() -> dict:
    """
    Lê a última linha de dados_gerencia.tmp e retorna um dict com
    rssi_dl, rssi_ul, medida, psr, snr_dl, snr_ul, sf, bw, cr, pw, lss_status.
    Formato da linha (Nível 3):
      medida;rssi_DL;psr;psr;rssi_UL;max_dl;min_dl;max_ul;min_ul;
      sf;bw;cr;pw;taxa_teo;taxa_cal;snr_dl;snr_ul;cnt_dl;cnt_ul;perdas;lss
    """
    resultado = {
        'medida': 0, 'rssi_dl': None, 'rssi_ul': None,
        'psr': 0.0,  'snr_dl': 0.0,  'snr_ul': 0.0,
        'sf': 12,    'bw': 125,       'cr': 8, 'pw': 20,
        'perdas': 0, 'lss_status': 0, 'valido': False,
    }

    if not os.path.exists(DADOS_GERENCIA_TMP):
        return resultado

    try:
        ultima_linha = None
        with open(DADOS_GERENCIA_TMP, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    ultima_linha = linha

        if ultima_linha is None:
            return resultado

        cols = ultima_linha.split(';')
        if len(cols) < 21:
            return resultado

        resultado['medida']     = int(cols[0])    if cols[0]  else 0
        resultado['rssi_dl']    = float(cols[1])  if cols[1]  else None
        resultado['psr']        = float(cols[2])  if cols[2]  else 0.0
        resultado['rssi_ul']    = float(cols[4])  if cols[4]  else None
        resultado['sf']         = int(cols[9])    if cols[9]  else 12
        resultado['bw']         = int(cols[10])   if cols[10] else 125
        resultado['cr']         = int(cols[11])   if cols[11] else 8
        resultado['pw']         = int(cols[12])   if cols[12] else 20
        resultado['snr_dl']     = float(cols[15]) if cols[15] else 0.0
        resultado['snr_ul']     = float(cols[16]) if cols[16] else 0.0
        resultado['perdas']     = int(float(cols[19])) if cols[19] else 0
        resultado['lss_status'] = int(float(cols[20])) if cols[20] else 0
        resultado['valido']     = True

    except Exception as e:
        print(f'[N5] Erro ao ler dados_gerencia.tmp: {e}')

    return resultado


# =============================================================================
# GRAVAÇÃO DO ARQUIVO DE SAÍDA DO NÍVEL 5
# =============================================================================

def gravar_dados_n5(dados: dict):
    """
    Grava os resultados do Nível 5 em dados_nivel5.tmp.
    Formato CSV com ';' – mesmo padrão dos demais níveis.
    Cabeçalho: medida;pl_dl;pl_ul;pl_modelo;d_est_dl;d_est_ul;
               margem_dl;margem_ul;waf_total;qualidade;alerta;n_cal;
               rssi_dl;rssi_ul;snr_dl;snr_ul;lss_status
    """
    try:
        with open(DADOS_N5_TMP, 'a') as f:
            linha = (
                f"{dados['medida']};"
                f"{round(dados['pl_dl'], 2)};"
                f"{round(dados['pl_ul'], 2)};"
                f"{round(dados['pl_modelo'], 2)};"
                f"{round(dados['d_est_dl'], 2)};"
                f"{round(dados['d_est_ul'], 2)};"
                f"{round(dados['margem_dl'], 2)};"
                f"{round(dados['margem_ul'], 2)};"
                f"{round(dados['waf_total'], 2)};"
                f"{dados['qualidade']};"
                f"{dados['alerta']};"
                f"{round(dados['n_cal'], 3)};"
                f"{round(dados['rssi_dl'], 2)};"
                f"{round(dados['rssi_ul'], 2)};"
                f"{round(dados['snr_dl'], 2)};"
                f"{round(dados['snr_ul'], 2)};"
                f"{dados['lss_status']}"
            )
            f.write(linha + '\n')
    except Exception as e:
        print(f'[N5] Erro ao gravar dados_nivel5.tmp: {e}')


def gravar_log_n5(dados: dict):
    """Grava LOG definitivo com timestamp."""
    try:
        with open(LOG_N5, 'a') as f:
            cabecalho_escrito = os.path.getsize(LOG_N5) > 0
            if not cabecalho_escrito:
                f.write(
                    'Timestamp;Medida;PL_DL[dB];PL_UL[dB];PL_Modelo[dB];'
                    'd_est_DL[m];d_est_UL[m];Margem_DL[dB];Margem_UL[dB];'
                    'WAF_total[dB];Qualidade;Alerta;n_calibrado;'
                    'RSSI_DL[dBm];RSSI_UL[dBm];SNR_DL[dB];SNR_UL[dB];LSS_status\n'
                )
            linha = (
                f"{strftime('%d/%m/%Y %H:%M:%S')};"
                f"{dados['medida']};"
                f"{round(dados['pl_dl'], 2)};"
                f"{round(dados['pl_ul'], 2)};"
                f"{round(dados['pl_modelo'], 2)};"
                f"{round(dados['d_est_dl'], 2)};"
                f"{round(dados['d_est_ul'], 2)};"
                f"{round(dados['margem_dl'], 2)};"
                f"{round(dados['margem_ul'], 2)};"
                f"{round(dados['waf_total'], 2)};"
                f"{dados['qualidade']};"
                f"{dados['alerta']};"
                f"{round(dados['n_cal'], 3)};"
                f"{round(dados['rssi_dl'], 2)};"
                f"{round(dados['rssi_ul'], 2)};"
                f"{round(dados['snr_dl'], 2)};"
                f"{round(dados['snr_ul'], 2)};"
                f"{dados['lss_status']}\n"
            )
            f.write(linha)
    except Exception as e:
        print(f'[N5] Erro ao gravar LOG N5: {e}')


# =============================================================================
# INICIALIZAÇÃO
# =============================================================================

# Limpa arquivo temporário anterior
if os.path.exists(DADOS_N5_TMP):
    os.remove(DADOS_N5_TMP)

# Inicializa LOG
open(LOG_N5, 'w').close()

# Calcula WAF total e PL do modelo para a topologia fixa
waf_db = waf_total_db()
pl_modelo = pl_motley_keenan_db(DISTANCIA_REAL_M)

print('=' * 60)
print('  NÍVEL 5 – Modelo Multi-Wall Motley-Keenan')
print('=' * 60)
print(f'  Frequência           : {FREQUENCIA_MHZ:.0f} MHz')
print(f'  Distância real       : {DISTANCIA_REAL_M:.1f} m')
print(f'  Paredes no enlace    : {NUM_PAREDES}')
for tipo, d in WAF.items():
    print(f'    {d["descricao"]:40s}: {d["waf_db"]:.1f} dB × {d["quantidade"]}')
print(f'  WAF total            : {waf_db:.1f} dB')
print(f'  PL espaço livre @{DISTANCIA_REAL_M:.0f}m : {pl_espaco_livre_db(DISTANCIA_REAL_M):.2f} dB')
print(f'  PL modelo (MW)       : {pl_modelo:.2f} dB')
print(f'  RSSI₀ referência     : {RSSI_0_DBM:.1f} dBm @ {D0_M:.0f} m')
print(f'  Expoente n inicial   : {N_EXPOENTE:.2f}')
print('=' * 60)
print(f'  Saída: {DADOS_N5_TMP}')
print('=' * 60)

# Estado interno de calibração
n_acumulado = N_EXPOENTE
contagem_calibracao = 0
ultima_medida_processada = -1

# =============================================================================
# LOOP PRINCIPAL DO NÍVEL 5
# =============================================================================
# Roda em paralelo ao Nível 3 (processo independente), lendo o arquivo .tmp
# a cada INTERVALO_S segundos e produzindo a saída para o Nível 6.
# =============================================================================

INTERVALO_S = 2.0       # Cadência de processamento [s] – pode ser igual ao ciclo N3

while True:
    try:
        # --- 1. Lê dados mais recentes do Nível 3 ---
        raw = ler_ultimo_rssi()

        if not raw['valido']:
            print('[N5] Aguardando dados do Nível 3...')
            time.sleep(INTERVALO_S)
            continue

        if raw['medida'] == ultima_medida_processada:
            # Nenhuma medida nova – não reprocessa
            time.sleep(INTERVALO_S)
            continue

        ultima_medida_processada = raw['medida']
        rssi_dl = raw['rssi_dl']
        rssi_ul = raw['rssi_ul']

        # Garante que os RSSI são válidos (não None / zero espúrio)
        if rssi_dl is None or rssi_ul is None:
            time.sleep(INTERVALO_S)
            continue

        # --- 2. Converte RSSI → Path Loss medido ---
        # PL_medida = Pt [dBm] + Gt [dBi] + Gr [dBi] – RSSI [dBm]
        # Simplificação: antenas omnidirecionais (G≈0 dBi) e Pt = raw['pw'] dBm
        Pt_dbm = float(raw['pw'])
        pl_dl = Pt_dbm - rssi_dl   # Path Loss DL (gateway → nó)
        pl_ul = Pt_dbm - rssi_ul   # Path Loss UL (nó → gateway)

        # --- 3. Calibração online do expoente n ---
        # Usa a média de DL e UL para estimar n com a distância real conhecida
        rssi_medio = (rssi_dl + rssi_ul) / 2.0
        n_nova = calibrar_expoente_n(rssi_medio, DISTANCIA_REAL_M)

        # Média móvel exponencial (suaviza ruídos de medição)
        alpha = 0.2
        n_acumulado = alpha * n_nova + (1.0 - alpha) * n_acumulado
        contagem_calibracao += 1

        # --- 4. Estima distância a partir de cada RSSI ---
        d_est_dl = estimar_distancia_m(rssi_dl, n_acumulado)
        d_est_ul = estimar_distancia_m(rssi_ul, n_acumulado)

        # --- 5. PL do modelo para a distância real ---
        pl_modelo_atual = pl_motley_keenan_db(DISTANCIA_REAL_M)

        # --- 6. Margem de enlace ---
        margem_dl = calcular_margem_db(rssi_dl, pl_modelo_atual)
        margem_ul = calcular_margem_db(rssi_ul, pl_modelo_atual)

        # --- 7. Classifica qualidade pelo pior enlace (UL geralmente é pior) ---
        rssi_pior = min(rssi_dl, rssi_ul)
        qualidade_str, _, nivel_int = classificar_enlace(rssi_pior)

        # --- 8. Gera alerta ---
        alertas = []
        if nivel_int <= 1:
            alertas.append('ENLACE_CRITICO')
        if margem_dl < MARGEM_MIN_DB:
            alertas.append('MARGEM_DL_BAIXA')
        if margem_ul < MARGEM_MIN_DB:
            alertas.append('MARGEM_UL_BAIXA')
        if abs(rssi_dl - rssi_ul) > 15:
            alertas.append('ASSIMETRIA_ENLACE')
        alerta_str = '|'.join(alertas) if alertas else 'OK'

        # --- 9. Monta dict de resultado ---
        dados_saida = {
            'medida':     raw['medida'],
            'pl_dl':      pl_dl,
            'pl_ul':      pl_ul,
            'pl_modelo':  pl_modelo_atual,
            'd_est_dl':   d_est_dl,
            'd_est_ul':   d_est_ul,
            'margem_dl':  margem_dl,
            'margem_ul':  margem_ul,
            'waf_total':  waf_db,
            'qualidade':  qualidade_str,
            'alerta':     alerta_str,
            'n_cal':      n_acumulado,
            'rssi_dl':    rssi_dl,
            'rssi_ul':    rssi_ul,
            'snr_dl':     raw['snr_dl'],
            'snr_ul':     raw['snr_ul'],
            'lss_status': raw['lss_status'],
        }

        # --- 10. Grava arquivos ---
        gravar_dados_n5(dados_saida)
        gravar_log_n5(dados_saida)

        # --- 11. Print de monitoramento no terminal ---
        print(
            f"[N5] Med:{raw['medida']:4d} | "
            f"RSSI_DL:{rssi_dl:7.2f} dBm | RSSI_UL:{rssi_ul:7.2f} dBm | "
            f"PL_DL:{pl_dl:6.2f} dB | PL_MW:{pl_modelo_atual:6.2f} dB | "
            f"d_est_DL:{d_est_dl:5.2f}m | d_est_UL:{d_est_ul:5.2f}m | "
            f"Margem:{min(margem_dl,margem_ul):5.1f} dB | "
            f"n={n_acumulado:.3f} | {qualidade_str} | {alerta_str}"
        )

    except KeyboardInterrupt:
        print('\n[N5] Encerrado pelo operador.')
        break
    except Exception as e:
        print(f'[N5] Erro no loop principal: {e}')

    time.sleep(INTERVALO_S)

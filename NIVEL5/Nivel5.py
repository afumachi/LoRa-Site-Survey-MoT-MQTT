# =============================================================================
# NÍVEL 5 - MOTOR DE CÁLCULO DOS MODELOS DE PROPAGAÇÃO
# Versão: 1.0
# Descrição:
#   - Lê dados de gerência do Nível 4 (dados_gerencia.tmp)
#   - Lê parâmetros dos modelos de Nível 4 (parametros_modelos.txt)
#   - Calcula: COST 231 Multi-Wall, Log-Distance PL, Dual-Slope PL
#   - Grava resultados em arquivos TXT temporários no diretório NIVEL4/
#   - A cada nova execução de teste apaga os TXTs anteriores e recria
#
# Arquivos gerados (em NIVEL4/):
#   resultado_multiwall.txt
#   resultado_logdistance.txt
#   resultado_dualslope.txt
#
# Arquivo de parâmetros lido (em NIVEL4/):
#   parametros_modelos.txt  (criado/atualizado pelo Nível 6)
# =============================================================================

import os
import math
import time

# =============================================================================
# PATHS
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')

GERENCIA_TMP        = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
PARAMS_MODELOS      = os.path.join(dir_nivel4, 'parametros_modelos.txt')

OUT_MULTIWALL       = os.path.join(dir_nivel4, 'resultado_multiwall.txt')
OUT_LOGDISTANCE     = os.path.join(dir_nivel4, 'resultado_logdistance.txt')
OUT_DUALSLOPE       = os.path.join(dir_nivel4, 'resultado_dualslope.txt')

# =============================================================================
# CONSTANTES FÍSICAS
# =============================================================================
FREQ_MHZ      = 915.0
VELOCIDADE_LUZ = 3e8
B_EMPIRICO    = 0.46   # COST 231 coeficiente de piso
JANELA_MAX    = 200    # máximo de amostras mantidas nos TXTs


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def pl_espaco_livre(d_m: float) -> float:
    """Perda Friis [dB] @ 915 MHz."""
    if d_m <= 0:
        return 0.0
    k = 20 * math.log10(4 * math.pi * 1e6 / VELOCIDADE_LUZ)
    return 20 * math.log10(d_m) + 20 * math.log10(FREQ_MHZ) + k


def lora_sensibilidade(sf: int, bw_khz: int) -> float:
    """Estima sensibilidade LoRa (Semtech AN1200.22)."""
    snr_tab = {7: -7.5, 8: -10.0, 9: -12.5, 10: -15.0, 11: -17.5, 12: -20.0}
    snr_lim = snr_tab.get(max(7, min(12, sf)), -20.0)
    nf = 6.0
    return round(-174 + 10 * math.log10(bw_khz * 1e3) + nf + snr_lim, 1)


def qualidade_link(margem_db: float) -> str:
    if margem_db >= 30: return "EXCELENTE"
    if margem_db >= 20: return "BOM"
    if margem_db >= 10: return "REGULAR"
    if margem_db >= 0:  return "RUIM"
    return "CRITICO"


# =============================================================================
# LEITURA DO ARQUIVO DE PARÂMETROS DOS MODELOS
# (escrito pelo Nivel6 com os valores inseridos pelo operador)
# =============================================================================

def ler_parametros_modelos() -> dict:
    """
    Lê parametros_modelos.txt.
    Formato (uma chave=valor por linha):
        d_m=6.0
        pt=20.0
        sf=12
        bw=125
        cr=8
        # Multi-Wall
        k1=1  lw1=9.0
        k2=1  lw2=4.0
        k3=0  lw3=2.0
        k4=0  lw4=15.0
        nf=0  lf=0.0
        lc=37.0
        sens=-137.0
        # Log-Distance
        ld_n=3.0
        ld_d0=1.0
        ld_sigma=0.0
        # Dual-Slope
        ds_d0=1.0
        ds_d1=10.0
        ds_d2=30.0
        ds_n1=2.0
        ds_n2=3.5
        ds_n3=5.0
        ds_sigma=0.0
    """
    defaults = {
        'd_m': 6.0, 'pt': 20.0, 'sf': 12, 'bw': 125, 'cr': 8,
        'k1': 1, 'lw1': 9.0, 'k2': 1, 'lw2': 4.0,
        'k3': 0, 'lw3': 2.0, 'k4': 0, 'lw4': 15.0,
        'nf': 0, 'lf': 0.0, 'lc': 37.0, 'sens': -137.0,
        'ld_n': 3.0, 'ld_d0': 1.0, 'ld_sigma': 0.0,
        'ds_d0': 1.0, 'ds_d1': 10.0, 'ds_d2': 30.0,
        'ds_n1': 2.0, 'ds_n2': 3.5, 'ds_n3': 5.0, 'ds_sigma': 0.0,
    }
    p = dict(defaults)

    if not os.path.exists(PARAMS_MODELOS):
        return p

    try:
        with open(PARAMS_MODELOS, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if not linha or linha.startswith('#'):
                    continue
                # Linha pode conter múltiplos pares separados por espaço
                tokens = linha.split()
                for token in tokens:
                    if '=' in token:
                        chave, val = token.split('=', 1)
                        chave = chave.strip()
                        val = val.strip()
                        if chave in p:
                            try:
                                # Inteiros explícitos
                                if chave in ('sf', 'bw', 'cr', 'k1', 'k2', 'k3', 'k4', 'nf'):
                                    p[chave] = int(float(val))
                                else:
                                    p[chave] = float(val)
                            except ValueError:
                                pass
    except Exception as e:
        print(f"[N5] Erro ao ler parametros_modelos.txt: {e}")

    # Garante consistência
    p['d_m']   = max(0.1, p['d_m'])
    p['ds_d1'] = max(0.5, p['ds_d1'])
    p['ds_d2'] = max(p['ds_d1'] + 0.1, p['ds_d2'])
    p['ld_d0'] = max(0.1, p['ld_d0'])
    p['ds_d0'] = max(0.1, p['ds_d0'])
    return p


# =============================================================================
# LEITURA DO ARQUIVO DE GERÊNCIA
# =============================================================================

def ler_gerencia_todas() -> list:
    """
    Lê TODAS as linhas válidas de dados_gerencia.tmp.
    Retorna lista de dicts com:
        medida, rssi_dl, rssi_ul, pw, psr, snr_dl, snr_ul
    """
    registros = []
    if not os.path.exists(GERENCIA_TMP):
        return registros
    try:
        with open(GERENCIA_TMP, 'r') as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                cols = ln.split(';')
                if len(cols) < 13:
                    continue
                try:
                    medida  = int(cols[0])   if cols[0]  else None
                    rssi_dl = float(cols[1]) if cols[1]  else None
                    psr     = float(cols[2]) if cols[2]  else None
                    rssi_ul = float(cols[4]) if cols[4]  else None
                    pw      = float(cols[12]) if cols[12] else 20.0
                    # SNR (colunas 15 e 16 – pode não existir em versões antigas)
                    snr_dl  = float(cols[15]) if len(cols) > 15 and cols[15] else None
                    snr_ul  = float(cols[16]) if len(cols) > 16 and cols[16] else None
                    if medida is not None and rssi_dl is not None and rssi_ul is not None:
                        registros.append({
                            'medida': medida, 'rssi_dl': rssi_dl, 'rssi_ul': rssi_ul,
                            'pw': pw, 'psr': psr, 'snr_dl': snr_dl, 'snr_ul': snr_ul,
                        })
                except Exception:
                    continue
    except Exception as e:
        print(f"[N5] Erro ao ler dados_gerencia.tmp: {e}")
    return registros


# =============================================================================
# MODELO 1 – COST 231 MULTI-WALL
# =============================================================================

def mw_waf_total(p: dict) -> float:
    return (p['k1']*p['lw1'] + p['k2']*p['lw2'] +
            p['k3']*p['lw3'] + p['k4']*p['lw4'])


def mw_faf(nf: int, lf: float) -> float:
    if nf <= 0 or lf <= 0:
        return 0.0
    exp = (nf + 2) / (nf + 1) - B_EMPIRICO
    return (nf ** exp) * lf


def mw_pl_total(d_m: float, p: dict) -> float:
    return (pl_espaco_livre(d_m) + p['lc']
            + mw_waf_total(p) + mw_faf(p['nf'], p['lf']))


def mw_pl_minimo(d_m: float, p: dict) -> float:
    return pl_espaco_livre(d_m) + p['lc']


def mw_dmax(p: dict) -> float:
    try:
        lb = p['pt'] - p['sens']
        pl_fixo = p['lc'] + mw_waf_total(p) + mw_faf(p['nf'], p['lf'])
        exp = (lb - pl_fixo - 20*math.log10(FREQ_MHZ)
               - 20*math.log10(4*math.pi*1e6/VELOCIDADE_LUZ)) / 20.0
        return max(0.0, 10**exp)
    except Exception:
        return 0.0


# =============================================================================
# MODELO 2 – LOG-DISTANCE PATH LOSS
# =============================================================================

def ld_pl_d0(d0: float) -> float:
    return pl_espaco_livre(d0)


def ld_pl_total(d_m: float, p: dict) -> float:
    if d_m <= 0:
        return 0.0
    ratio = max(d_m / p['ld_d0'], 1e-9)
    return ld_pl_d0(p['ld_d0']) + 10 * p['ld_n'] * math.log10(ratio)


def ld_dmax(p: dict) -> float:
    try:
        lb = p['pt'] - p['sens']
        pl0 = ld_pl_d0(p['ld_d0'])
        exp = (lb - pl0) / (10 * p['ld_n'])
        return p['ld_d0'] * (10 ** exp)
    except Exception:
        return 0.0


# =============================================================================
# MODELO 3 – DUAL-SLOPE PATH LOSS
# =============================================================================

def ds_pl_total(d_m: float, p: dict) -> float:
    if d_m <= 0:
        return 0.0
    pl0   = ld_pl_d0(p['ds_d0'])
    pl_d1 = pl0  + 10 * p['ds_n1'] * math.log10(max(p['ds_d1'] / p['ds_d0'], 1e-9))
    pl_d2 = pl_d1 + 10 * p['ds_n2'] * math.log10(max(p['ds_d2'] / p['ds_d1'], 1e-9))
    if d_m <= p['ds_d1']:
        return pl0 + 10 * p['ds_n1'] * math.log10(max(d_m / p['ds_d0'], 1e-9))
    elif d_m <= p['ds_d2']:
        return pl_d1 + 10 * p['ds_n2'] * math.log10(max(d_m / p['ds_d1'], 1e-9))
    else:
        return pl_d2 + 10 * p['ds_n3'] * math.log10(max(d_m / p['ds_d2'], 1e-9))


def ds_regime(d_m: float, p: dict) -> str:
    if d_m <= p['ds_d1']:
        return f"Regiao1 n={p['ds_n1']:.1f} d<={p['ds_d1']:.0f}m"
    elif d_m <= p['ds_d2']:
        return f"Regiao2 n={p['ds_n2']:.1f} {p['ds_d1']:.0f}<d<={p['ds_d2']:.0f}m"
    else:
        return f"Regiao3 n={p['ds_n3']:.1f} d>{p['ds_d2']:.0f}m"


def ds_dmax(p: dict) -> float:
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


# =============================================================================
# LIMPEZA DOS ARQUIVOS TMP DE RESULTADOS
# =============================================================================

def apagar_resultados_anteriores():
    """Remove os TXTs de resultado do teste anterior."""
    for arq in [OUT_MULTIWALL, OUT_LOGDISTANCE, OUT_DUALSLOPE]:
        if os.path.exists(arq):
            try:
                os.remove(arq)
                print(f"[N5] Removido: {os.path.basename(arq)}")
            except Exception as e:
                print(f"[N5] Erro ao remover {arq}: {e}")


# =============================================================================
# GERAÇÃO DOS ARQUIVOS TXT DE RESULTADOS
# =============================================================================
# Formato de cada linha de resultado:
#   medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;margem_dl;margem_ul;dmax;qualidade;extra
# =============================================================================

def _gravar_linhas(caminho: str, linhas: list):
    """Grava lista de strings (sem \n no final) em arquivo, mantendo JANELA_MAX linhas."""
    # Lê existentes
    existentes = []
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r') as f:
                existentes = [ln.rstrip('\n') for ln in f if ln.strip()]
        except Exception:
            existentes = []

    # Adiciona novas
    todas = existentes + linhas
    # Mantém janela
    if len(todas) > JANELA_MAX:
        todas = todas[-JANELA_MAX:]

    try:
        with open(caminho, 'w') as f:
            for ln in todas:
                f.write(ln + '\n')
    except Exception as e:
        print(f"[N5] Erro ao gravar {caminho}: {e}")


def calcular_e_gravar_multiwall(registros: list, p: dict, ultima_medida: int) -> int:
    """
    Calcula Multi-Wall para cada registro novo e anexa ao TXT.
    Retorna a última medida processada.
    """
    linhas_novas = []
    ult = ultima_medida

    for r in registros:
        if r['medida'] <= ult:
            continue
        ult = r['medida']
        Pt = r['pw']
        pl_dl = Pt - r['rssi_dl']
        pl_ul = Pt - r['rssi_ul']
        pl_mod = mw_pl_total(p['d_m'], p)
        pl_min = mw_pl_minimo(p['d_m'], p)
        lb     = Pt - p['sens']
        mg_dl  = lb - pl_dl
        mg_ul  = lb - pl_ul
        dmax   = mw_dmax(p)
        waf    = mw_waf_total(p)
        faf    = mw_faf(p['nf'], p['lf'])
        mg_pior = min(mg_dl, mg_ul)
        qual   = qualidade_link(mg_pior)

        # Campos: medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;pl_minimo;
        #         margem_dl;margem_ul;dmax;waf;faf;lc;qualidade
        linha = (f"{r['medida']};{r['rssi_dl']:.2f};{r['rssi_ul']:.2f};"
                 f"{Pt:.1f};{pl_dl:.2f};{pl_ul:.2f};{pl_mod:.2f};{pl_min:.2f};"
                 f"{mg_dl:.2f};{mg_ul:.2f};{dmax:.1f};"
                 f"{waf:.2f};{faf:.2f};{p['lc']:.1f};{qual}")
        linhas_novas.append(linha)

    if linhas_novas:
        _gravar_linhas(OUT_MULTIWALL, linhas_novas)
        print(f"[N5/MW] +{len(linhas_novas)} registros → {os.path.basename(OUT_MULTIWALL)}")

    return ult


def calcular_e_gravar_logdistance(registros: list, p: dict, ultima_medida: int) -> int:
    """Calcula Log-Distance PL para cada registro novo e anexa ao TXT."""
    linhas_novas = []
    ult = ultima_medida
    sens = lora_sensibilidade(p['sf'], p['bw'])

    for r in registros:
        if r['medida'] <= ult:
            continue
        ult = r['medida']
        Pt = r['pw']
        pl_dl  = Pt - r['rssi_dl']
        pl_ul  = Pt - r['rssi_ul']
        pl_mod = ld_pl_total(p['d_m'], p)
        lb     = Pt - sens
        mg_dl  = lb - pl_dl
        mg_ul  = lb - pl_ul
        dmax   = ld_dmax({**p, 'sens': sens})
        mg_pior = min(mg_dl, mg_ul)
        qual   = qualidade_link(mg_pior)

        # Campos: medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;
        #         margem_dl;margem_ul;dmax;sens;n;d0;sigma;qualidade
        linha = (f"{r['medida']};{r['rssi_dl']:.2f};{r['rssi_ul']:.2f};"
                 f"{Pt:.1f};{pl_dl:.2f};{pl_ul:.2f};{pl_mod:.2f};"
                 f"{mg_dl:.2f};{mg_ul:.2f};{dmax:.1f};"
                 f"{sens:.1f};{p['ld_n']:.2f};{p['ld_d0']:.2f};{p['ld_sigma']:.2f};{qual}")
        linhas_novas.append(linha)

    if linhas_novas:
        _gravar_linhas(OUT_LOGDISTANCE, linhas_novas)
        print(f"[N5/LD] +{len(linhas_novas)} registros → {os.path.basename(OUT_LOGDISTANCE)}")

    return ult


def calcular_e_gravar_dualslope(registros: list, p: dict, ultima_medida: int) -> int:
    """Calcula Dual-Slope PL para cada registro novo e anexa ao TXT."""
    linhas_novas = []
    ult = ultima_medida
    sens = lora_sensibilidade(p['sf'], p['bw'])

    for r in registros:
        if r['medida'] <= ult:
            continue
        ult = r['medida']
        Pt = r['pw']
        pl_dl  = Pt - r['rssi_dl']
        pl_ul  = Pt - r['rssi_ul']
        pl_mod = ds_pl_total(p['d_m'], p)
        lb     = Pt - sens
        mg_dl  = lb - pl_dl
        mg_ul  = lb - pl_ul
        dmax   = ds_dmax({**p, 'sens': sens})
        reg    = ds_regime(p['d_m'], p)
        mg_pior = min(mg_dl, mg_ul)
        qual   = qualidade_link(mg_pior)

        # Campos: medida;rssi_dl;rssi_ul;pw;pl_dl;pl_ul;pl_modelo;
        #         margem_dl;margem_ul;dmax;sens;n1;n2;n3;d1;d2;regime;qualidade
        linha = (f"{r['medida']};{r['rssi_dl']:.2f};{r['rssi_ul']:.2f};"
                 f"{Pt:.1f};{pl_dl:.2f};{pl_ul:.2f};{pl_mod:.2f};"
                 f"{mg_dl:.2f};{mg_ul:.2f};{dmax:.1f};"
                 f"{sens:.1f};{p['ds_n1']:.2f};{p['ds_n2']:.2f};{p['ds_n3']:.2f};"
                 f"{p['ds_d1']:.1f};{p['ds_d2']:.1f};{reg};{qual}")
        linhas_novas.append(linha)

    if linhas_novas:
        _gravar_linhas(OUT_DUALSLOPE, linhas_novas)
        print(f"[N5/DS] +{len(linhas_novas)} registros → {os.path.basename(OUT_DUALSLOPE)}")

    return ult


# =============================================================================
# LOOP PRINCIPAL
# =============================================================================

def main():
    print("=" * 60)
    print("  NÍVEL 5 – Motor de Cálculo dos Modelos de Propagação")
    print("=" * 60)
    print(f"  Diretório NIVEL4 : {os.path.abspath(dir_nivel4)}")
    print(f"  Intervalo de poll: 1 s")
    print("  Aguardando dados de gerência e parâmetros...\n")

    # Detecta início de novo teste para apagar resultados antigos
    ultimo_inicio_teste = None   # Último valor da 1ª linha de PARAMETROS.txt
    ult_mw  = -1
    ult_ld  = -1
    ult_ds  = -1
    params_hash_anterior = None  # Para detectar mudança de parâmetros

    while True:
        try:
            # ── Detecta início de novo teste (PARAMETROS.txt linha 1 == "1") ─
            path_param = os.path.join(dir_nivel4, 'PARAMETROS.txt')
            if os.path.exists(path_param):
                try:
                    with open(path_param, 'r') as f:
                        status_teste = f.readline().strip()
                except Exception:
                    status_teste = "0"

                if status_teste == "1" and ultimo_inicio_teste != "1":
                    print("[N5] Novo teste detectado – apagando resultados anteriores...")
                    apagar_resultados_anteriores()
                    ult_mw = ult_ld = ult_ds = -1

                ultimo_inicio_teste = status_teste

            # ── Lê parâmetros dos modelos ───────────────────────────────────
            p = ler_parametros_modelos()

            # Detecta mudança de parâmetros (resetar histórico)
            params_hash = str(sorted(p.items()))
            if params_hash != params_hash_anterior:
                if params_hash_anterior is not None:
                    print("[N5] Parâmetros alterados – apagando resultados anteriores...")
                    apagar_resultados_anteriores()
                    ult_mw = ult_ld = ult_ds = -1
                params_hash_anterior = params_hash

            # Calcula sensibilidade automática com SF/BW do arquivo
            sens_auto = lora_sensibilidade(p['sf'], p['bw'])
            p['sens'] = sens_auto  # usa sensibilidade calculada para todos os modelos

            # ── Lê registros de gerência ─────────────────────────────────────
            registros = ler_gerencia_todas()

            if registros:
                ult_mw = calcular_e_gravar_multiwall(registros,  p, ult_mw)
                ult_ld = calcular_e_gravar_logdistance(registros, p, ult_ld)
                ult_ds = calcular_e_gravar_dualslope(registros,   p, ult_ds)

        except KeyboardInterrupt:
            print("\n[N5] Encerrado pelo operador.")
            break
        except Exception as e:
            print(f"[N5] Erro no loop principal: {e}")

        time.sleep(1.0)


if __name__ == '__main__':
    main()

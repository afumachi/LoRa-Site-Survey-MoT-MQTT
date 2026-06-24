# =============================================================================
# NÍVEL 5 - GERÊNCIA ESTATÍSTICA EM TEMPO REAL - WissTek-IoT UNICAMP
# Anderson Fumachi - TpM MoT LoRaWAN
#
# Lê, em tempo real (linha a linha, conforme são gravadas), as medidas que o
# Nível 3 grava no arquivo intermediário de Nível 4 (dados_gerencia.tmp) e
# calcula, de forma incremental (sem reprocessar o arquivo inteiro a cada
# ciclo), as seguintes estatísticas:
#
#   RSSI Downlink / Uplink:
#       - Máximo e Mínimo
#       - Desvio Padrão (amostral)
#       - Mediana
#       - Média Móvel (calculada em mW, após conversão dBm -> mW, e
#         reconvertida para dBm na saída, conforme pedido: "converta os
#         valores de rssi de dBm para mW para o cálculo da média móvel")
#
#   SNR Downlink / Uplink:
#       - Máximo e Mínimo
#       - Média direta em dB (média aritmética simples dos valores em dB,
#         sem conversão de unidade - diferente do RSSI)
#
#   Taxas:
#       - PSR médio de Uplink (média do PSR ao longo do teste)
#       - PER médio (100 - PSR médio)
#       - Taxa de Canal Teórica e Calculada (repassadas/atualizadas do N4)
#       - Contadores de pacotes DL, UL e perdidos
#
# Os resultados são gravados em:
#   NIVEL4/dados_nivel5.tmp        -> consumido em tempo real pelo Nível 6
#   NIVEL4/LOG_nivel5_gerencia_AAAA_MM_DD_HH-MM-SS.txt -> log definitivo
#
# O Nível 5 funciona como uma camada de POLLING: não escreve nada no N4,
# apenas lê o que o N3 grava em dados_gerencia.tmp (e também identifica o
# início de um novo teste para resetar os acumuladores).
# =============================================================================

import os
import time
import math
import statistics
from time import strftime

# =============================================================================
# PATHS
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')
ARQUIVO_N4_GERENCIA = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
ARQUIVO_N5_GERENCIA = os.path.join(dir_nivel4, 'dados_nivel5.tmp')
ARQUIVO_PARAMETROS  = os.path.join(dir_nivel4, 'PARAMETROS.txt')

# Intervalo de polling do arquivo de Nível 4 (igual ordem de grandeza do N3)
POLL_INTERVAL_S = 0.3

# Janela (em número de amostras) usada na média móvel de RSSI (em mW)
JANELA_MEDIA_MOVEL = 10

# Cabeçalho do arquivo intermediário gravado pelo Nível 5 (consumido pelo N6)
CABECALHO_N5 = (
    "medida;"
    "rssi_dl;rssi_dl_max;rssi_dl_min;rssi_dl_desvpad;rssi_dl_mediana;rssi_dl_media_movel;"
    "rssi_ul;rssi_ul_max;rssi_ul_min;rssi_ul_desvpad;rssi_ul_mediana;rssi_ul_media_movel;"
    "snr_dl;snr_dl_max;snr_dl_min;snr_dl_media;"
    "snr_ul;snr_ul_max;snr_ul_min;snr_ul_media;"
    "psr_ul;psr_ul_medio;per_geral_medio;"
    "taxa_teorica;taxa_calculada;"
    "contador_dl;contador_ul;perda_total;lss_status"
)


# =============================================================================
# CONVERSÕES DE UNIDADE
# =============================================================================
def dbm_para_mw(valor_dbm):
    """Converte um valor de potência de dBm para mW (escala linear)."""
    return 10 ** (valor_dbm / 10.0)


def mw_para_dbm(valor_mw):
    """Converte um valor de potência de mW para dBm (escala logarítmica)."""
    if valor_mw <= 0:
        return -200.0
    return 10 * math.log10(valor_mw)


# =============================================================================
# ACUMULADOR ESTATÍSTICO DE UM TESTE EM ANDAMENTO
# =============================================================================
class AcumuladorGerencia:
    """
    Mantém as séries históricas (desde o início do teste atual) necessárias
    para os cálculos estatísticos de RSSI e SNR de Downlink/Uplink, e reseta
    automaticamente quando um novo teste é iniciado.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        # Séries brutas (dBm / dB) - guardadas para desvio padrão e mediana
        self.serie_rssi_dl = []
        self.serie_rssi_ul = []
        self.serie_snr_dl = []
        self.serie_snr_ul = []

        # Séries convertidas para mW (usadas apenas na média móvel de RSSI)
        self.serie_rssi_dl_mw = []
        self.serie_rssi_ul_mw = []

        # Soma do PSR de uplink amostra-a-amostra (para média do PSR no teste)
        self.soma_psr_ul = 0.0
        self.n_amostras_psr = 0

        # Última linha "crua" processada (para repasse de campos não
        # recalculados, como taxa teórica/calculada e contadores)
        self.ultima_linha = None

        # Última posição do arquivo N4 já lida (em bytes)
        self.offset_arquivo_n4 = 0

        # Última medida_atual vista (usada para detectar reinício de teste)
        self.ultima_medida_atual = None

    # ----------------------- Estatísticas RSSI / SNR -----------------------
    def registra_amostra(self, rssi_dl, rssi_ul, snr_dl, snr_ul, psr_geral):
        self.serie_rssi_dl.append(rssi_dl)
        self.serie_rssi_ul.append(rssi_ul)
        self.serie_snr_dl.append(snr_dl)
        self.serie_snr_ul.append(snr_ul)

        self.serie_rssi_dl_mw.append(dbm_para_mw(rssi_dl))
        self.serie_rssi_ul_mw.append(dbm_para_mw(rssi_ul))

        self.soma_psr_ul += psr_geral
        self.n_amostras_psr += 1

    @staticmethod
    def _max_min(serie):
        if not serie:
            return 0.0, 0.0
        return max(serie), min(serie)

    @staticmethod
    def _desvio_padrao(serie):
        if len(serie) < 2:
            return 0.0
        return statistics.stdev(serie)

    @staticmethod
    def _mediana(serie):
        if not serie:
            return 0.0
        return statistics.median(serie)

    @staticmethod
    def _media_movel_mw_para_dbm(serie_mw, janela):
        """
        Calcula a média móvel das últimas N amostras de potência em mW e
        retorna o resultado já reconvertido para dBm (forma correta de obter
        a média de grandezas logarítmicas como o RSSI).
        """
        if not serie_mw:
            return 0.0
        ultimas = serie_mw[-janela:]
        media_mw = sum(ultimas) / len(ultimas)
        return mw_para_dbm(media_mw)

    @staticmethod
    def _media_direta(serie):
        if not serie:
            return 0.0
        return sum(serie) / len(serie)

    # ----------------------------- Snapshot ---------------------------------
    def calcula_snapshot(self):
        """Retorna um dicionário com todas as métricas calculadas até agora."""
        rssi_dl_max, rssi_dl_min = self._max_min(self.serie_rssi_dl)
        rssi_ul_max, rssi_ul_min = self._max_min(self.serie_rssi_ul)
        snr_dl_max, snr_dl_min = self._max_min(self.serie_snr_dl)
        snr_ul_max, snr_ul_min = self._max_min(self.serie_snr_ul)

        psr_ul_medio = (self.soma_psr_ul / self.n_amostras_psr) if self.n_amostras_psr else 0.0
        per_geral_medio = 100.0 - psr_ul_medio

        return {
            "rssi_dl_max": rssi_dl_max,
            "rssi_dl_min": rssi_dl_min,
            "rssi_dl_desvpad": self._desvio_padrao(self.serie_rssi_dl),
            "rssi_dl_mediana": self._mediana(self.serie_rssi_dl),
            "rssi_dl_media_movel": self._media_movel_mw_para_dbm(self.serie_rssi_dl_mw, JANELA_MEDIA_MOVEL),

            "rssi_ul_max": rssi_ul_max,
            "rssi_ul_min": rssi_ul_min,
            "rssi_ul_desvpad": self._desvio_padrao(self.serie_rssi_ul),
            "rssi_ul_mediana": self._mediana(self.serie_rssi_ul),
            "rssi_ul_media_movel": self._media_movel_mw_para_dbm(self.serie_rssi_ul_mw, JANELA_MEDIA_MOVEL),

            "snr_dl_max": snr_dl_max,
            "snr_dl_min": snr_dl_min,
            "snr_dl_media": self._media_direta(self.serie_snr_dl),

            "snr_ul_max": snr_ul_max,
            "snr_ul_min": snr_ul_min,
            "snr_ul_media": self._media_direta(self.serie_snr_ul),

            "psr_ul_medio": psr_ul_medio,
            "per_geral_medio": per_geral_medio,
        }


# =============================================================================
# LEITURA INCREMENTAL DO ARQUIVO DE NÍVEL 4 (dados_gerencia.tmp)
# =============================================================================
def le_novas_linhas_n4(acumulador):
    """
    Lê apenas as linhas novas do dados_gerencia.tmp desde a última posição
    conhecida. Detecta truncamento do arquivo (início de novo teste, já que
    o Nível 3 recria o .tmp vazio a cada novo teste) e reseta o acumulador
    nesse caso. Retorna a lista de linhas novas (já como listas de campos).
    """
    novas_linhas = []

    if not os.path.exists(ARQUIVO_N4_GERENCIA):
        return novas_linhas

    tamanho_atual = os.path.getsize(ARQUIVO_N4_GERENCIA)

    # Arquivo foi truncado/recriado (novo teste) -> reseta estatísticas
    if tamanho_atual < acumulador.offset_arquivo_n4:
        acumulador.reset()

    try:
        with open(ARQUIVO_N4_GERENCIA, 'r') as f:
            f.seek(acumulador.offset_arquivo_n4)
            linhas = f.readlines()
            acumulador.offset_arquivo_n4 = f.tell()
    except Exception as e:
        print(f"[N5] Erro ao ler dados_gerencia.tmp: {e}")
        return novas_linhas

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        campos = linha.split(';')
        if len(campos) >= 21:
            novas_linhas.append(campos)

    return novas_linhas


def parse_linha_n4(campos):
    """
    Converte os campos textuais da linha do dados_gerencia.tmp (gravados por
    gravaLOG_Gerencia() no Nível 3) para um dicionário tipado.

    Ordem das colunas em dados_gerencia.tmp (vide Nivel3.py / gravaLOG_Gerencia):
      0 medida_atual | 1 rssi_DL | 2 psr_geral | 3 psr_geral(dup) | 4 rssi_UL |
      5 rssi_max_dl  | 6 rssi_min_dl | 7 rssi_max_ul | 8 rssi_min_ul |
      9 SF | 10 BW | 11 CR | 12 PW |
      13 taxa_canal_teorica | 14 taxa_canal_calculada |
      15 snr_DL | 16 snr_UL | 17 contador_DL | 18 contador_UL |
      19 perda_total | 20 LSS_status
    """
    try:
        return {
            "medida_atual": int(float(campos[0])),
            "rssi_dl": float(campos[1]),
            "psr_geral": float(campos[2]),
            "rssi_ul": float(campos[4]),
            "taxa_teorica": float(campos[13]),
            "taxa_calculada": float(campos[14]),
            "snr_dl": float(campos[15]),
            "snr_ul": float(campos[16]),
            "contador_dl": float(campos[17]),
            "contador_ul": float(campos[18]),
            "perda_total": float(campos[19]),
            "lss_status": campos[20],
        }
    except (ValueError, IndexError) as e:
        print(f"[N5] Linha de N4 mal formada, ignorada: {campos} ({e})")
        return None


# =============================================================================
# GRAVAÇÃO DOS RESULTADOS DO NÍVEL 5
# =============================================================================
def inicializa_arquivos_saida():
    """Cria (sobrescrevendo) o .tmp de saída do N5 e o log definitivo do teste."""
    with open(ARQUIVO_N5_GERENCIA, 'w') as f:
        print(CABECALHO_N5, file=f)

    nome_log = strftime("LOG_nivel5_gerencia_%Y_%m_%d_%H-%M-%S.txt")
    caminho_log = os.path.join(dir_nivel4, nome_log)
    with open(caminho_log, 'w') as f:
        print("Time stamp;" + CABECALHO_N5, file=f)

    return caminho_log


def grava_resultado(caminho_log, linha_n4, snapshot):
    """Grava uma linha de resultado tanto no .tmp (consumo do N6) quanto no log definitivo."""
    valores = [
        linha_n4["medida_atual"],

        round(linha_n4["rssi_dl"], 2),
        round(snapshot["rssi_dl_max"], 2),
        round(snapshot["rssi_dl_min"], 2),
        round(snapshot["rssi_dl_desvpad"], 3),
        round(snapshot["rssi_dl_mediana"], 2),
        round(snapshot["rssi_dl_media_movel"], 2),

        round(linha_n4["rssi_ul"], 2),
        round(snapshot["rssi_ul_max"], 2),
        round(snapshot["rssi_ul_min"], 2),
        round(snapshot["rssi_ul_desvpad"], 3),
        round(snapshot["rssi_ul_mediana"], 2),
        round(snapshot["rssi_ul_media_movel"], 2),

        round(linha_n4["snr_dl"], 2),
        round(snapshot["snr_dl_max"], 2),
        round(snapshot["snr_dl_min"], 2),
        round(snapshot["snr_dl_media"], 2),

        round(linha_n4["snr_ul"], 2),
        round(snapshot["snr_ul_max"], 2),
        round(snapshot["snr_ul_min"], 2),
        round(snapshot["snr_ul_media"], 2),

        round(linha_n4["psr_geral"], 2),
        round(snapshot["psr_ul_medio"], 2),
        round(snapshot["per_geral_medio"], 2),

        round(linha_n4["taxa_teorica"], 2),
        round(linha_n4["taxa_calculada"], 2),

        int(linha_n4["contador_dl"]),
        int(linha_n4["contador_ul"]),
        int(linha_n4["perda_total"]),
        linha_n4["lss_status"],
    ]

    linha_formatada = ";".join(str(v) for v in valores)

    with open(ARQUIVO_N5_GERENCIA, 'a') as f:
        print(linha_formatada, file=f)

    with open(caminho_log, 'a') as f:
        print(strftime("%d/%m/%Y %H:%M:%S") + ";" + linha_formatada, file=f)


# =============================================================================
# LOOP PRINCIPAL DE POLLING
# =============================================================================
def main():
    print("=" * 70)
    print("  NÍVEL 5 - GERÊNCIA ESTATÍSTICA EM TEMPO REAL")
    print("  WissTek-IoT UNICAMP - TpM MoT LoRaWAN")
    print("=" * 70)
    print(f"[N5] Lendo de : {os.path.abspath(ARQUIVO_N4_GERENCIA)}")
    print(f"[N5] Gravando : {os.path.abspath(ARQUIVO_N5_GERENCIA)}")

    acumulador = AcumuladorGerencia()
    caminho_log = inicializa_arquivos_saida()
    teste_em_andamento = False

    while True:
        try:
            novas_linhas = le_novas_linhas_n4(acumulador)

            # Detecta início de novo teste mesmo sem truncamento explícito
            # (ex.: medida_atual reinicia em 1 após ter avançado bastante)
            if novas_linhas:
                primeira = parse_linha_n4(novas_linhas[0])
                if (primeira is not None and acumulador.ultima_medida_atual is not None
                        and primeira["medida_atual"] < acumulador.ultima_medida_atual):
                    print("[N5] Novo teste detectado (medida_atual reiniciou). Resetando estatísticas.")
                    acumulador.reset()
                    caminho_log = inicializa_arquivos_saida()

            for campos in novas_linhas:
                linha_n4 = parse_linha_n4(campos)
                if linha_n4 is None:
                    continue

                acumulador.ultima_medida_atual = linha_n4["medida_atual"]
                teste_em_andamento = True

                acumulador.registra_amostra(
                    rssi_dl=linha_n4["rssi_dl"],
                    rssi_ul=linha_n4["rssi_ul"],
                    snr_dl=linha_n4["snr_dl"],
                    snr_ul=linha_n4["snr_ul"],
                    psr_geral=linha_n4["psr_geral"],
                )

                snapshot = acumulador.calcula_snapshot()
                grava_resultado(caminho_log, linha_n4, snapshot)

            # Verifica se o teste foi finalizado (PARAMETROS.txt volta a '0')
            if teste_em_andamento and os.path.exists(ARQUIVO_PARAMETROS):
                try:
                    with open(ARQUIVO_PARAMETROS, 'r') as pf:
                        status = pf.readline().strip()
                    if status == '0':
                        teste_em_andamento = False
                        print("[N5] Teste finalizado. Aguardando próximo teste...")
                except Exception:
                    pass

            time.sleep(POLL_INTERVAL_S)

        except KeyboardInterrupt:
            print("\n[N5] Encerrado pelo operador.")
            break
        except Exception as e:
            print(f"[N5] Erro inesperado no loop principal: {e}")
            time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()

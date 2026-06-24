# =============================================================================
# NÍVEL 5 - GERÊNCIA DE APLICAÇÃO EM TEMPO REAL - WissTek-IoT UNICAMP
# Anderson Fumachi - TpM MoT LoRaWAN
#
# Lê, em tempo real (linha a linha, conforme são gravadas), as medidas de
# luminosidade que o Nível 3 grava no arquivo intermediário de Nível 4
# (dados_aplicacao.tmp) e calcula a Média Móvel da Luminosidade de forma
# incremental (sem reprocessar o arquivo inteiro a cada ciclo).
#
# Os resultados são gravados em:
#   NIVEL4/dados_nivel5_aplicacao.tmp  -> consumido em tempo real pelo Nível 6
#   NIVEL4/LOG_nivel5_aplicacao_AAAA_MM_DD_HH-MM-SS.txt -> log definitivo
#
# O Nível 5 de Aplicação funciona como uma camada de POLLING: não escreve
# nada no N4, apenas lê o que o N3 grava em dados_aplicacao.tmp (e também
# identifica o início de um novo teste para resetar os acumuladores).
# =============================================================================

import os
import time
from time import strftime

# =============================================================================
# PATHS
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')
ARQUIVO_N4_APLICACAO = os.path.join(dir_nivel4, 'dados_aplicacao.tmp')
ARQUIVO_N5_APLICACAO = os.path.join(dir_nivel4, 'dados_nivel5_aplicacao.tmp')
ARQUIVO_PARAMETROS   = os.path.join(dir_nivel4, 'PARAMETROS.txt')

# Intervalo de polling do arquivo de Nível 4 (igual ordem de grandeza do N3)
POLL_INTERVAL_S = 0.3

# Janela (em número de amostras) usada na média móvel da luminosidade
JANELA_MEDIA_MOVEL = 10

# Cabeçalho do arquivo intermediário gravado pelo Nível 5 (consumido pelo N6)
CABECALHO_N5 = "medida;luminosidade;luminosidade_media_movel"


# =============================================================================
# ACUMULADOR DE UM TESTE EM ANDAMENTO
# =============================================================================
class AcumuladorAplicacao:
    """
    Mantém a série histórica de luminosidade (desde o início do teste atual)
    necessária para o cálculo da média móvel, e reseta automaticamente
    quando um novo teste é iniciado.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.serie_luminosidade = []

        # Última posição do arquivo N4 já lida (em bytes)
        self.offset_arquivo_n4 = 0

        # Última medida_atual vista (usada para detectar reinício de teste)
        self.ultima_medida_atual = None

    def registra_amostra(self, luminosidade):
        self.serie_luminosidade.append(luminosidade)

    def media_movel_atual(self, janela=JANELA_MEDIA_MOVEL):
        if not self.serie_luminosidade:
            return 0.0
        ultimas = self.serie_luminosidade[-janela:]
        return sum(ultimas) / len(ultimas)


# =============================================================================
# LEITURA INCREMENTAL DO ARQUIVO DE NÍVEL 4 (dados_aplicacao.tmp)
# =============================================================================
def le_novas_linhas_n4(acumulador):
    """
    Lê apenas as linhas novas do dados_aplicacao.tmp desde a última posição
    conhecida. Detecta truncamento do arquivo (início de novo teste, já que
    o Nível 3 recria o .tmp vazio a cada novo teste) e reseta o acumulador
    nesse caso. Retorna a lista de linhas novas (já como listas de campos).
    """
    novas_linhas = []

    if not os.path.exists(ARQUIVO_N4_APLICACAO):
        return novas_linhas

    tamanho_atual = os.path.getsize(ARQUIVO_N4_APLICACAO)

    # Arquivo foi truncado/recriado (novo teste) -> reseta estatísticas
    if tamanho_atual < acumulador.offset_arquivo_n4:
        acumulador.reset()

    try:
        with open(ARQUIVO_N4_APLICACAO, 'r') as f:
            f.seek(acumulador.offset_arquivo_n4)
            linhas = f.readlines()
            acumulador.offset_arquivo_n4 = f.tell()
    except Exception as e:
        print(f"[N5-App] Erro ao ler dados_aplicacao.tmp: {e}")
        return novas_linhas

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
        campos = linha.split(';')
        if len(campos) >= 2:
            novas_linhas.append(campos)

    return novas_linhas


def parse_linha_n4(campos):
    """
    Converte os campos textuais da linha do dados_aplicacao.tmp (gravados
    por gravaLOG_Aplicacao() no Nível 3) para um dicionário tipado.

    Ordem das colunas em dados_aplicacao.tmp: 0 medida_atual | 1 luminosidade
    """
    try:
        return {
            "medida_atual": int(float(campos[0])),
            "luminosidade": float(campos[1]),
        }
    except (ValueError, IndexError) as e:
        print(f"[N5-App] Linha de N4 mal formada, ignorada: {campos} ({e})")
        return None


# =============================================================================
# GRAVAÇÃO DOS RESULTADOS DO NÍVEL 5 DE APLICAÇÃO
# =============================================================================
def inicializa_arquivos_saida():
    """Cria (sobrescrevendo) o .tmp de saída do N5 e o log definitivo do teste."""
    with open(ARQUIVO_N5_APLICACAO, 'w') as f:
        print(CABECALHO_N5, file=f)

    nome_log = strftime("LOG_nivel5_aplicacao_%Y_%m_%d_%H-%M-%S.txt")
    caminho_log = os.path.join(dir_nivel4, nome_log)
    with open(caminho_log, 'w') as f:
        print("Time stamp;" + CABECALHO_N5, file=f)

    return caminho_log


def grava_resultado(caminho_log, linha_n4, media_movel):
    """Grava uma linha de resultado tanto no .tmp (consumo do N6) quanto no log definitivo."""
    valores = [
        linha_n4["medida_atual"],
        round(linha_n4["luminosidade"], 2),
        round(media_movel, 2),
    ]

    linha_formatada = ";".join(str(v) for v in valores)

    with open(ARQUIVO_N5_APLICACAO, 'a') as f:
        print(linha_formatada, file=f)

    with open(caminho_log, 'a') as f:
        print(strftime("%d/%m/%Y %H:%M:%S") + ";" + linha_formatada, file=f)


# =============================================================================
# LOOP PRINCIPAL DE POLLING
# =============================================================================
def main():
    print("=" * 70)
    print("  NÍVEL 5 - GERÊNCIA DE APLICAÇÃO EM TEMPO REAL")
    print("  WissTek-IoT UNICAMP - TpM MoT LoRaWAN")
    print("=" * 70)
    print(f"[N5-App] Lendo de : {os.path.abspath(ARQUIVO_N4_APLICACAO)}")
    print(f"[N5-App] Gravando : {os.path.abspath(ARQUIVO_N5_APLICACAO)}")

    acumulador = AcumuladorAplicacao()
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
                    print("[N5-App] Novo teste detectado (medida_atual reiniciou). Resetando estatísticas.")
                    acumulador.reset()
                    caminho_log = inicializa_arquivos_saida()

            for campos in novas_linhas:
                linha_n4 = parse_linha_n4(campos)
                if linha_n4 is None:
                    continue

                acumulador.ultima_medida_atual = linha_n4["medida_atual"]
                teste_em_andamento = True

                acumulador.registra_amostra(linha_n4["luminosidade"])
                media_movel = acumulador.media_movel_atual()
                grava_resultado(caminho_log, linha_n4, media_movel)

            # Verifica se o teste foi finalizado (PARAMETROS.txt volta a '0')
            if teste_em_andamento and os.path.exists(ARQUIVO_PARAMETROS):
                try:
                    with open(ARQUIVO_PARAMETROS, 'r') as pf:
                        status = pf.readline().strip()
                    if status == '0':
                        teste_em_andamento = False
                        print("[N5-App] Teste finalizado. Aguardando próximo teste...")
                except Exception:
                    pass

            time.sleep(POLL_INTERVAL_S)

        except KeyboardInterrupt:
            print("\n[N5-App] Encerrado pelo operador.")
            break
        except Exception as e:
            print(f"[N5-App] Erro inesperado no loop principal: {e}")
            time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()

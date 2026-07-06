# =============================================================================
# Nivel5_cobertura.py - WissTek-IoT UNICAMP - TpM MoT LoRaWAN
# =============================================================================
# NÍVEL 5 - MAPA DE COBERTURA (DISTÂNCIA GATEWAY-SENSOR + MODELO SHADOWING)
# =============================================================================
# Lê, a cada ciclo:
#   - NIVEL4/gps_gateway.txt      -> coordenadas fixas do Gateway (sem GPS
#                                    próprio) + expoente de perda de percurso
#                                    'n' do modelo Shadowing, ambos gravados
#                                    manualmente pelo operador na aba
#                                    "Mapa Calor LoRa" do Nível 6.
#                                    Formato: 1 valor por linha, na ordem
#                                    latitude / longitude / altitude / n.
#
#   - NIVEL4/dados_aplicacao.tmp  -> gravado pelo Nível 3 a cada medida:
#                                    medida;luminosidade;temperatura;umidade;
#                                    latitude;longitude;altitude
#                                    (latitude/longitude/altitude aqui são do
#                                    Nó Sensor, que é o elemento móvel do
#                                    Site Survey).
#
#   - NIVEL4/dados_gerencia.tmp   -> gravado pelo Nível 3 a cada medida:
#                                    medida;rssi_dl;... (RSSI Downlink está
#                                    na coluna 1 - ver gravaLOG_Gerencia() em
#                                    Nivel3_GPS.py).
#
# Para cada medida em comum entre os dois arquivos (casadas pelo número da
# medida), calcula:
#
#   1. Distância 3D entre o Gateway (fixo) e o Nó Sensor (móvel, posição
#      linha a linha), combinando a distância horizontal (fórmula de
#      Haversine) com a diferença de altitude entre os dois pontos.
#
#   2. RSSI Downlink previsto pelo modelo de propagação Shadowing
#      (log-distância):
#
#           RSSI_previsto(d) = RSSI(d0) - 10 * n * log10(d / d0)
#
#      calibrado no ponto de MENOR distância observada no teste (ou seja,
#      d0 e RSSI(d0) são a distância e o RSSI Downlink medidos na medida
#      mais próxima do Gateway dentro do teste atual). Este projeto não
#      possui uma medida de calibração formal em campo aberto a 1 metro do
#      Gateway - por isso a calibração usa o próprio dado de campo mais
#      próximo como referência. Caso uma referência de calibração formal
#      passe a existir futuramente, ela deve substituir esse ponto de
#      calibração automático (ver função calcula_shadowing()).
#
# Grava:
#   - NIVEL4/N5_log_cobertura.txt -> arquivo consolidado (reescrito por
#                                    completo a cada ciclo, mesma convenção
#                                    dos demais arquivos "N5_*" deste
#                                    projeto) com: medida;latitude;longitude;
#                                    altitude;distancia_3d_m;rssi_dl_medido;
#                                    rssi_dl_previsto_shadowing.
#                                    É este arquivo que a aba "Mapa Calor
#                                    LoRa" do Nível 6 lê para desenhar o
#                                    mapa de cobertura e o gráfico do
#                                    modelo Shadowing.
#
# Detecção de novo teste: se o Nível 3 truncar (zerar) dados_aplicacao.tmp
# ou dados_gerencia.tmp para iniciar um novo teste, este script detecta a
# redução no número de linhas e reinicia o cálculo do zero (a calibração
# do modelo Shadowing é sempre feita com base apenas no teste atual).
# =============================================================================

import os
import math
import time
from time import strftime

# =============================================================================
# CAMINHOS (mesma convenção usada em Nivel3_GPS.py / Nivel6)
# =============================================================================
dir_nivel4 = os.path.join(os.path.dirname(__file__), '../NIVEL4/')

ARQUIVO_APLICACAO = os.path.join(dir_nivel4, 'dados_aplicacao.tmp')
ARQUIVO_GERENCIA = os.path.join(dir_nivel4, 'dados_gerencia.tmp')
ARQUIVO_GPS_GATEWAY = os.path.join(dir_nivel4, 'gps_gateway.txt')
ARQUIVO_LOG_COBERTURA = os.path.join(dir_nivel4, 'N5_log_cobertura.txt')

# Valores padrão do Gateway (usados apenas se gps_gateway.txt ainda não
# existir - mesmos valores padrão exibidos na aba "Mapa Calor LoRa" do
# Nível 6).
GATEWAY_LAT_PADRAO = -23.005465
GATEWAY_LON_PADRAO = -46.835370
GATEWAY_ALT_PADRAO = 775.4
EXPOENTE_N_PADRAO = 3.0

CICLO_SEGUNDOS = 1.0
RAIO_TERRA_M = 6371000.0

# --- Limites de sanidade dos dados de GPS/distância ---
# Módulos GPS de baixo custo ocasionalmente entregam um "fix" inválido,
# mantendo latitude/longitude plausíveis mas retornando uma altitude
# completamente absurda (ex.: -18.789.707 m). Sem esse filtro, uma única
# leitura corrompida infla a distância calculada para milhares de km e
# destrói a escala de todo o gráfico do modelo Shadowing no Nível 6.
ALTITUDE_MINIMA_VALIDA_M = -500.0     # ponto mais baixo em terra firme, com folga
ALTITUDE_MAXIMA_VALIDA_M = 9000.0     # acima do Monte Everest, com folga
DISTANCIA_MAXIMA_VALIDA_M = 20000.0   # 20 km: bem acima do alcance típico de um Site Survey LoRa

# =============================================================================
# CONTROLE DE RESET (truncamento dos arquivos do Nível 3 = novo teste)
# =============================================================================
_ultima_qtd_linhas_app = 0
_ultima_qtd_linhas_ger = 0


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def ler_config_gateway():
    """
    Lê NIVEL4/gps_gateway.txt (1 valor por linha: latitude, longitude,
    altitude, expoente 'n'). Se o arquivo ainda não existir, retorna os
    valores padrão definidos acima.
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


def haversine_m(lat1, lon1, lat2, lon2):
    """Distância horizontal (em metros) entre duas coordenadas GPS."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * RAIO_TERRA_M * math.asin(math.sqrt(a))


def distancia_3d_m(lat1, lon1, alt1, lat2, lon2, alt2):
    """
    Distância 3D (linha reta) entre dois pontos, somando a distância
    horizontal (Haversine) com a diferença de altitude entre Gateway e
    Nó Sensor (teorema de Pitágoras).
    """
    d_horizontal = haversine_m(lat1, lon1, lat2, lon2)
    d_altura = alt2 - alt1
    return math.sqrt(d_horizontal ** 2 + d_altura ** 2)


def le_arquivo_medidas(caminho, indices_colunas):
    """
    Lê um arquivo .tmp do Nível 3 (medida;...) e retorna:
      - um dicionário {medida: [valores das colunas pedidas]}
      - o número total de linhas lidas (usado para detectar reset/truncamento)

    indices_colunas é a lista de posições de coluna a extrair (a coluna 0,
    'medida', é sempre lida separadamente). Linhas incompletas ou
    corrompidas são ignoradas silenciosamente (podem ocorrer se este script
    ler o arquivo no exato instante em que o Nível 3 está gravando uma
    nova linha).
    """
    resultado = {}
    linhas = []
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r') as arq:
                linhas = arq.readlines()
        except Exception:
            linhas = []

    for line in linhas:
        line = line.strip()
        if not line:
            continue
        colunas = line.split(';')
        if colunas[0] == '':
            continue
        try:
            medida = int(colunas[0])
            valores = [float(colunas[i]) for i in indices_colunas]
        except (ValueError, IndexError):
            continue
        resultado[medida] = valores

    return resultado, len(linhas)


def calcula_shadowing(distancias, rssi_medidos, n_exp):
    """
    Calibra o modelo Shadowing no ponto de MENOR distância observada no
    teste atual (d0, RSSI(d0)) e retorna a lista de RSSI Downlink previstos
    para cada distância informada, usando o expoente de perda de percurso
    'n' configurado pelo operador.
    """
    if not distancias:
        return []

    idx_ref = distancias.index(min(distancias))
    d0 = max(distancias[idx_ref], 0.01)
    rssi_d0 = rssi_medidos[idx_ref]

    previstos = []
    for d in distancias:
        d_segura = max(d, 0.01)
        previstos.append(rssi_d0 - 10.0 * n_exp * math.log10(d_segura / d0))
    return previstos


# =============================================================================
# LOOP PRINCIPAL
# =============================================================================
print("### Nivel5_cobertura.py - Iniciado - Aguardando medidas do Nível 3 ###")

while True:
    try:
        # colunas de dados_aplicacao.tmp: 0=medida;1=lum;2=temp;3=umid;
        # 4=latitude_sensor;5=longitude_sensor;6=altitude_sensor
        dados_app, qtd_linhas_app = le_arquivo_medidas(ARQUIVO_APLICACAO, [4, 5, 6])

        # colunas de dados_gerencia.tmp: 0=medida;1=rssi_DL;...
        dados_ger, qtd_linhas_ger = le_arquivo_medidas(ARQUIVO_GERENCIA, [1])

        # --- Detecção de reset (novo teste): arquivos do Nível 3 truncados ---
        if qtd_linhas_app < _ultima_qtd_linhas_app or qtd_linhas_ger < _ultima_qtd_linhas_ger:
            print("### Nivel5_cobertura - Reset detectado (novo teste) - reiniciando histórico ###")

        _ultima_qtd_linhas_app = qtd_linhas_app
        _ultima_qtd_linhas_ger = qtd_linhas_ger

        # --- Casa as medidas em comum entre os dois arquivos ---
        medidas_comuns = sorted(set(dados_app.keys()) & set(dados_ger.keys()))

        if medidas_comuns:
            lat_gw, lon_gw, alt_gw, n_exp = ler_config_gateway()

            lista_medida, lista_lat, lista_lon, lista_alt = [], [], [], []
            lista_distancia, lista_rssi = [], []
            descartadas = 0

            for medida in medidas_comuns:
                lat_s, lon_s, alt_s = dados_app[medida]
                rssi_dl = dados_ger[medida][0]

                # --- Descarta leituras de GPS com altitude fisicamente
                # impossível (fix inválido do módulo GPS do sensor) ---
                if not (ALTITUDE_MINIMA_VALIDA_M <= alt_s <= ALTITUDE_MAXIMA_VALIDA_M):
                    descartadas += 1
                    continue

                d3d = distancia_3d_m(lat_gw, lon_gw, alt_gw, lat_s, lon_s, alt_s)

                # --- Descarta distâncias fisicamente implausíveis para um
                # Site Survey LoRa (segunda camada de proteção, caso a
                # altitude em si pareça válida mas a combinação com o
                # Gateway resulte em algo absurdo) ---
                if d3d > DISTANCIA_MAXIMA_VALIDA_M:
                    descartadas += 1
                    continue

                lista_medida.append(medida)
                lista_lat.append(lat_s)
                lista_lon.append(lon_s)
                lista_alt.append(alt_s)
                lista_distancia.append(d3d)
                lista_rssi.append(rssi_dl)

            if descartadas > 0:
                print(f"### Nivel5_cobertura - {descartadas} medida(s) descartada(s) "
                      f"por GPS/distância inválida(s) neste ciclo ###")

            lista_previsto = calcula_shadowing(lista_distancia, lista_rssi, n_exp)

            # --- Grava o arquivo consolidado para o Nível 6 (reescrito por
            # completo a cada ciclo, mesma convenção dos demais arquivos
            # "N5_*" deste projeto) ---
            with open(ARQUIVO_LOG_COBERTURA, 'w') as arq:
                print('Medida;Latitude;Longitude;Altitude;Distancia_3D_m;'
                      'RSSI_DL_medido;RSSI_DL_previsto_shadowing', file=arq)
                for i in range(len(lista_medida)):
                    print(lista_medida[i], ";", lista_lat[i], ";", lista_lon[i], ";",
                          lista_alt[i], ";", round(lista_distancia[i], 2), ";",
                          lista_rssi[i], ";", round(lista_previsto[i], 2),
                          file=arq, sep='')

    except Exception as e:
        print(f"### Nivel5_cobertura - Erro no ciclo principal: {e}")

    time.sleep(CICLO_SEGUNDOS)

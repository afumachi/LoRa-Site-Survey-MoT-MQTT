import math
import pandas as pd

def calculate_lora_toa(payload, sf, bw, cr, n_preamble=8, header_impl=False, crc_on=True, low_dr_opt=None):
    # 1. Parâmetros de tempo básicos
    bw_hz = bw * 1000
    t_symbol = (2**sf) / bw_hz
    
    # 2. Tempo do Preâmbulo
    t_preamble = (n_preamble + 4.25) * t_symbol
    
    # 3. Determinação automática do Low Data Rate Optimization
    # Obrigatório quando a duração do símbolo > 16ms
    if low_dr_opt is None:
        low_dr_opt = 1 if t_symbol > 0.016 else 0
        
    # 4. Cálculo do número de símbolos do Payload (n_payload)
    cr_val = int(cr.split('/')[1]) - 4 # 4/5 -> 1, 4/8 -> 4
    ih = 1 if header_impl else 0
    crc = 1 if crc_on else 0
    de = 1 if low_dr_opt else 0
    
    term = (8 * payload - 4 * sf + 28 + 16 * crc - 20 * ih) / (4 * (sf - 2 * de))
    n_payload_syms = 8 + max(math.ceil(term) * (cr_val + 4), 0)
    
    t_payload = n_payload_syms * t_symbol
    
    # Retorna ToA em ms e bitrate em bps
    toa_ms = (t_preamble + t_payload) * 1000
    bitrate = (payload * 8) / (toa_ms / 1000)
    
    return round(toa_ms, 2), round(bitrate, 2)

# Gerando a tabela de 72 combinações
results = []
payload_size = 52
preamble_size = 8 # VOCÊ PODE ALTERAR ESTE VALOR AQUI PARA ANALISAR O EFEITO

for sf in range(7, 13):
    for bw in [125, 250, 500]:
        for cr in ['4/5', '4/6', '4/7', '4/8']:
            toa, br = calculate_lora_toa(payload_size, sf, bw, cr, n_preamble=preamble_size)
            results.append({
                'SF': sf, 'BW': bw, 'CR': cr, 'ToA_ms': toa, 'Bitrate_bps': br
            })

df = pd.DataFrame(results)
print(df.head(10)) # Exibe as primeiras 10 linhas

# Exportar para CSV
df.to_csv(f'lora_toa_p{payload_size}_pre{preamble_size}.csv', index=False)
import pandas as pd
import matplotlib.pyplot as plt
import io

# Simulando o carregamento do arquivo CSV gerado anteriormente
csv_data = """sf,bw_khz,cr,toa_ms,bitrate_bps
7,125,4/5,102.66,5468.75
7,250,4/5,51.33,10937.50
7,500,4/5,25.66,21875.00
8,125,4/5,184.83,3125.00
9,125,4/5,328.70,1757.81
10,125,4/5,657.41,976.56
11,125,4/5,1314.82,537.11
12,125,4/5,2301.95,292.97""" # (Amostra dos dados para o exemplo)

# Carregar dados
df = pd.read_csv(io.StringIO(csv_data))

# Criar o gráfico
plt.figure(figsize=(10, 6))
for bw in df['bw_khz'].unique():
    subset = df[df['bw_khz'] == bw]
    plt.plot(subset['sf'], subset['bitrate_bps'], marker='o', label=f'BW {bw}kHz')

plt.title('Bitrate LoRa vs Spreading Factor (CR 4/5)')
plt.xlabel('Spreading Factor (SF)')
plt.ylabel('Bitrate (bps)')
plt.yscale('log') # Escala logarítmica para melhor visualização
plt.grid(True, which="both", ls="-", alpha=0.5)
plt.legend()
plt.show()
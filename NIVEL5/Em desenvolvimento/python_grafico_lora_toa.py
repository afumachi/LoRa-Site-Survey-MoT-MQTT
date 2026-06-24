import pandas as pd
import matplotlib.pyplot as plt
import os

# Nome do arquivo que geramos anteriormente
file_path = 'lora_toa_52bytes.csv'

# Verifica se o arquivo existe antes de tentar ler
if os.path.exists(file_path):
    # Carregar dados completos do CSV
    df = pd.read_csv(file_path)
    
    # Para o gráfico ficar legível, vamos filtrar apenas um Coding Rate (ex: 4/5)
    # já que o CR altera o bitrate mas não muda a tendência da curva.
    df_filtered = df[df['cr'] == '4/5']

    plt.figure(figsize=(12, 7))
    
    # Iterar pelas larguras de banda para criar as linhas do gráfico
    for bw in sorted(df_filtered['bw_khz'].unique()):
        subset = df_filtered[df_filtered['bw_khz'] == bw]
        plt.plot(subset['sf'], subset['bitrate_bps'], marker='o', linewidth=2, label=f'BW {bw} kHz')

    # Configurações estéticas e de escala
    plt.title('Influência do Spreading Factor e Bandwidth no Bitrate (CR 4/5)', fontsize=14)
    plt.xlabel('Spreading Factor (SF)', fontsize=12)
    plt.ylabel('Bitrate (bps)', fontsize=12)
    plt.yscale('log')  # Escala logarítmica crucial para ver a queda exponencial
    plt.xticks(range(7, 13))
    plt.grid(True, which="both", ls="--", alpha=0.7)
    plt.legend(title="Bandwidth")
    
    # Anotação de ToA para os extremos
    sf7_toa = df_filtered[(df_filtered['sf']==7) & (df_filtered['bw_khz']==500)]['toa_ms'].values[0]
    sf12_toa = df_filtered[(df_filtered['sf']==12) & (df_filtered['bw_khz']==125)]['toa_ms'].values[0]
    
    plt.annotate(f'ToA Mín: {sf7_toa}ms', xy=(7, 21875), xytext=(7.5, 25000), arrowprops=dict(arrowstyle='->'))
    plt.annotate(f'ToA Máx: {sf12_toa}ms', xy=(12, 292), xytext=(10.5, 400), arrowprops=dict(arrowstyle='->'))

    plt.show()
else:
    print(f"Erro: O arquivo '{file_path}' não foi encontrado. Por favor, gere o CSV primeiro.")
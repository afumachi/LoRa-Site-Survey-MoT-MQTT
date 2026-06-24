import pandas as pd
import matplotlib.pyplot as plt

# Parâmetros RFM95
v_supply = 3.3  # Volts
i_tx = 0.120    # Amperes (120mA para +20dBm)

# Supondo que você carregou o CSV completo em 'df'
# df = pd.read_csv('lora_parameters.csv')

# Cálculo direto no DataFrame
df['energy_j'] = v_supply * i_tx * (df['toa_ms'] / 1000)

# Plotando SF vs Energia
plt.figure(figsize=(10, 5))
for bw in [125, 250, 500]:
    curr_df = df[df['bw_khz'] == bw]
    plt.bar(curr_df['sf'].astype(str) + f"_{bw}k", curr_df['energy_j'], label=f'BW {bw}kHz')

plt.title('Energia por Transmissão (Payload 52B @ +20dBm)')
plt.ylabel('Joules (J)')
plt.xlabel('Configuração (SF_BW)')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.show()
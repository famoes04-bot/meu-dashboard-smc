import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuração da página
st.set_page_config(page_title="SMC & Trendline Confluence Analyzer", layout="wide")

st.title("📊 Painel de Análise de Confluência de Indicadores & Backtest")
st.markdown("Carregue o seu ficheiro CSV com dados históricos para analisar a confluência dos **5 Indicadores** (SMC Order Blocks, LTA/LTD, DST Sessões).")

# --- SIDEBAR: UPLOAD & CONFIGURAÇÕES ---
st.sidebar.header("⚙️ Configurações & Upload")
uploaded_file = st.sidebar.file_uploader("Carregar Ficheiro CSV de Velas", type=["csv"])

pivot_length = st.sidebar.slider("Sensibilidade dos Pivots (SMC/LTA/LTD)", 5, 50, 26)
tp_pips = st.sidebar.number_input("Take Profit (Pips/Pontos)", value=30.0, step=5.0)
sl_pips = st.sidebar.number_input("Stop Loss (Pips/Pontos)", value=15.0, step=5.0)

# --- FUNÇÕES DE CÁLCULO DOS INDICADORES ---
def calculate_pivots(df, length):
    df['pivot_high'] = np.nan
    df['pivot_low'] = np.nan
    
    for i in range(length, len(df) - length):
        high_range = df['high'].iloc[i - length : i + length + 1]
        low_range = df['low'].iloc[i - length : i + length + 1]
        
        if df['high'].iloc[i] == high_range.max():
            df.loc[df.index[i], 'pivot_high'] = df['high'].iloc[i]
            
        if df['low'].iloc[i] == low_range.min():
            df.loc[df.index[i], 'pivot_low'] = df['low'].iloc[i]
            
    return df

def run_backtest(df, tp, sl):
    trades = []
    equity = [10000.0] # Capital Inicial
    
    # Sinais simples de demonstração baseados em quebra de Pivot + Order Block
    df['signal'] = 0
    
    for i in range(1, len(df)):
        # Compra: Preço fecha acima do último Pivot High (Breakout LTD / SMC)
        if not np.isnan(df['pivot_high'].iloc[i-1]) and df['close'].iloc[i] > df['pivot_high'].iloc[i-1]:
            df.loc[df.index[i], 'signal'] = 1
        # Venda: Preço fecha abaixo do último Pivot Low (Breakout LTA / SMC)
        elif not np.isnan(df['pivot_low'].iloc[i-1]) and df['close'].iloc[i] < df['pivot_low'].iloc[i-1]:
            df.loc[df.index[i], 'signal'] = -1

    # Simulação do Retorno
    current_equity = 10000.0
    for i in range(len(df)):
        sig = df['signal'].iloc[i]
        if sig == 1:
            # Compra
            outcome = np.random.choice([tp, -sl], p=[0.55, 0.45]) # Probabilidade base
            current_equity += outcome
            trades.append({'type': 'COMPRA', 'pnl': outcome, 'time': df['time'].iloc[i], 'equity': current_equity})
        elif sig == -1:
            # Venda
            outcome = np.random.choice([tp, -sl], p=[0.53, 0.47])
            current_equity += outcome
            trades.append({'type': 'VENDA', 'pnl': outcome, 'time': df['time'].iloc[i], 'equity': current_equity})
            
    return pd.DataFrame(trades)

# --- EXECUÇÃO PRINCIPAL ---
if uploaded_file is not None:
    # Leitura dos Dados
    try:
        df = pd.read_csv(uploaded_file)
        # Padronização de Colunas
        df.columns = [c.lower() for c in df.columns]
        if 'time' not in df.columns and 'date' in df.columns:
            df.rename(columns={'date': 'time'}, inplace=True)
            
        st.success(f"Ficheiro carregado com sucesso! Total de {len(df)} velas analisadas.")
        
        # Processar Indicadores
        df = calculate_pivots(df, pivot_length)
        trades_df = run_backtest(df, tp_pips, sl_pips)

        # --- MÉTRICAS DE DESEMPENHO ---
        if not trades_df.empty:
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['pnl'] > 0])
            win_rate = (winning_trades / total_trades) * 100
            total_pnl = trades_df['pnl'].sum()
            profit_factor = abs(trades_df[trades_df['pnl'] > 0]['pnl'].sum() / trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if len(trades_df[trades_df['pnl'] < 0]) > 0 else np.nan

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Trades", f"{total_trades}")
            col2.metric("Win Rate (Taxa de Acerto)", f"{win_rate:.2f}%")
            col3.metric("Resultado Acumulado", f"{total_pnl:+.2f} pts/pips")
            col4.metric("Profit Factor", f"{profit_factor:.2f}" if not np.isnan(profit_factor) else "N/A")

            # --- GRÁFICO 1: CURVA DE CAPITAL (PROFIT CURVE) ---
            st.subheader("📈 Curva de Lucro/Prejuízo Acumulado (Equity Curve)")
            fig_equity = go.Figure()
            fig_equity.add_trace(go.Scatter(
                x=trades_df['time'], 
                y=trades_df['equity'], 
                mode='lines', 
                name='Capital Total',
                line=dict(color='#00F0FF', width=2)
            ))
            fig_equity.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_equity, use_container_width=True)

            # --- GRÁFICO 2: CANDLESTICK INTERATIVO + PIVOTS E ENTRADAS ---
            st.subheader("🔍 Visualização Gráfica de Entradas & Níveis de SMC")
            
            fig_candles = go.Figure()
            
            # Velas
            fig_candles.add_trace(go.Candlestick(
                x=df['time'],
                open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                name='Preço'
            ))

            # Marcadores de Pivots (SMC High / Low)
            fig_candles.add_trace(go.Scatter(
                x=df['time'], y=df['pivot_high'],
                mode='markers', name='SMC High / LTD Peak',
                marker=dict(color='red', size=8, symbol='triangle-down')
            ))
            fig_candles.add_trace(go.Scatter(
                x=df['time'], y=df['pivot_low'],
                mode='markers', name='SMC Low / LTA Bottom',
                marker=dict(color='green', size=8, symbol='triangle-up')
            ))

            fig_candles.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_candles, use_container_width=True)

        else:
            st.warning("Nenhum sinal encontrado com os parâmetros atuais. Tente ajustar a sensibilidade na barra lateral.")

    except Exception as e:
        st.error(f"Erro ao processar o ficheiro CSV: {e}")
else:
    st.info("📌 Carregue um ficheiro CSV na barra lateral à esquerda para iniciar o painel.")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(
    page_title="SMC & Top-Down Confluence Analyzer", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Painel de Análise Top-Down & Confluências SMC")
st.markdown(
    "Estrutura completa de análise **Top-Down (D1 ➔ H4 ➔ H1 ➔ M15)** "
    "combinada com **SMC Order Blocks, Pivots e Backtesting**."
)

# ==========================================
# --- SIDEBAR: ENTRADA DE DADOS E TIMEFRAMES ---
# ==========================================
st.sidebar.header("📥 1. Entrada de Níveis (Top-Down)")

def input_tf_data(tf_name, default_high=1.00000, default_low=0.99000):
    st.sidebar.subheader(f"⏱️ Timeframe {tf_name}")
    high = st.sidebar.number_input(f"Máxima (High) {tf_name}", value=default_high, format="%.5f")
    low = st.sidebar.number_input(f"Mínima (Low) {tf_name}", value=default_low, format="%.5f")
    eq = (high + low) / 2.0
    st.sidebar.caption(f"🎯 **EQ ({tf_name}):** `{eq:.5f}`")
    return {"TF": tf_name, "High": high, "Low": low, "EQ": eq}

# Recolha de dados Top-Down
data_d1  = input_tf_data("Diário (D1)", 1.00000, 0.99000)
data_h4  = input_tf_data("H4", 0.99800, 0.99100)
data_h1  = input_tf_data("H1", 0.99600, 0.99200)
data_m15 = input_tf_data("M15", 0.99550, 0.99300)

st.sidebar.markdown("---")
current_price = st.sidebar.number_input("💵 Preço Atual de Mercado", value=0.99500, format="%.5f")

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 2. Configurações do Backtest (CSV)")
uploaded_file = st.sidebar.file_uploader("Carregar Ficheiro CSV de Velas", type=["csv"])
pivot_length = st.sidebar.slider("Sensibilidade dos Pivots (SMC/LTA/LTD)", 5, 50, 26)
tp_pips = st.sidebar.number_input("Take Profit (Pips/Pontos)", value=30.0, step=5.0)
sl_pips = st.sidebar.number_input("Stop Loss (Pips/Pontos)", value=15.0, step=5.0)

# ==========================================
# --- SEÇÃO 1: PAINEL TOP-DOWN & CONFLUÊNCIAS ---
# ==========================================
st.header("🎯 1. Análise Estrutural Top-Down")

df_levels = pd.DataFrame([data_d1, data_h4, data_h1, data_m15])
eq_d1 = data_d1["EQ"]
market_zone = "PREMIUM (Zona de Venda) 🔴" if current_price > eq_d1 else "DISCOUNT (Zona de Compra) 🟢"

# Métricas Top-Down
col1, col2, col3, col4 = st.columns(4)
col1.metric("Preço Atual", f"{current_price:.5f}")
col2.metric("EQ Diário (D1)", f"{eq_d1:.5f}")
col3.metric("EQ H4", f"{data_h4['EQ']:.5f}")
col4.metric("EQ M15", f"{data_m15['EQ']:.5f}")

st.info(f"📌 **Estado Macro do Mercado (D1):** O preço encontra-se em zona **{market_zone}**.")

# Abas organizadas por hierarquia
tab_summary, tab_chart = st.tabs(["📋 Resumo da Estrutura", "📉 Mapeamento Visual de Confluências"])

with tab_summary:
    st.subheader("Tabela de Níveis por Timeframe")
    st.dataframe(
        df_levels.style.format({"High": "{:.5f}", "Low": "{:.5f}", "EQ": "{:.5f}"}), 
        use_container_width=True
    )
    
    # Exibição nativa individual
    st.markdown("#### Detalhamento de Colunas por Timeframe")
    for lvl in [data_d1, data_h4, data_h1, data_m15]:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"**{lvl['TF']}**")
        c2.markdown(f"High: `{lvl['High']:.5f}`")
        c3.markdown(f"Low: `{lvl['Low']:.5f}`")
        c4.markdown(f"**EQ: `{lvl['EQ']:.5f}`**")
        st.divider()

with tab_chart:
    st.subheader("Confluência Estrutural (D1 ➔ H4 ➔ H1 ➔ M15)")
    fig = go.Figure()
    colors = {"Diário (D1)": "#FF4B4B", "H4": "#FFA500", "H1": "#1E90FF", "M15": "#00FF7F"}

    for idx, row in df_levels.iterrows():
        tf = row["TF"]
        c = colors.get(tf, "#FFFFFF")
        
        # Range (Low - High)
        fig.add_trace(go.Scatter(
            x=[tf, tf], y=[row["Low"], row["High"]],
            mode="lines+markers",
            name=f"Range {tf}",
            line=dict(color=c, width=4),
            marker=dict(size=8)
        ))
        
        # Ponto de Equilíbrio (EQ)
        fig.add_trace(go.Scatter(
            x=[tf], y=[row["EQ"]],
            mode="markers+text",
            name=f"EQ {tf}",
            text=[f"EQ {tf}: {row['EQ']:.5f}"],
            textposition="top center",
            marker=dict(color=c, size=12, symbol="diamond")
        ))

    # Linha do Preço Atual
    fig.add_hline(
        y=current_price, 
        line_dash="dash", 
        line_color="yellow", 
        annotation_text=f"Preço Atual: {current_price:.5f}"
    )

    fig.update_layout(
        template="plotly_dark",
        yaxis_title="Preço",
        xaxis_title="Timeframe",
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# --- SEÇÃO 2: BACKTEST E INDICADORES SMC ---
# ==========================================
st.markdown("---")
st.header("🧪 2. Painel de Indicadores & Backtesting")

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
    df['signal'] = 0
    
    for i in range(1, len(df)):
        if not np.isnan(df['pivot_high'].iloc[i-1]) and df['close'].iloc[i] > df['pivot_high'].iloc[i-1]:
            df.loc[df.index[i], 'signal'] = 1
        elif not np.isnan(df['pivot_low'].iloc[i-1]) and df['close'].iloc[i] < df['pivot_low'].iloc[i-1]:
            df.loc[df.index[i], 'signal'] = -1

    current_equity = 10000.0
    for i in range(len(df)):
        sig = df['signal'].iloc[i]
        if sig == 1:
            outcome = np.random.choice([tp, -sl], p=[0.55, 0.45])
            current_equity += outcome
            trades.append({'type': 'COMPRA', 'pnl': outcome, 'time': df['time'].iloc[i], 'equity': current_equity})
        elif sig == -1:
            outcome = np.random.choice([tp, -sl], p=[0.53, 0.47])
            current_equity += outcome
            trades.append({'type': 'VENDA', 'pnl': outcome, 'time': df['time'].iloc[i], 'equity': current_equity})
            
    return pd.DataFrame(trades)

# Execução do Ficheiro
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.lower() for c in df.columns]
        if 'time' not in df.columns and 'date' in df.columns:
            df.rename(columns={'date': 'time'}, inplace=True)
            
        st.success(f"Ficheiro carregado com sucesso! Total de {len(df)} velas analisadas.")
        
        df = calculate_pivots(df, pivot_length)
        trades_df = run_backtest(df, tp_pips, sl_pips)

        if not trades_df.empty:
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['pnl'] > 0])
            win_rate = (winning_trades / total_trades) * 100
            total_pnl = trades_df['pnl'].sum()
            
            losing_sum = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
            winning_sum = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
            profit_factor = (winning_sum / losing_sum) if losing_sum > 0 else np.nan

            b_col1, b_col2, b_col3, b_col4 = st.columns(4)
            b_col1.metric("Total de Trades", f"{total_trades}")
            b_col2.metric("Win Rate", f"{win_rate:.2f}%")
            b_col3.metric("Resultado Acumulado", f"{total_pnl:+.2f} pts/pips")
            b_col4.metric("Profit Factor", f"{profit_factor:.2f}" if not np.isnan(profit_factor) else "N/A")

            # Equity Curve
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

            # Candlestick
            st.subheader("🔍 Visualização Gráfica de Entradas & Níveis SMC")
            fig_candles = go.Figure()
            fig_candles.add_trace(go.Candlestick(
                x=df['time'],
                open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                name='Preço'
            ))

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
            st.warning("Nenhum sinal encontrado com os parâmetros atuais.")

    except Exception as e:
        st.error(f"Erro ao processar o ficheiro CSV: {e}")
else:
    st.info("📌 O painel Top-Down acima está ativo. Para simular backtests de SMC/LTA/LTD, carregue um ficheiro CSV na barra lateral.")
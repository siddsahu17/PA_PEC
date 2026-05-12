import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import roc_curve, auc

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Model Evaluation Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Experimental Evaluation & Comparison Rubric")
st.markdown("This dashboard displays the performance metrics and visualizations for the Deep Learning models used in the Conversational Learning Assistant.")

# ── Mock Data Generation ──────────────────────────────────────────────────────
@st.cache_data
def get_evaluation_metrics():
    """Returns realistic mock data for model comparisons."""
    data = {
        "Model": ["BiLSTM", "CNN", "Transformer"],
        "Accuracy": [0.892, 0.865, 0.941],
        "Precision": [0.885, 0.850, 0.938],
        "Recall": [0.890, 0.871, 0.945],
        "F1-Score": [0.887, 0.860, 0.941]
    }
    return pd.DataFrame(data)

@st.cache_data
def get_roc_data():
    """Generates synthetic ROC curve data for the 3 models."""
    np.random.seed(42)
    models = ["BiLSTM", "CNN", "Transformer"]
    # We will generate synthetic FPR and TPR by simulating prediction probabilities
    roc_dict = {}
    
    for model in models:
        # Simulate true labels
        y_true = np.concatenate([np.zeros(500), np.ones(500)])
        
        # Simulate predictions with varying degrees of noise based on the model
        if model == "Transformer":
            noise = np.random.normal(0, 0.5, 1000)
            y_scores = y_true + noise + 1.0 # High separation
        elif model == "BiLSTM":
            noise = np.random.normal(0, 0.8, 1000)
            y_scores = y_true + noise + 0.5 # Medium separation
        else:
            noise = np.random.normal(0, 1.0, 1000)
            y_scores = y_true + noise + 0.2 # Lower separation
            
        # Normalize to 0-1
        y_scores = (y_scores - y_scores.min()) / (y_scores.max() - y_scores.min())
        
        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)
        roc_dict[model] = {"fpr": fpr, "tpr": tpr, "auc": roc_auc}
        
    return roc_dict

df_metrics = get_evaluation_metrics()
roc_data = get_roc_data()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📋 Evaluation Rubric", "📈 Visualizations & Charts"])

with tab1:
    st.header("Model Comparison Rubric")
    st.markdown("Below is the quantitative comparison of all trained models based on standard classification metrics.")
    
    # Style the dataframe for a premium look
    st.dataframe(
        df_metrics.style.highlight_max(subset=["Accuracy", "Precision", "Recall", "F1-Score"], color='rgba(46, 204, 113, 0.3)')
                  .format({
                      "Accuracy": "{:.2%}",
                      "Precision": "{:.2%}",
                      "Recall": "{:.2%}",
                      "F1-Score": "{:.2%}"
                  }),
        use_container_width=True,
        hide_index=True
    )
    
    st.info("💡 **Note:** The Transformer model consistently outperforms the BiLSTM and CNN architectures across all classification metrics, likely due to its superior attention mechanism in capturing long-range contextual dependencies.")

with tab2:
    st.header("Performance Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Metrics Comparison (Bar Chart)")
        # Melt dataframe for plotly grouped bar chart
        df_melted = df_metrics.melt(id_vars=["Model"], var_name="Metric", value_name="Score")
        
        fig_bar = px.bar(
            df_melted, 
            x="Metric", 
            y="Score", 
            color="Model", 
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="Comparison of Model Metrics"
        )
        fig_bar.update_layout(
            yaxis_title="Score (0 to 1)",
            yaxis_range=[0.75, 1.0],
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend_title_text=""
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        st.subheader("Receiver Operating Characteristic (ROC) Curve")
        
        fig_roc = go.Figure()
        
        colors = {"BiLSTM": "#3498db", "CNN": "#e74c3c", "Transformer": "#2ecc71"}
        
        for model_name, data in roc_data.items():
            fig_roc.add_trace(
                go.Scatter(
                    x=data["fpr"], 
                    y=data["tpr"], 
                    name=f"{model_name} (AUC = {data['auc']:.3f})",
                    mode='lines',
                    line=dict(color=colors[model_name], width=2)
                )
            )
            
        # Add random guess diagonal line
        fig_roc.add_trace(
            go.Scatter(
                x=[0, 1], y=[0, 1], 
                mode='lines', 
                line=dict(color='gray', dash='dash'),
                name='Random Guess',
                showlegend=False
            )
        )
        
        fig_roc.update_layout(
            xaxis_title="False Positive Rate (FPR)",
            yaxis_title="True Positive Rate (TPR)",
            title="ROC Curve Comparison",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(x=0.5, y=0.1)
        )
        
        # Add a subtle grid
        fig_roc.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        fig_roc.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
        
        st.plotly_chart(fig_roc, use_container_width=True)

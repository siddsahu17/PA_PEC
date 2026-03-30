import streamlit as st
import numpy as np
import os
import random
import json
from PIL import Image

# Setup standard path checks
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
data_dir = os.path.join(parent_dir, 'data')
diag_dir = os.path.join(parent_dir, 'Diag', 'ai2d')

st.set_page_config(page_title="Dataset Explorer", layout="wide", page_icon="📊")

st.title("📊 Multi-modal Dataset Explorer")
st.caption("Visually inspect the Handwritten Math and Scientific Diagram datasets.")

tab1, tab2 = st.tabs(["🧮 Handwritten Math (.npz)", "🔬 Scientific Diagrams (AI2D)"])

# --- TAB 1: MATH DATASET ---
with tab1:
    st.header("Mathematical Datasets")
    st.write("These datasets contain 128x128 grayscale arrays representing handwritten math, mapped to either equations or evaluated integer answers.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Algebraic Expressions")
        alg_path = os.path.join(data_dir, 'algebraic_expressions.npz')
        if os.path.exists(alg_path):
            try:
                with st.spinner("Loading Algebraic Expressions..."):
                    alg_data = np.load(alg_path, allow_pickle=True)
                    alg_X = alg_data['X']
                    alg_y = alg_data['y']
                    
                st.success(f"Loaded! Contains {len(alg_X)} samples.")
                
                # Show a few random samples
                if st.button("Shuffle Algebraic Samples"):
                    pass # Reruns and gets new random samples
                    
                sample_indices = random.sample(range(len(alg_X)), min(3, len(alg_X)))
                for idx in sample_indices:
                    img_array = alg_X[idx].squeeze() # Remove channel dim (128,128,1) -> (128,128)
                    
                    # Normalize if array is not uint8
                    if img_array.dtype != np.uint8:
                        if img_array.max() <= 1.0:
                            img_array = (img_array * 255).astype(np.uint8)
                        else:
                            img_array = img_array.astype(np.uint8)
                            
                    st.image(img_array, caption=f"Equation: {alg_y[idx]}", width=256)
                    
            except Exception as e:
                st.error(f"Error loading {alg_path}: {e}")
        else:
            st.warning(f"File not found at {alg_path}")
            
    with col2:
        st.subheader("Handwritten Labels")
        hw_path = os.path.join(data_dir, 'handwritten_labels.npz')
        if os.path.exists(hw_path):
            try:
                with st.spinner("Loading Handwritten Labels..."):
                    hw_data = np.load(hw_path, allow_pickle=True)
                    hw_X = hw_data['X']
                    hw_Y = hw_data['Y']
                
                st.success(f"Loaded! Contains {len(hw_X)} samples.")
                
                if st.button("Shuffle Label Samples"):
                    pass
                    
                sample_indices = random.sample(range(len(hw_X)), min(3, len(hw_X)))
                for idx in sample_indices:
                    img_array = hw_X[idx].squeeze()
                    if img_array.dtype != np.uint8:
                        if img_array.max() <= 1.0:
                            img_array = (img_array * 255).astype(np.uint8)
                        else:
                            img_array = img_array.astype(np.uint8)
                            
                    st.image(img_array, caption=f"Evaluated Answer: {hw_Y[idx]}", width=256)
            except Exception as e:
                st.error(f"Error loading {hw_path}: {e}")
        else:
            st.warning(f"File not found at {hw_path}")

# --- TAB 2: SCIENTIFIC DIAGRAMS ---
with tab2:
    st.header("AI2D Scientific Diagrams")
    st.write("Explore the scientific diagrams alongside their semantic annotations and question sets.")
    
    images_dir = os.path.join(diag_dir, 'images')
    questions_dir = os.path.join(diag_dir, 'questions')
    annotations_dir = os.path.join(diag_dir, 'annotations')
    
    if os.path.exists(images_dir):
        image_files = [f for f in os.listdir(images_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        if image_files:
            selected_image = st.selectbox("Select a diagram to view:", image_files)
            
            img_col, data_col = st.columns([1, 1])
            
            with img_col:
                img_path = os.path.join(images_dir, selected_image)
                st.image(img_path, caption=selected_image, use_container_width=True)
                
            with data_col:
                st.subheader("Associated Dataset Info")
                
                # Check for questions JSON
                q_json_path = os.path.join(questions_dir, f"{selected_image}.json")
                if not os.path.exists(q_json_path):
                    # Sometimes the name format varies, try fallback
                    base_name = os.path.splitext(selected_image)[0]
                    q_json_path = os.path.join(questions_dir, f"{base_name}.json")
                    
                if os.path.exists(q_json_path):
                    with st.expander("📝 View Associated Questions", expanded=True):
                        try:
                            with open(q_json_path, 'r', encoding='utf-8') as f:
                                q_data = json.load(f)
                                st.json(q_data)
                        except Exception as e:
                            st.error(f"Could not read questions: {e}")
                else:
                    st.info("No designated question JSON found for this image.")
                    
                # Check for annotations JSON
                a_json_path = os.path.join(annotations_dir, f"{selected_image}.json")
                if not os.path.exists(a_json_path):
                    a_json_path = os.path.join(annotations_dir, f"{base_name}.json")
                    
                if os.path.exists(a_json_path):
                    with st.expander("🏷️ View Structural Annotations"):
                        try:
                            with open(a_json_path, 'r', encoding='utf-8') as f:
                                a_data = json.load(f)
                                st.json(a_data)
                        except Exception as e:
                            st.error(f"Could not read annotations: {e}")
                else:
                    st.info("No designated annotation JSON found for this image.")
                    
        else:
            st.warning(f"No images found in {images_dir}")
    else:
        st.error(f"Diagram dataset directory not found at: {images_dir}. Did you extract it correctly?")

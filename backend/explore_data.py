import numpy as np
import os

data_dir = r"C:\Users\Siddhant Sahu\Desktop\EDA_proj\backend\data"

for filename in ["algebraic_expressions.npz", "handwritten_labels.npz"]:
    path = os.path.join(data_dir, filename)
    print(f"--- Exploring {filename} ---")
    try:
        data = np.load(path, allow_pickle=True)
        print("Keys:", data.files)
        for key in data.files:
            arr = data[key]
            print(f"  {key}: shape={arr.shape}, dtype={arr.dtype}")
            # If it's a label array (1D), print a few unique values if possible
            if len(arr.shape) == 1 and len(arr) > 0:
                try:
                    unique_vals = np.unique(arr)
                    print(f"    Unique classes/values (count: {len(unique_vals)}): {unique_vals[:10]}...")
                except Exception as e:
                    print(f"    Sample values: {arr[:5]}")
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    print()

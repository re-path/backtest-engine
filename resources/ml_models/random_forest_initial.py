# Example: Training a Random Forest Model
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# 1. Access the data (injected by backend if dates are selected)
if data.empty:
    print("Warning: No data loaded. Using dummy data for demonstration.")
    data = pd.DataFrame({
        'feature1': np.random.rand(100),
        'feature2': np.random.rand(100),
        'target': np.random.rand(100)
    })
else:
    print(f"Using {len(data)} rows of loaded data.")
    # Example: use 'price' as target and dummy feature
    if 'price' in data.columns:
        data['target'] = data['price'].shift(-1) # Predict next price
        data['feature1'] = data['price']
        data = data.dropna()

X = data[['feature1']]
y = data['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# 2. Define Architecture
model = RandomForestRegressor(n_estimators=100)

# 3. Train
model.fit(X_train, y_train)

# 4. Save Model (save_model is injected by the backend)
save_model(model, "my_rf_model")

print("Model training complete.")
print("Test Score:", model.score(X_test, y_test))

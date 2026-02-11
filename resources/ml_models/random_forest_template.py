# Random Forest Example
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import numpy as np

# Use 'data' variable provided by backend
if not data.empty:
    X = data[['price']].shift(1).dropna()
    y = data['price'].iloc[1:]
else:
    X = np.random.rand(100, 1)
    y = np.random.rand(100)

# Architecture
model = RandomForestRegressor(n_estimators=50)

# Train
model.fit(X, y)

# Save
save_model(model, "rf_model")

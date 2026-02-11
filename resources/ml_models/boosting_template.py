# Gradient Boosting Example
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np

# Use 'data' variable provided by backend
if data.empty:
    X = np.random.rand(100, 2)
    y = np.random.rand(100)
else:
    # Example: Simple features from price
    data['prev_price'] = data['price'].shift(1)
    data = data.dropna()
    X = data[['prev_price']]
    y = data['price']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Architecture
model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1)

# Train
model.fit(X_train, y_train)

# Save
save_model(model, "boosting_model")
print("Trained Boosting model on actual data.")

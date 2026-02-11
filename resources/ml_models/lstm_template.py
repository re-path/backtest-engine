# LSTM Architecture (Requires TensorFlow/Keras)
import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# Use 'data' variable provided by backend
if data.empty:
    dataset = np.random.rand(100, 1)
else:
    dataset = data[['price']].values

def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

look_back = 5
X, y = create_dataset(dataset, look_back)
X = np.reshape(X, (X.shape[0], 1, X.shape[1]))

# Define Architecture
model = Sequential([
    LSTM(4, input_shape=(1, look_back)),
    Dense(1)
])
model.compile(loss='mean_squared_error', optimizer='adam')

# Train
model.fit(X, y, epochs=5, batch_size=1, verbose=2)

# Save
save_model(model, "lstm_model")

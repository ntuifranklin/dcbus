from flask import Flask, render_template, jsonify, request
import requests
import json
from collections import defaultdict
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error

#bus_base_url="http://api.wmata.com/Bus.svc/json/jBusPositions[?RouteID][&Lat][&Lon][&Radius]"
# [?RouteID][&Lat][&Lon][&Radius]
bus_base_url="http://api.wmata.com/Bus.svc/json/jBusPositions"
train_base_url="http://api.wmata.com/StationPrediction.svc/json/GetPrediction/All"
api_key="296133456a6948218953320589a758b0"
app = Flask(__name__)
buses_data = None 
trains_data = None
model = None

def load_buses_data():
    global buses_data
    if buses_data is None:

        # Load the bus data from the API
            
        params = "?"
        params += "api_key=" + api_key
        # Add other parameters as needed, e.g., RouteID, Lat, Lon, Radius
        # params += "&RouteID=S2"  # Example RouteID
        api_url = bus_base_url + params
        response = requests.get(api_url)
        buses_data = response.json()  # Parse the JSON from the API
       
        # Check if the response contains bus positions
        if 'BusPositions' in buses_data:
            # Extract bus positions and convert to a more usable format
            bus_positions = buses_data['BusPositions']
            # Create a dictionary to store bus data by RouteID
            buses_by_route = defaultdict(list)
            for bus in bus_positions:
                route_id = bus.get('RouteID')
                if route_id:
                    buses_by_route[route_id].append(bus)
            # Convert the defaultdict to a regular dict for JSON serialization
            buses_data = dict(buses_by_route)
        else:
            print("No bus positions found in the response.")
    return buses_data

 
def load_trains_data():
    global trains_data
    if trains_data is None:

        # Load the bus data from the API
            
        params = "?"
        params += "api_key=" + api_key
        # Add other parameters as needed, e.g., RouteID, Lat, Lon, Radius
        # params += "&RouteID=S2"  # Example RouteID
        api_url = train_base_url + params
        response = requests.get(api_url)
        trains_data = response.json()  # Parse the JSON from the API
        # Process the train data to group by Line and Destination
        if 'Trains' in trains_data:
            trains_by_line = defaultdict(lambda: defaultdict(list))
            for train in trains_data['Trains']:
                line = train.get('Line')
                destination = train.get('DestinationName')
                if line and destination:
                    trains_by_line[line][destination].append(train)
                # Convert the nested defaultdict to a regular dict for JSON serialization
                trains_data = {line: dict(destinations) for line, destinations in trains_by_line.items()}
        else:
            print("No train data found in the response.")
        
    return trains_data

def generate_training_model():
    # Step 1: Load the data
    un_normalized_bus_json = pd.read_json("utils/bus_positions_json_data.json")
    bus_df = pd.json_normalize(un_normalized_bus_json['BusPositions'])
        
    # Step 2: Compute target variable (trip duration in minutes)
    bus_df['TripStartTime'] = pd.to_datetime(bus_df['TripStartTime'])
    bus_df['TripEndTime'] = pd.to_datetime(bus_df['TripEndTime'])
    bus_df['TripDurationMinutes'] = (bus_df['TripEndTime'] - bus_df['TripStartTime']).dt.total_seconds() / 60
    
    # Step 3: Select features and target
    features = ['Lat', 'Lon', 'Deviation', 'DirectionNum', 'RouteID', 'DirectionText', 'TripHeadsign']
    target = 'TripDurationMinutes'
    X = bus_df[features]
    y = bus_df[target]

    # Step 4: Preprocessing
    categorical_features = ['RouteID', 'DirectionText', 'TripHeadsign']
    numerical_features = ['Lat', 'Lon', 'Deviation', 'DirectionNum']

    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features),
            ('num', 'passthrough', numerical_features)
        ])
    
    # Step 5: Model pipeline
    model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('regressor', RandomForestRegressor(random_state=42))
    ])

        
    # Step 6: Train/test split and model training
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model.fit(X_train, y_train)

        
    # Step 7: Evaluation
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f'Mean Absolute Error on test set: {mae:.2f} minutes')

    return model 
def predict_trip_duration(new_data, model):
    # Convert new data into a DataFrame
    new_df = pd.DataFrame([new_data])
    
    # Ensure all required columns are present
    required_columns = ['Lat', 'Lon', 'Deviation', 'DirectionNum', 'RouteID', 'DirectionText', 'TripHeadsign']
    missing = set(required_columns) - set(new_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Predict duration
    predicted_duration = model.predict(new_df)[0]
    return round(predicted_duration, 2)

@app.before_request
def preload_training_model():
    global model
    if model is None:
        model = generate_training_model()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buses')
def buses():
    
    data = load_buses_data()
    for route_id, buses in data.items():
        # Sort buses by Lat and Lon (or any other criteria)
        buses.sort(key=lambda x: (x['Lat'], x['Lon']))
        # Add a unique ID for each bus in the route
        for i, bus in enumerate(buses):
            bus['BusID'] = f"{route_id}_{i}"
    # check if url is parametrized
    if 'RouteID' in request.args:
        route_id = request.args.get('RouteID')
        if route_id in data:
            data = {route_id: data[route_id]}
    elif 'TripHeadsign' in request.args:
        trip_sign = request.args.get('TripHeadsign')
        # Filter buses by TripSign
        filtered_data = {}
        for route_id, buses in data.items():
            filtered_buses = [bus for bus in buses if bus.get('TripHeadsign') == trip_sign]
            if filtered_buses:
                filtered_data[route_id] = filtered_buses
        # Check if any buses matched the filter
        if not filtered_data:
            return jsonify({"error": "No buses found with the specified TripHeadsign."})
        data = filtered_data
    return render_template('buses.html', data=data)


@app.route('/trains')
def trains():
    
    data = load_trains_data()
    # Filter by Line if provided in the URL parameters
    if 'Line' in request.args:
        line = request.args.get('Line')
        if line in data:
            data = {line: data[line]}
        else:
            return jsonify({"error": "No trains found for the specified Line."})
    # Filter by Destination if provided in the URL parameters
    elif 'DestinationName' in request.args:
        destination = request.args.get('DestinationName')
        filtered_data = {}
        for line, destinations in data.items():
            for dest, trains in destinations.items():
                if dest == destination:
                    filtered_data[line] = {dest: trains}
        # Check if any trains matched the filter
        if not filtered_data:
            return jsonify({"error": "No trains found for the specified Destination."})
        data = filtered_data    
    
    return render_template('trains.html', data=data)

@app.route('/buses_trips_predictions', methods=['GET'])
def bus_predictions():
    global model
    # Example new bus data
    new_bus_data = {
        "Lat": 38.8951,
        "Lon": -77.0364,
        "Deviation": 10.0,
        "DirectionNum": 1,
        "RouteID": "32",
        "DirectionText": "WEST",
        "TripHeadsign": "POTOMAC PARK"
    }

    # Predict the trip duration in minutes
    predicted_minutes = predict_trip_duration(new_bus_data, model)
    print(f"Predicted Trip Duration: {predicted_minutes} minutes")
    return render_template('bus_predictions.html', data=predicted_minutes)

@app.route('/buses_trips_predictions', methods=['POST'])
def bus_predictions_post():
    global model
    # Get the new bus data from the request
    form_data = request.form
    
    new_bus_data = {
        "Lat": form_data.get("Lat", 38.8951),
        "Lon": form_data.get("Lon", -77.0364),
        "Deviation": form_data.get("Deviation", 10.0),
        "DirectionNum": form_data.get("DirectionNum", 1),
        "RouteID": form_data.get("RouteID", "32"),
        "DirectionText": form_data.get("DirectionText", "WEST"),
        "TripHeadsign": form_data.get("TripHeadsign", "POTOMAC PARK")
    }
    
    # Predict the trip duration in minutes
    predicted_minutes = predict_trip_duration(new_bus_data, model)
    print(f"Predicted Trip Duration: {predicted_minutes} minutes")
    
    return render_template('bus_predictions.html', data=predicted_minutes)

def bus_predictions():
    global model
    # Example new bus data
    new_bus_data = {
        "Lat": 38.8951,
        "Lon": -77.0364,
        "Deviation": 10.0,
        "DirectionNum": 1,
        "RouteID": "32",
        "DirectionText": "WEST",
        "TripHeadsign": "POTOMAC PARK"
    }

    # Predict the trip duration in minutes
    predicted_minutes = predict_trip_duration(new_bus_data, model)
    print(f"Predicted Trip Duration: {predicted_minutes} minutes")
    return render_template('bus_predictions.html', data=predicted_minutes)

if __name__ == '__main__':
    app.run(debug=True)
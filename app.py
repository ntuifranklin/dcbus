from flask import Flask, render_template, jsonify
import requests
#base_url="http://api.wmata.com/Bus.svc/json/jBusPositions[?RouteID][&Lat][&Lon][&Radius]"
# [?RouteID][&Lat][&Lon][&Radius]
base_url="http://api.wmata.com/Bus.svc/json/jBusPositions"
api_key="296133456a6948218953320589a758b0"
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/buses')
def buses():
    params = "?"
    params += "api_key=" + api_key
    # Add other parameters as needed, e.g., RouteID, Lat, Lon, Radius
    params += "&RouteID=S2"  # Example RouteID
    api_url = base_url + params
    response = requests.get(api_url)
    data = response.json()  # Parse the JSON from the API
    print(data)  # Print the data to the console for debugging
    # Check if the response contains bus positions
    
    return render_template('buses.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)
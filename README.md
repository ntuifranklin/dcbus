# dcbus
![DC Bus Map](https://upload.wikimedia.org/wikipedia/commons/thumb/3/37/WMATA_system_map.svg/2471px-WMATA_system_map.svg.png)
# Demo
![DC Bus App](static/img/dcbus_app_screen_recording.gif)
# Details
Shows information about buses in dc.
When you open the app, it opens a map. You can zoom in and out of the map.
When you click on a location on the map, the gps coordiante for that map is sent to the api to list all bus stops in that location.

# Run

## activate the environment
```
dcbusenv\Scripts\activate.bat
```

## run flask
```
flask run --debug
```

## open localhost:5000
Open your browser at localhost:5000


import React, { useEffect, useState, useCallback } from "react";
import Map, { Source, Layer, Popup } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";

import { fetchDamageZones } from "../services/api";
import { connectWebSocket } from "../services/websocket";

const MAPBOX_TOKEN = process.env.REACT_APP_MAPBOX_TOKEN;


// --------------------------------------------------
// 166. MAP COMPONENT
// --------------------------------------------------
const DisasterMap = ({ activeEventId }) => {
  const [geoData, setGeoData] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [viewState, setViewState] = useState({
    longitude: 77.1025, // default India
    latitude: 28.7041,
    zoom: 5,
  });

  const [layerType, setLayerType] = useState("damage"); // toggle


  // --------------------------------------------------
  // 167. FETCH DAMAGE ZONES
  // --------------------------------------------------
  useEffect(() => {
    if (!activeEventId) return;

    const loadData = async () => {
      const data = await fetchDamageZones(activeEventId);
      console.log("API response:", data); // 🔥 trace step 1
      setGeoData(data);
    };

    loadData();
  }, [activeEventId]);


  // --------------------------------------------------
  // 170. REAL-TIME UPDATES (WebSocket)
  // --------------------------------------------------
  useEffect(() => {
    const ws = connectWebSocket((update) => {
      console.log("WebSocket update:", update);
      // optionally merge new GeoJSON
    });

    return () => ws.close();
  }, []);


  // --------------------------------------------------
  // 168. DAMAGE LAYER STYLE
  // --------------------------------------------------
  const damageLayer = {
    id: "damage-layer",
    type: "fill",
    paint: {
      "fill-color": [
        "match",
        ["get", "damage_level"],
        0, "#00FF00",   // green
        1, "#FFFF00",   // yellow
        2, "#FFA500",   // orange
        3, "#FF0000",   // red
        "#CCCCCC"
      ],
      "fill-opacity": 0.6,
    },
  };


  // SAR overlay (dummy style)
  const sarLayer = {
    id: "sar-layer",
    type: "fill",
    paint: {
      "fill-color": "#00FFFF",
      "fill-opacity": 0.3,
    },
  };


  // --------------------------------------------------
  // 169. CLICK HANDLER (POPUP)
  // --------------------------------------------------
  const onMapClick = useCallback((event) => {
    const feature = event.features && event.features[0];
    if (feature) {
      setSelectedFeature(feature);
    }
  }, []);


  return (
    <div style={{ width: "100%", height: "100%" }}>

      {/* 170. TOGGLE */}
      <div style={{ position: "absolute", zIndex: 1, padding: 10 }}>
        <button onClick={() => setLayerType("damage")}>Damage</button>
        <button onClick={() => setLayerType("sar")}>SAR</button>
      </div>

      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle="mapbox://styles/mapbox/satellite-streets-v12"
        mapboxAccessToken={MAPBOX_TOKEN}
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["damage-layer"]}
        onClick={onMapClick}
      >

        {/* 168. SOURCE + LAYER */}
        {geoData && (
          <Source id="damage-source" type="geojson" data={geoData}>
            <Layer {...(layerType === "damage" ? damageLayer : sarLayer)} />
          </Source>
        )}

        {/* 169. POPUP */}
        {selectedFeature && (
          <Popup
            longitude={selectedFeature.geometry.coordinates[0][0][0]}
            latitude={selectedFeature.geometry.coordinates[0][0][1]}
            onClose={() => setSelectedFeature(null)}
          >
            <div>
              <p><strong>Damage Level:</strong> {selectedFeature.properties.damage_level}</p>
              <p><strong>Population:</strong> {selectedFeature.properties.affected_population_estimate}</p>
              <p><strong>Assessed At:</strong> {selectedFeature.properties.assessed_at}</p>
            </div>
          </Popup>
        )}

      </Map>
    </div>
  );
};

export default DisasterMap;
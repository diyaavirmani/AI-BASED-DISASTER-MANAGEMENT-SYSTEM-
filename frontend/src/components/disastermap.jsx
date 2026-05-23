import React, { useEffect, useState, useCallback } from 'react';
import Map, { Source, Layer, Popup } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

import { fetchDamageZones } from '../services/api';
import { useWebSocket } from '../services/websocket';
import { API_BASE_URL, MAPBOX_TOKEN } from '../config';

const DAMAGE_LAYER = {
  id: 'damage-layer',
  type: 'fill',
  paint: {
    'fill-color': [
      'match',
      ['get', 'damage_level'],
      0, '#22c55e',
      1, '#eab308',
      2, '#f97316',
      3, '#ef4444',
      '#94a3b8'
    ],
    'fill-opacity': 0.72,
    'fill-outline-color': '#0f172a'
  }
};

const SAR_LAYER = {
  id: 'sar-layer',
  type: 'fill',
  paint: {
    'fill-color': '#0ea5e9',
    'fill-opacity': 0.35,
    'fill-outline-color': '#0284c7'
  }
};

const DisasterMap = ({ activeEventId }) => {
  const [geoData, setGeoData] = useState(null);
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [viewState, setViewState] = useState({
    longitude: 0,
    latitude: 20,
    zoom: 2
  });
  const [layerType, setLayerType] = useState('damage');

  const { latestMessage } = useWebSocket(`${API_BASE_URL.replace(/^http/, 'ws')}/ws/updates`);

  useEffect(() => {
    if (!activeEventId) {
      setGeoData(null);
      return;
    }

    const loadZones = async () => {
      try {
        const data = await fetchDamageZones(activeEventId);
        console.log('Fetched damage zones:', data);
        setGeoData(data);
      } catch (err) {
        console.error('Failed to load damage zones:', err);
        setGeoData(null);
      }
    };

    loadZones();
  }, [activeEventId]);

  useEffect(() => {
    if (!latestMessage || latestMessage.type !== 'damage_update') {
      return;
    }

    if (latestMessage.event_id !== activeEventId) {
      return;
    }

    console.log('Received real-time damage update:', latestMessage);

    if (latestMessage.geojson) {
      setGeoData(latestMessage.geojson);
      return;
    }

    setGeoData((prev) => {
      if (!prev || !prev.features || !latestMessage.feature) {
        return prev;
      }

      const updated = prev.features.map((feature) => {
        if (feature.properties?.zone_id === latestMessage.feature.properties?.zone_id) {
          return {
            ...feature,
            properties: {
              ...feature.properties,
              ...latestMessage.feature.properties
            }
          };
        }
        return feature;
      });

      return { ...prev, features: updated };
    });
  }, [latestMessage, activeEventId]);

  const onMapClick = useCallback((event) => {
    const feature = event.features?.[0];
    if (!feature) {
      setSelectedFeature(null);
      return;
    }

    setSelectedFeature({
      properties: feature.properties,
      lngLat: event.lngLat
    });
  }, []);

  if (!activeEventId) {
    return (
      <div className="card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ color: 'var(--color-text-secondary)', textAlign: 'center' }}>
          Select a disaster event to load the damage map.
        </div>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <div style={{ position: 'absolute', top: 16, left: 16, zIndex: 10, display: 'flex', gap: '0.5rem' }}>
        <button className="btn btn-secondary" onClick={() => setLayerType('damage')}>
          Damage
        </button>
        <button className="btn btn-secondary" onClick={() => setLayerType('sar')}>
          SAR
        </button>
      </div>

      <Map
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle="mapbox://styles/mapbox/satellite-streets-v12"
        mapboxAccessToken={MAPBOX_TOKEN}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={['damage-layer']}
        onClick={onMapClick}
      >
        {geoData && (
          <Source id="damage-source" type="geojson" data={geoData}>
            <Layer {...(layerType === 'damage' ? DAMAGE_LAYER : SAR_LAYER)} />
          </Source>
        )}

        {selectedFeature && (
          <Popup
            longitude={selectedFeature.lngLat[0]}
            latitude={selectedFeature.lngLat[1]}
            anchor="bottom"
            onClose={() => setSelectedFeature(null)}
          >
            <div style={{ minWidth: '160px' }}>
              <p style={{ margin: '0 0 0.5rem 0' }}><strong>Damage Level:</strong> {selectedFeature.properties.damage_level ?? 'N/A'}</p>
              <p style={{ margin: '0 0 0.5rem 0' }}><strong>Population:</strong> {selectedFeature.properties.affected_population_estimate ?? 'N/A'}</p>
              <p style={{ margin: 0 }}><strong>Assessed At:</strong> {selectedFeature.properties.assessed_at ?? 'Unknown'}</p>
            </div>
          </Popup>
        )}
      </Map>
    </div>
  );
};

export default DisasterMap;

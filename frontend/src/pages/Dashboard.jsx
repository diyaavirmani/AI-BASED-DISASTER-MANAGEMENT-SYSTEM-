import { useState, useEffect } from 'react';
import { useDisasterStore } from '../store/useDisasterStore';
import { API_BASE_URL } from '../config';
import DisasterMap from '../components/DisasterMap';
import MetricsPanel from '../components/MetricsPanel';
import AlertFeed from '../components/AlertFeed';
import ResourcePanel from '../components/ResourcePanel';

const Dashboard = () => {
  const [disasters, setDisasters] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const { setActiveEvent } = useDisasterStore();

  // Fetch active disasters on component mount
  useEffect(() => {
    fetchDisasters();
  }, []);

  const fetchDisasters = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/disasters`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setDisasters(data);

      // Auto-select first disaster if available
      if (data.length > 0) {
        handleEventSelect(data[0]);
      }
    } catch (err) {
      setError(err.message);
      console.error('Failed to fetch disasters:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleEventSelect = (event) => {
    setSelectedEvent(event);
    setActiveEvent(event.id, event);
  };

  const retryFetch = () => {
    fetchDisasters();
  };

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        flexDirection: 'column',
        gap: 'var(--spacing-md)'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '4px solid var(--color-surface)',
          borderTop: '4px solid var(--color-info)',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <p>Loading disaster data...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        padding: 'var(--spacing-xl)',
        textAlign: 'center'
      }}>
        <div style={{
          backgroundColor: 'var(--color-error)',
          color: 'white',
          padding: 'var(--spacing-lg)',
          borderRadius: 'var(--radius-lg)',
          marginBottom: 'var(--spacing-lg)',
          maxWidth: '500px'
        }}>
          <h3 style={{ marginBottom: 'var(--spacing-md)' }}>Failed to Load Data</h3>
          <p>{error}</p>
        </div>
        <button className="btn btn-primary" onClick={retryFetch}>
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div style={{
      padding: 'var(--spacing-lg)',
      height: '100vh',
      display: 'grid',
      gridTemplateColumns: '70% 30%',
      gridTemplateAreas: '"map panels"',
      gap: 'var(--spacing-lg)',
      overflow: 'hidden'
    }}>
      {/* Header with disaster selector */}
      <div style={{
        gridColumn: '1 / -1',
        marginBottom: 'var(--spacing-lg)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-md)'
      }}>
        <h1 style={{ margin: 0 }}>Disaster Management Dashboard</h1>
        <select
          value={selectedEvent?.id || ''}
          onChange={(e) => {
            const event = disasters.find(d => d.id === parseInt(e.target.value));
            if (event) handleEventSelect(event);
          }}
          style={{
            padding: 'var(--spacing-sm) var(--spacing-md)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-surface)',
            color: 'var(--color-text)',
            minWidth: '200px'
          }}
        >
          <option value="">Select a disaster event...</option>
          {disasters.map(disaster => (
            <option key={disaster.id} value={disaster.id}>
              {disaster.name} - {disaster.location}
            </option>
          ))}
        </select>
      </div>

      {/* Main map area */}
      <div style={{ gridArea: 'map', overflow: 'hidden' }}>
        <DisasterMap activeEventId={selectedEvent?.id} />
      </div>

      {/* Right panel with metrics, alerts, and resources */}
      <div style={{
        gridArea: 'panels',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--spacing-md)',
        overflow: 'auto'
      }}>
        <MetricsPanel selectedEvent={selectedEvent} />
        <AlertFeed selectedEvent={selectedEvent} />
        <ResourcePanel selectedEvent={selectedEvent} />
      </div>
    </div>
  );
};

export default Dashboard;
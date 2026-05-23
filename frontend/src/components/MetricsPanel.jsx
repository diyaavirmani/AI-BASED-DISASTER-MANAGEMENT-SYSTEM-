import { useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { API_BASE_URL } from '../config';

// Damage level colors matching the design system
const DAMAGE_COLORS = {
  'no-damage': 'var(--color-no-damage)',
  'minor': 'var(--color-minor)',
  'major': 'var(--color-major)',
  'destroyed': 'var(--color-destroyed)'
};

// Disaster type icons
const DISASTER_ICONS = {
  earthquake: '🌍',
  flood: '🌊',
  fire: '🔥',
  cyclone: '🌀',
  hurricane: '🌀',
  tornado: '🌪️',
  tsunami: '🌊',
  volcano: '🌋',
  landslide: '🏔️'
};

// Format large numbers
const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  }
  if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toLocaleString();
};

// Calculate time since disaster
const getTimeSinceDisaster = (startTime) => {
  const now = new Date();
  const disasterTime = new Date(startTime);
  const diffMs = now - disasterTime;
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  } else if (diffHours > 0) {
    return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  } else {
    const diffMinutes = Math.floor(diffMs / (1000 * 60));
    return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
  }
};

const MetricsPanel = ({ selectedEvent }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timeSince, setTimeSince] = useState('');

  // Update time since disaster every minute
  useEffect(() => {
    if (!selectedEvent) return;

    const updateTime = () => {
      setTimeSince(getTimeSinceDisaster(selectedEvent.start_time));
    };

    updateTime();
    const interval = setInterval(updateTime, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [selectedEvent]);

  // Fetch summary data when selectedEvent changes
  useEffect(() => {
    if (!selectedEvent) {
      setSummary(null);
      return;
    }

    const fetchSummary = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/disasters/${selectedEvent.id}/summary`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setSummary(data);
      } catch (err) {
        console.error('Failed to fetch disaster summary:', err);
        setSummary(null);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [selectedEvent]);

  if (!selectedEvent) {
    return (
      <div className="card">
        <h4>Damage Metrics</h4>
        <div style={{
          color: 'var(--color-text-secondary)',
          textAlign: 'center',
          padding: 'var(--spacing-xl)'
        }}>
          Select a disaster event to view metrics
        </div>
      </div>
    );
  }

  // Prepare chart data
  const chartData = summary ? [
    { name: 'No Damage', value: summary.zone_counts?.['no-damage'] || 0, color: DAMAGE_COLORS['no-damage'] },
    { name: 'Minor', value: summary.zone_counts?.minor || 0, color: DAMAGE_COLORS.minor },
    { name: 'Major', value: summary.zone_counts?.major || 0, color: DAMAGE_COLORS.major },
    { name: 'Destroyed', value: summary.zone_counts?.destroyed || 0, color: DAMAGE_COLORS.destroyed }
  ].filter(item => item.value > 0) : [];

  return (
    <div className="card">
      <h4>Damage Metrics</h4>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 'var(--spacing-xl)' }}>
          Loading metrics...
        </div>
      ) : summary ? (
        <div>
          {/* Event header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--spacing-md)',
            marginBottom: 'var(--spacing-lg)',
            paddingBottom: 'var(--spacing-md)',
            borderBottom: '1px solid var(--color-border)'
          }}>
            <span style={{ fontSize: '2rem' }}>
              {DISASTER_ICONS[selectedEvent.disaster_type] || '⚠️'}
            </span>
            <div>
              <h3 style={{ margin: 0, fontSize: 'var(--font-size-lg)' }}>
                {selectedEvent.name}
              </h3>
              <p style={{
                margin: 0,
                color: 'var(--color-text-secondary)',
                fontSize: 'var(--font-size-sm)'
              }}>
                {timeSince}
              </p>
            </div>
          </div>

          {/* Key metrics */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: 'var(--spacing-md)',
            marginBottom: 'var(--spacing-lg)'
          }}>
            <div>
              <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                Affected Area
              </div>
              <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'bold' }}>
                {formatNumber(summary.affected_area_km2 || 0)} km²
              </div>
            </div>

            <div>
              <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                Population Affected
              </div>
              <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'bold' }}>
                {formatNumber(summary.affected_population || 0)}
              </div>
            </div>

            {selectedEvent.magnitude && (
              <div>
                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                  Magnitude
                </div>
                <div style={{ fontSize: 'var(--font-size-lg)', fontWeight: 'bold' }}>
                  {selectedEvent.magnitude}
                </div>
              </div>
            )}
          </div>

          {/* Damage zones chart */}
          {chartData.length > 0 && (
            <div>
              <h5 style={{ marginBottom: 'var(--spacing-md)' }}>Damage Zone Breakdown</h5>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    outerRadius={60}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [value, 'Zones']} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      ) : (
        <div style={{
          color: 'var(--color-text-secondary)',
          textAlign: 'center',
          padding: 'var(--spacing-xl)'
        }}>
          Unable to load metrics
        </div>
      )}
    </div>
  );
};

export default MetricsPanel;
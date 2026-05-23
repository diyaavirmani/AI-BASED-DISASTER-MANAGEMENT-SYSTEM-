import { useState, useEffect, useRef } from 'react';
import { API_BASE_URL } from '../config';
import { useWebSocket } from '../services/websocket';

// Alert type configurations
const ALERT_TYPES = {
  satellite: { icon: '📡', color: 'var(--color-info)', label: 'Satellite' },
  crowdsource: { icon: '👥', color: 'var(--color-warning)', label: 'Crowdsource' },
  gdacs: { icon: '⚠️', color: 'var(--color-error)', label: 'Official' },
  resource: { icon: '🚁', color: 'var(--color-success)', label: 'Resource' }
};

// Filter options
const FILTERS = ['ALL', 'SATELLITE', 'CROWDSOURCE', 'OFFICIAL'];

// Format relative time
const getRelativeTime = (timestamp) => {
  const now = new Date();
  const alertTime = new Date(timestamp);
  const diffMs = now - alertTime;
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffDays > 0) {
    return `${diffDays}d ago`;
  } else if (diffHours > 0) {
    return `${diffHours}h ago`;
  } else if (diffMinutes > 0) {
    return `${diffMinutes}m ago`;
  } else {
    return 'Just now';
  }
};

const AlertFeed = ({ selectedEvent }) => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [unreadCount, setUnreadCount] = useState(0);
  const feedRef = useRef(null);
  const hasScrolledToTop = useRef(false);

  // WebSocket connection
  const { latestMessage, connected } = useWebSocket(`${API_BASE_URL.replace('http', 'ws')}/ws/alerts`);

  // Fetch initial alerts
  useEffect(() => {
    if (!selectedEvent) {
      setAlerts([]);
      return;
    }

    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/disasters/${selectedEvent.id}/alerts`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setAlerts(data.slice(0, 100)); // Limit to 100 alerts
      } catch (err) {
        console.error('Failed to fetch alerts:', err);
        setAlerts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, [selectedEvent]);

  // Handle WebSocket messages
  useEffect(() => {
    if (!latestMessage) {
      return;
    }

    setAlerts(prev => {
      const newAlerts = [latestMessage, ...prev].slice(0, 100);
      setUnreadCount(prevCount => prevCount + 1);
      return newAlerts;
    });
  }, [latestMessage]);

  // Handle scroll to clear unread counter
  const handleScroll = () => {
    if (feedRef.current && feedRef.current.scrollTop === 0 && !hasScrolledToTop.current) {
      setUnreadCount(0);
      hasScrolledToTop.current = true;
    } else if (feedRef.current && feedRef.current.scrollTop > 0) {
      hasScrolledToTop.current = false;
    }
  };

  // Filter alerts based on active filter
  const filteredAlerts = alerts.filter(alert => {
    if (activeFilter === 'ALL') return true;
    return alert.type === activeFilter.toLowerCase();
  });

  // Get severity color
  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'var(--color-error)';
      case 'major': return 'var(--color-major)';
      case 'minor': return 'var(--color-minor)';
      default: return 'var(--color-text-secondary)';
    }
  };

  if (!selectedEvent) {
    return (
      <div className="card">
        <h4>Alert Feed</h4>
        <div style={{
          color: 'var(--color-text-secondary)',
          textAlign: 'center',
          padding: 'var(--spacing-xl)'
        }}>
          Select a disaster event to view alerts
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 'var(--spacing-md)'
      }}>
        <h4 style={{ margin: 0 }}>
          Alert Feed
          {unreadCount > 0 && (
            <span style={{
              backgroundColor: 'var(--color-error)',
              color: 'white',
              borderRadius: '50%',
              padding: '2px 6px',
              fontSize: 'var(--font-size-xs)',
              marginLeft: 'var(--spacing-sm)'
            }}>
              {unreadCount}
            </span>
          )}
        </h4>
        <div style={{
          fontSize: 'var(--font-size-xs)',
          color: connected ? 'var(--color-success)' : 'var(--color-error)'
        }}>
          {connected ? '● Live' : '● Offline'}
        </div>
      </div>

      {/* Filter buttons */}
      <div style={{
        display: 'flex',
        gap: 'var(--spacing-xs)',
        marginBottom: 'var(--spacing-md)',
        flexWrap: 'wrap'
      }}>
        {FILTERS.map(filter => (
          <button
            key={filter}
            className={`btn ${activeFilter === filter ? 'btn-primary' : 'btn-secondary'}`}
            style={{
              fontSize: 'var(--font-size-xs)',
              padding: 'var(--spacing-xs) var(--spacing-sm)',
              minWidth: 'auto'
            }}
            onClick={() => setActiveFilter(filter)}
          >
            {filter}
          </button>
        ))}
      </div>

      {/* Alert feed */}
      <div
        ref={feedRef}
        onScroll={handleScroll}
        style={{
          maxHeight: '400px',
          overflowY: 'auto',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--spacing-sm)'
        }}
      >
        {loading ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
            color: 'var(--color-text-secondary)'
          }}>
            Loading alerts...
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: 'var(--spacing-xl)',
            color: 'var(--color-text-secondary)'
          }}>
            No alerts found
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
            {filteredAlerts.map(alert => (
              <div
                key={alert.id}
                style={{
                  padding: 'var(--spacing-sm)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'var(--color-surface-hover)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 'var(--spacing-sm)'
                }}
              >
                {/* Alert type icon */}
                <span style={{ fontSize: 'var(--font-size-lg)' }}>
                  {ALERT_TYPES[alert.type]?.icon || '📢'}
                </span>

                <div style={{ flex: 1 }}>
                  {/* Header with timestamp and type */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    <span style={{
                      fontSize: 'var(--font-size-xs)',
                      color: 'var(--color-text-secondary)'
                    }}>
                      {getRelativeTime(alert.timestamp)}
                    </span>
                    <span style={{
                      fontSize: 'var(--font-size-xs)',
                      backgroundColor: ALERT_TYPES[alert.type]?.color || 'var(--color-surface)',
                      color: 'white',
                      padding: '2px 6px',
                      borderRadius: 'var(--radius-sm)'
                    }}>
                      {ALERT_TYPES[alert.type]?.label || alert.type}
                    </span>
                  </div>

                  {/* Alert message */}
                  <div style={{
                    fontSize: 'var(--font-size-sm)',
                    marginBottom: 'var(--spacing-xs)'
                  }}>
                    {alert.message}
                  </div>

                  {/* Location and severity */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: 'var(--font-size-xs)'
                  }}>
                    {alert.location && (
                      <span style={{ color: 'var(--color-text-secondary)' }}>
                        📍 {alert.location}
                      </span>
                    )}
                    {alert.severity && (
                      <span style={{
                        color: getSeverityColor(alert.severity),
                        fontWeight: 'bold'
                      }}>
                        {alert.severity.toUpperCase()}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertFeed;
import { useEffect, useState } from 'react';
import { useDisasterStore } from '../store/useDisasterStore';
import { fetchAllocationRecommendations, deployResources } from '../services/api';

const RESOURCE_AVAILABILITY = {
  medicalTeams: 5,
  foodRations: 200
};

const DAMAGE_LEVEL_BADGE = {
  destroyed: 'var(--color-destroyed)',
  major: 'var(--color-major)',
  minor: 'var(--color-minor)',
  'no-damage': 'var(--color-no-damage)'
};

const formatPercent = (value) => `${Math.round((value || 0) * 100)}%`;

const ResourcePanel = ({ selectedEvent }) => {
  const [recommendations, setRecommendations] = useState([]);
  const [deploying, setDeploying] = useState(false);
  const [confirmModal, setConfirmModal] = useState(null);
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);

  const { addDeploymentRoute } = useDisasterStore();

  useEffect(() => {
    if (!selectedEvent) {
      setRecommendations([]);
      return;
    }

    const loadRecommendations = async () => {
      try {
        setLoading(true);
        const data = await fetchAllocationRecommendations(selectedEvent.id);
        const sorted = Array.isArray(data)
          ? data.sort((a, b) => (b.priority || b.priority_score || 0) - (a.priority || a.priority_score || 0))
          : [];
        setRecommendations(sorted.map((item, index) => ({ ...item, rank: index + 1, deployed: false })));
      } catch (err) {
        console.error('Failed to load resource recommendations:', err);
        setRecommendations([]);
      } finally {
        setLoading(false);
      }
    };

    loadRecommendations();
  }, [selectedEvent]);

  const handleDeployClick = (recommendation) => {
    setConfirmModal(recommendation);
  };

  const handleConfirmDeployment = async () => {
    if (!confirmModal || !selectedEvent) {
      return;
    }

    const deploymentPayload = {
      event_id: selectedEvent.id,
      zone_id: confirmModal.zone_id,
      recommended_resources: confirmModal.recommended_resources,
      priority: confirmModal.priority || confirmModal.priority_score,
      estimated_arrival_minutes: confirmModal.estimated_arrival_minutes || 30
    };

    const previousRecommendations = [...recommendations];
    setRecommendations((current) =>
      current.map((item) =>
        item.zone_id === confirmModal.zone_id ? { ...item, deployed: true } : item
      )
    );
    setDeploying(true);
    setConfirmModal(null);

    try {
      const result = await deployResources(deploymentPayload);
      addDeploymentRoute({
        eventId: selectedEvent.id,
        route: {
          zone_id: confirmModal.zone_id,
          deployed_at: new Date().toISOString(),
          resources: confirmModal.recommended_resources,
          status: 'deployed',
          apiResponse: result
        }
      });
      setToast('Deployment confirmed successfully.');
    } catch (err) {
      console.error('Deployment failed:', err);
      setRecommendations(previousRecommendations);
      setToast('Deployment failed. Please try again.');
    } finally {
      setDeploying(false);
      window.setTimeout(() => setToast(null), 4000);
    }
  };

  if (!selectedEvent) {
    return (
      <div className="card">
        <h4>Resource Allocation</h4>
        <div style={{ color: 'var(--color-text-secondary)', padding: 'var(--spacing-xl)', textAlign: 'center' }}>
          Select a disaster event to view resource recommendations.
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ position: 'relative' }}>
      <h4>Resource Allocation</h4>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 'var(--spacing-md)',
        marginBottom: 'var(--spacing-lg)',
        padding: 'var(--spacing-sm) 0'
      }}>
        <div>
          <div style={{ color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Medical Teams Available</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700' }}>{RESOURCE_AVAILABILITY.medicalTeams}</div>
        </div>
        <div>
          <div style={{ color: 'var(--color-text-secondary)', marginBottom: '0.25rem' }}>Food Rations Available</div>
          <div style={{ fontSize: '1.25rem', fontWeight: '700' }}>{RESOURCE_AVAILABILITY.foodRations}</div>
        </div>
      </div>

      {loading ? (
        <div style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: 'var(--spacing-xl)' }}>
          Loading deployment recommendations...
        </div>
      ) : recommendations.length === 0 ? (
        <div style={{ color: 'var(--color-text-secondary)', textAlign: 'center', padding: 'var(--spacing-xl)' }}>
          No allocation recommendations available for this event.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
          {recommendations.map((recommendation) => {
            const priority = recommendation.priority ?? recommendation.priority_score ?? 0;
            const badgeColor = DAMAGE_LEVEL_BADGE[recommendation.damage_level] || 'var(--color-text-secondary)';

            return (
              <div
                key={recommendation.zone_id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto',
                  gap: 'var(--spacing-md)',
                  padding: 'var(--spacing-md)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: recommendation.deployed ? 'rgba(148, 163, 184, 0.15)' : 'var(--color-surface-hover)',
                  border: '1px solid var(--color-border)',
                  opacity: recommendation.deployed ? 0.7 : 1
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)', marginBottom: '0.5rem' }}>
                    <span style={{ fontWeight: '700' }}>#{recommendation.rank}</span>
                    <span style={{ color: badgeColor, fontWeight: '700' }}>
                      Zone {recommendation.zone_id}
                    </span>
                    <span style={{
                      backgroundColor: badgeColor,
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: '999px',
                      fontSize: '0.75rem'
                    }}>
                      {formatPercent(priority)} priority
                    </span>
                  </div>

                  <div style={{ color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
                    Recommended resources:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '1.25rem', color: 'var(--color-text)', fontSize: '0.95rem' }}>
                    {(recommendation.recommended_resources || []).map((resource, idx) => (
                      <li key={idx}>{resource}</li>
                    ))}
                  </ul>

                  <div style={{ marginTop: '0.75rem', display: 'flex', gap: 'var(--spacing-md)', color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>
                    <span>ETA: {recommendation.estimated_arrival_minutes ?? 30} min</span>
                    {recommendation.rationale && <span>{recommendation.rationale}</span>}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                  <button
                    className="btn"
                    style={{
                      minWidth: '120px',
                      backgroundColor: recommendation.deployed ? 'var(--color-border)' : 'var(--color-info)',
                      color: recommendation.deployed ? 'var(--color-text)' : 'white',
                      cursor: recommendation.deployed ? 'default' : 'pointer'
                    }}
                    disabled={recommendation.deployed || deploying}
                    onClick={() => handleDeployClick(recommendation)}
                  >
                    {recommendation.deployed ? 'Deployed' : 'Deploy'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {confirmModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 50,
          padding: 'var(--spacing-lg)'
        }}>
          <div style={{
            width: '100%',
            maxWidth: '520px',
            backgroundColor: 'var(--color-background)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-xl)',
            padding: 'var(--spacing-xl)',
            boxShadow: '0 16px 40px rgba(0, 0, 0, 0.35)'
          }}>
            <h4 style={{ marginTop: 0 }}>Confirm Deployment</h4>
            <p style={{ color: 'var(--color-text-secondary)' }}>
              Deploy <strong>{confirmModal.recommended_resources?.join(', ') || 'resources'}</strong> to zone <strong>{confirmModal.zone_id}</strong> with priority <strong>{formatPercent(confirmModal.priority || confirmModal.priority_score)}</strong>?
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-sm)', marginTop: 'var(--spacing-lg)' }}>
              <button className="btn btn-secondary" onClick={() => setConfirmModal(null)}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleConfirmDeployment}
                disabled={deploying}
              >
                {deploying ? 'Deploying...' : 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div style={{
          position: 'absolute',
          top: 'var(--spacing-sm)',
          right: 'var(--spacing-sm)',
          backgroundColor: 'var(--color-surface)',
          color: 'var(--color-text)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--spacing-sm) var(--spacing-md)',
          boxShadow: '0 8px 20px rgba(0,0,0,0.2)'
        }}>
          {toast}
        </div>
      )}
    </div>
  );
};

export default ResourcePanel;

import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, auth } from '../services/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [apps, setApps] = useState<any[]>([]);
  const [user, setUser] = useState<{ username: string; role: string; email?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!auth.isLoggedIn()) {
      navigate('/login');
      return;
    }
    Promise.all([api.getApps(), api.getMe()])
      .then(([appsData, userData]: [any, any]) => {
        setApps(appsData);
        setUser(userData);
      })
      .catch((err: any) => {
        if (err.message === 'UNAUTHORIZED') {
          // Token invalid or expired — force re-login
          auth.clearToken();
          navigate('/login');
        }
        // Network error (backend down) — stay on dashboard, user data just won't show
      })
      .finally(() => setLoading(false));
  }, []);

  const handleLogout = () => {
    auth.clearToken();
    navigate('/login');
  };

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', margin: 0 }}>AetherAgents Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {user && (
            <div style={{ textAlign: 'right', fontSize: '0.875rem', color: '#4b5563' }}>
              <div style={{ fontWeight: 'bold', color: '#111827' }}>{user.username}</div>
              <div style={{ textTransform: 'capitalize', color: '#6b7280' }}>{user.role}</div>
            </div>
          )}
          <Link to="/deploy" style={{ backgroundColor: '#2563eb', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', textDecoration: 'none', fontWeight: 'bold' }}>
            Deploy New App
          </Link>
          <button
            onClick={handleLogout}
            style={{ backgroundColor: '#ef4444', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', border: 'none', cursor: 'pointer', fontWeight: 'bold' }}
          >
            Logout
          </button>
        </div>
      </div>

      <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead style={{ backgroundColor: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
            <tr>
              <th style={{ padding: '1rem' }}>App Name</th>
              <th style={{ padding: '1rem' }}>Version</th>
              <th style={{ padding: '1rem' }}>Status</th>
              <th style={{ padding: '1rem' }}>Nodes</th>
              <th style={{ padding: '1rem' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {apps.map(app => (
              <tr key={app.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                <td style={{ padding: '1rem', fontWeight: 'bold' }}>{app.name}</td>
                <td style={{ padding: '1rem' }}>{app.version}</td>
                <td style={{ padding: '1rem' }}>
                  <span style={{
                    padding: '0.25rem 0.5rem',
                    borderRadius: '999px',
                    fontSize: '0.875rem',
                    backgroundColor: app.status === 'Healthy' ? '#d1fae5' : '#fef3c7',
                    color: app.status === 'Healthy' ? '#065f46' : '#92400e'
                  }}>
                    {app.status}
                  </span>
                </td>
                <td style={{ padding: '1rem' }}>{app.nodes}</td>
                <td style={{ padding: '1rem' }}>
                  <Link to={`/apps/${app.id}`} style={{ color: '#2563eb', textDecoration: 'none', marginRight: '1rem' }}>View Details</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

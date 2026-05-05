import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';

export default function Dashboard() {
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Component Mount: Fetch from API
    api.getApps().then((data: any) => {
      setApps(data);
      setLoading(false);
    });
  }, []);

  if (loading) return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading apps...</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', margin: 0 }}>AetherAgents Dashboard</h1>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <Link to="/deploy" style={{ backgroundColor: '#2563eb', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', textDecoration: 'none', fontWeight: 'bold' }}>
            Deploy New App
          </Link>
          <Link to="/login" style={{ backgroundColor: '#ef4444', color: 'white', padding: '0.5rem 1rem', borderRadius: '4px', textDecoration: 'none', fontWeight: 'bold' }}>
            Logout
          </Link>
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

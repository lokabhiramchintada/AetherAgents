import React from 'react';
import { useParams, Link } from 'react-router-dom';

export default function AppDetail() {
  const { id } = useParams();

  // Mock data for the specific app
  const app = {
    id: id,
    name: 'Email Classifier',
    version: '1.0.0',
    status: 'Healthy',
    nodes: 2,
    ram: '145 MB',
    cpu: '2.4%',
    endpoints: [
      { name: 'CLI Usage', command: 'python main.py --help' },
      { name: 'Health Check', url: `http://vm-001:8001/health` }
    ]
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Link to="/dashboard" style={{ color: '#4b5563', textDecoration: 'none' }}>← Back to Dashboard</Link>
        <h1 style={{ margin: 0 }}>{app.name} <span style={{ fontSize: '1rem', fontWeight: 'normal', color: '#6b7280' }}>v{app.version}</span></h1>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem', marginBottom: '2rem' }}>
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#4b5563' }}>Status</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#10b981' }}></div>
            <span style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>{app.status}</span>
          </div>
        </div>
        <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginTop: 0, color: '#4b5563' }}>Performance</h3>
          <div><strong>CPU:</strong> {app.cpu}</div>
          <div><strong>RAM:</strong> {app.ram}</div>
        </div>
      </div>

      <div style={{ backgroundColor: 'white', padding: '1.5rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', marginBottom: '2rem' }}>
        <h3 style={{ marginTop: 0 }}>Lifecycle Controls</h3>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button style={{ backgroundColor: '#10b981', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Start</button>
          <button style={{ backgroundColor: '#ef4444', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Stop</button>
          <button style={{ backgroundColor: '#f59e0b', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Restart</button>
          <button style={{ backgroundColor: '#3b82f6', color: 'white', padding: '0.5rem 1rem', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>Scale Up</button>
        </div>
      </div>

      <div style={{ backgroundColor: '#1f2937', color: '#f3f4f6', padding: '1.5rem', borderRadius: '8px' }}>
        <h3 style={{ marginTop: 0, color: '#f9fafb' }}>CLI Endpoints</h3>
        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
          {app.endpoints.map(ep => (
            <div key={ep.name} style={{ marginBottom: '0.5rem' }}>
              <span style={{ color: '#9ca3af' }}># {ep.name}</span>
              <br/>
              {ep.command || ep.url}
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}

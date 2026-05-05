import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../services/api';

export default function Deploy() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [isDeploying, setIsDeploying] = useState(false);
  const [status, setStatus] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setIsDeploying(true);
    
    try {
      // Call the API wrapper, passing a callback to handle Kafka/deployment status updates
      await api.deployApp(file, (newStatus) => {
        setStatus(newStatus);
      });
      
      alert('Deployment successful!');
      navigate('/dashboard');
    } catch (error) {
      console.error("Deployment failed", error);
      setStatus('Deployment failed.');
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <Link to="/dashboard" style={{ color: '#4b5563', textDecoration: 'none' }}>← Back to Dashboard</Link>
        <h1 style={{ margin: 0 }}>Deploy New Application</h1>
      </div>

      <div style={{ backgroundColor: 'white', padding: '2rem', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <form onSubmit={handleDeploy} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Upload Application ZIP (*.aether.zip)</label>
            <div style={{ border: '2px dashed #d1d5db', padding: '2rem', textAlign: 'center', borderRadius: '8px', backgroundColor: '#f9fafb' }}>
              <input 
                type="file" 
                accept=".zip" 
                onChange={handleFileChange}
                style={{ display: 'block', margin: '0 auto' }}
              />
              <p style={{ marginTop: '1rem', color: '#6b7280', fontSize: '0.875rem' }}>
                ZIP must contain main.py, config.yaml, and requirements.txt at the root.
              </p>
            </div>
          </div>

          {status && (
            <div style={{ padding: '1rem', backgroundColor: '#eff6ff', color: '#1e3a8a', borderRadius: '4px' }}>
              {status}
            </div>
          )}

          <button 
            type="submit" 
            disabled={!file || isDeploying}
            style={{ 
              backgroundColor: !file || isDeploying ? '#9ca3af' : '#2563eb', 
              color: 'white', 
              padding: '0.75rem', 
              border: 'none', 
              borderRadius: '4px', 
              cursor: !file || isDeploying ? 'not-allowed' : 'pointer', 
              fontWeight: 'bold', 
              fontSize: '1rem' 
            }}
          >
            {isDeploying ? 'Deploying...' : 'Deploy App'}
          </button>
        </form>
      </div>
    </div>
  );
}

/**
 * API Service Configuration
 * 
 * Once the FastAPI backends (App Registry, Validator, User Management, etc.) are 
 * ready, you can simply un-comment the `fetch` calls in these functions.
 * All functions are built to return Promises so the UI natively handles async DB/API calls.
 */

// Update this to match your Gateway URL or specific microservice ports if not routing via Gateway
const BASE_URL = 'http://localhost:8000';

export const api = {
  // --- USER MANAGEMENT ---
  login: async (credentials: any) => {
    // return fetch(`${BASE_URL}/login`, { method: 'POST', body: JSON.stringify(credentials) }).then(res => res.json());
    
    // MOCK:
    return new Promise(resolve => setTimeout(() => resolve({ token: 'mock-jwt-token' }), 500));
  },
  
  register: async (userData: any) => {
    // return fetch(`${BASE_URL}/register`, { method: 'POST', body: JSON.stringify(userData) }).then(res => res.json());
    
    // MOCK:
    return new Promise(resolve => setTimeout(() => resolve({ success: true }), 500));
  },

  // --- APP REGISTRY ---
  getApps: async () => {
    // return fetch(`${BASE_URL}/apps/list`).then(res => res.json());
    
    // MOCK:
    return new Promise(resolve => setTimeout(() => resolve([
      { id: 'app-001', name: 'Email Classifier', version: '1.0.0', status: 'Healthy', nodes: 2 },
      { id: 'app-002', name: 'Data Scraper', version: '2.1.0', status: 'Degraded', nodes: 1 },
    ]), 500));
  },

  getAppDetails: async (id: string) => {
    // return fetch(`${BASE_URL}/apps/${id}`).then(res => res.json());
    
    // MOCK:
    return new Promise(resolve => setTimeout(() => resolve({
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
    }), 500));
  },

  // --- APP VALIDATOR & DEPLOYER ---
  deployApp: async (file: File, onStatusUpdate: (status: string) => void) => {
    // REAL IMPLEMENTATION:
    // const formData = new FormData();
    // formData.append('file', file);
    // 
    // You might use WebSockets or Server-Sent Events here to get real-time status updates 
    // from the Kafka queues (Validator -> Registry -> Deployer).
    // 
    // return fetch(`${BASE_URL}/apps/deploy`, { method: 'POST', body: formData }).then(res => res.json());

    // MOCK (Simulating the pipeline flow):
    onStatusUpdate('Uploading ZIP to Gateway...');
    await new Promise(r => setTimeout(r, 800));
    
    onStatusUpdate('App Validator: Checking structure & config...');
    await new Promise(r => setTimeout(r, 1200));

    onStatusUpdate('App Registry: Registering metadata & saving ZIP...');
    await new Promise(r => setTimeout(r, 1000));
    
    onStatusUpdate('App Deployer: Launching on VM pool...');
    await new Promise(r => setTimeout(r, 1500));
    
    return { success: true, appId: 'app-new' };
  },

  // --- LIFECYCLE MANAGER ---
  appAction: async (id: string, action: 'start' | 'stop' | 'restart' | 'scale') => {
    // return fetch(`${BASE_URL}/apps/${id}/${action}`, { method: 'POST' }).then(res => res.json());
    
    // MOCK:
    return new Promise(resolve => setTimeout(() => resolve({ success: true, message: `Command ${action} executed` }), 500));
  }
};

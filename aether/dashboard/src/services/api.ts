/**
 * API Service Configuration
 *
 * User Management runs on BASE_URL (port 8000) directly until the Gateway is built.
 * When Gateway is ready, it will proxy all routes — no frontend changes needed.
 */

const BASE_URL = 'http://localhost:8000';

// --- Token helpers (stored in localStorage) ---
export const auth = {
  getToken: (): string | null => localStorage.getItem('aether_token'),
  setToken: (token: string) => localStorage.setItem('aether_token', token),
  clearToken: () => localStorage.removeItem('aether_token'),
  isLoggedIn: (): boolean => !!localStorage.getItem('aether_token'),
};

function authHeaders(): HeadersInit {
  const token = auth.getToken();
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

export const api = {
  // --- USER MANAGEMENT ---
  login: async (credentials: { username: string; password: string }) => {
    const res = await fetch(`${BASE_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail ?? 'Login failed');
    }
    return res.json(); // { token, token_type, user_id, username, role }
  },

  register: async (userData: { username: string; password: string; email?: string; role?: string }) => {
    const res = await fetch(`${BASE_URL}/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail ?? 'Registration failed');
    }
    return res.json(); // UserResponse
  },

  getMe: async () => {
    const res = await fetch(`${BASE_URL}/me`, { headers: authHeaders() });
    if (res.status === 401) throw new Error('UNAUTHORIZED');
    if (!res.ok) throw new Error('Failed to fetch user profile');
    return res.json(); // UserResponse
  },

  listApiKeys: async () => {
    const res = await fetch(`${BASE_URL}/api-keys`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Failed to fetch API keys');
    return res.json(); // APIKeyResponse[]
  },

  createApiKey: async (label: string = 'default') => {
    const res = await fetch(`${BASE_URL}/api-keys`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ label }),
    });
    if (!res.ok) throw new Error('Failed to create API key');
    return res.json(); // CreateAPIKeyFullResponse (includes plaintext key — store it!)
  },

  deleteApiKey: async (keyId: string) => {
    const res = await fetch(`${BASE_URL}/api-keys/${keyId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error('Failed to revoke API key');
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

  /**
   * Calls the App Validator subsystem via the Gateway.
   * Gateway publishes to Kafka topic `app.upload`; Validator consumes and returns a ValidationReport.
   * Endpoint (validator team to implement): POST /apps/validate
   * Returns: { passed: boolean, errors: string[], warnings: string[] }
   */
  validateApp: async (file: File): Promise<{ passed: boolean; errors: string[]; warnings: string[] }> => {
    // REAL IMPLEMENTATION (un-comment when Gateway + App Validator are ready):
    // const formData = new FormData();
    // formData.append('file', file);
    // return fetch(`${BASE_URL}/apps/validate`, {
    //   method: 'POST',
    //   body: formData,
    // }).then(res => res.json());

    // MOCK — simulates the ValidationReport the validator team will return:
    await new Promise(r => setTimeout(r, 800));
    return { passed: true, errors: [], warnings: [] };
  },

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

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import apiKeyService from '../services/apiKeyService';
import useApiKeysStatus from '../hooks/useApiKeysStatus';
import { useDelegation } from '../hooks/useDelegation';
import DelegationStatus from '../components/DelegationStatus';
import DelegationDialog from '../components/DelegationDialog';
import './ApiKeysPage.css';

const ApiKeysDisabledMessage = ({ onRefresh, isRefreshing }) => (
  <div className="api-keys-disabled">
    <div className="disabled-message">
      <h2>🔑 API Keys Feature Not Available</h2>
      <p>
        The API keys feature is currently disabled on this instance of FuseVault.
      </p>
      <div className="refresh-section">
        <button 
          className="btn btn-secondary" 
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? 'Checking...' : 'Check Again'}
        </button>
        <p className="refresh-note">
          If you've just enabled API keys in the backend configuration, 
          click "Check Again" to refresh the status.
        </p>
      </div>
      <div className="info-box">
        <h3>What are API Keys?</h3>
        <p>
          API keys allow you to programmatically access your FuseVault assets and perform operations 
          without needing to connect your wallet each time. This is useful for:
        </p>
        <ul>
          <li>Building applications that integrate with FuseVault</li>
          <li>Automating asset management tasks</li>
          <li>Creating backend services that interact with your data</li>
          <li>Developing mobile applications</li>
        </ul>
      </div>
      <div className="info-box">
        <h3>For Administrators</h3>
        <p>
          To enable API keys, set <code>API_KEY_AUTH_ENABLED=true</code> in your backend configuration 
          and ensure <code>API_KEY_SECRET_KEY</code> is properly configured.
        </p>
      </div>
    </div>
  </div>
);

const ApiKeysPage = () => {
  const { account, isAuthenticated } = useAuth();
  const { loading: statusLoading, isEnabled, refresh: refreshStatus } = useApiKeysStatus({
    pollingInterval: 60000, // Poll every minute on API keys page
    refetchOnFocus: true
  });
  const { 
    isDelegated, 
    isLoading: delegationLoading, 
    isDelegationRequiredForApiKeys 
  } = useDelegation();
  
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCreatedKey, setShowCreatedKey] = useState(null);
  const [delegationDialogOpen, setDelegationDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    permissions: ['read'],
    expiresIn: 90,
    metadata: {}
  });

  // Check if API keys can be used (enabled + delegated if required)
  const canUseApiKeys = isEnabled && (!isDelegationRequiredForApiKeys() || isDelegated);
  
  useEffect(() => {
    if (isAuthenticated && canUseApiKeys) {
      fetchApiKeys();
    } else {
      setLoading(false);
    }
  }, [isAuthenticated, canUseApiKeys]);

  const fetchApiKeys = async () => {
    try {
      setLoading(true);
      const keys = await apiKeyService.listApiKeys();
      setApiKeys(keys);
      setError(null);
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('not enabled')) {
        // This shouldn't happen now since we check status first, but handle it anyway
        setError('API key authentication is not enabled on this server');
      } else {
        setError('Failed to fetch API keys');
        console.error('Error fetching API keys:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      
      // Calculate expiration date
      const expiresAt = new Date();
      expiresAt.setDate(expiresAt.getDate() + formData.expiresIn);
      
      const apiKeyData = {
        name: formData.name,
        permissions: formData.permissions,
        expires_at: expiresAt.toISOString(),
        metadata: {
          ...formData.metadata,
          createdBy: account,
          createdAt: new Date().toISOString()
        }
      };

      const createdKey = await apiKeyService.createApiKey(apiKeyData);
      
      // Show the created key to the user (only shown once)
      setShowCreatedKey(createdKey);
      setShowCreateForm(false);
      setFormData({
        name: '',
        permissions: ['read'],
        expiresIn: 90,
        metadata: {}
      });
      
      // Refresh the list
      await fetchApiKeys();
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('not enabled')) {
        setError('API key authentication is not enabled on this server');
      } else {
        setError('Failed to create API key');
      }
      console.error('Error creating API key:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeKey = async (keyName) => {
    if (!window.confirm(`Are you sure you want to revoke the API key "${keyName}"?`)) {
      return;
    }

    try {
      setLoading(true);
      await apiKeyService.revokeApiKey(keyName);
      await fetchApiKeys();
      setError(null);
    } catch (err) {
      if (err.response?.status === 400 && err.response?.data?.detail?.includes('not enabled')) {
        setError('API key authentication is not enabled on this server');
      } else {
        setError('Failed to revoke API key');
      }
      console.error('Error revoking API key:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionToggle = (permission) => {
    setFormData(prev => {
      const newPermissions = prev.permissions.includes(permission)
        ? prev.permissions.filter(p => p !== permission)
        : [...prev.permissions, permission];
      
      return { ...prev, permissions: newPermissions };
    });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    alert('API key copied to clipboard!');
  };

  if (!isAuthenticated) {
    return (
      <div className="api-keys-page">
        <div className="container">
          <h1>API Keys</h1>
          <p>Please connect your wallet to manage API keys.</p>
        </div>
      </div>
    );
  }

  // Show loading while checking status and delegation
  if (statusLoading || delegationLoading) {
    return (
      <div className="api-keys-page">
        <div className="container">
          <h1>API Keys</h1>
          <p>Checking API keys availability...</p>
        </div>
      </div>
    );
  }

  // Show disabled message if API keys are not enabled
  if (!isEnabled) {
    return (
      <div className="api-keys-page">
        <div className="container">
          <ApiKeysDisabledMessage 
            onRefresh={refreshStatus}
            isRefreshing={statusLoading}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="api-keys-page">
      <div className="container">
        <div className="page-header">
          <h1>API Keys</h1>
          <button 
            className="btn btn-primary"
            onClick={() => setShowCreateForm(true)}
            disabled={loading || !canUseApiKeys}
          >
            Create New API Key
          </button>
        </div>

        {/* Add delegation status if delegation is required */}
        {isDelegationRequiredForApiKeys() && (
          <DelegationStatus 
            onSetupClick={() => setDelegationDialogOpen(true)} 
          />
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {showCreatedKey && (
          <div className="api-key-created">
            <div className="warning-box">
              <h3>⚠️ Important: Save Your API Key</h3>
              <p>This is the only time you'll see this API key. Please copy and save it securely.</p>
              <div className="api-key-display">
                <code>{showCreatedKey.api_key}</code>
                <button 
                  className="btn btn-secondary"
                  onClick={() => copyToClipboard(showCreatedKey.api_key)}
                >
                  Copy
                </button>
              </div>
              <button 
                className="btn btn-primary"
                onClick={() => setShowCreatedKey(null)}
              >
                I've Saved My Key
              </button>
            </div>
          </div>
        )}

        {showCreateForm && (
          <div className="create-form-modal">
            <div className="modal-content">
              <h2>Create New API Key</h2>
              <form onSubmit={handleCreateApiKey}>
                <div className="form-group">
                  <label htmlFor="name">Key Name</label>
                  <input
                    type="text"
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., My Application Key"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Permissions</label>
                  <div className="permissions-grid">
                    {apiKeyService.getAvailablePermissions().map(({ value, label }) => (
                      <label key={value} className="permission-checkbox">
                        <input
                          type="checkbox"
                          checked={formData.permissions.includes(value)}
                          onChange={() => handlePermissionToggle(value)}
                        />
                        <span>{label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="expiresIn">Expires In (days)</label>
                  <select
                    id="expiresIn"
                    value={formData.expiresIn}
                    onChange={(e) => setFormData({ ...formData, expiresIn: parseInt(e.target.value) })}
                  >
                    <option value={30}>30 days</option>
                    <option value={90}>90 days</option>
                    <option value={180}>180 days</option>
                    <option value={365}>1 year</option>
                  </select>
                </div>

                <div className="form-actions">
                  <button type="submit" className="btn btn-primary" disabled={loading}>
                    Create API Key
                  </button>
                  <button 
                    type="button" 
                    className="btn btn-secondary"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <div className={`api-keys-list ${!canUseApiKeys ? 'disabled' : ''}`}>
          <h2>Your API Keys</h2>
          {loading ? (
            <p>Loading...</p>
          ) : apiKeys.length === 0 ? (
            <p>No API keys yet. Create your first one!</p>
          ) : (
            <div className="keys-table">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Permissions</th>
                    <th>Created</th>
                    <th>Last Used</th>
                    <th>Expires</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((key) => (
                    <tr key={key.name}>
                      <td>{key.name}</td>
                      <td>{apiKeyService.formatPermissions(key.permissions)}</td>
                      <td>{new Date(key.created_at).toLocaleDateString()}</td>
                      <td>{key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}</td>
                      <td>{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}</td>
                      <td>
                        <span className={`status ${key.is_active ? 'active' : 'inactive'}`}>
                          {key.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRevokeKey(key.name)}
                          disabled={!key.is_active || loading || !canUseApiKeys}
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="api-usage-info">
          <h2>Using Your API Keys</h2>
          <div className="code-example">
            <h3>Example Request</h3>
            <pre>
{`curl -X GET \\
  https://fusevault-backend.up.railway.app/assets/user/{wallet_address} \\
  -H 'X-API-Key: your_api_key_here'`}
            </pre>
          </div>
          <div className="info-box">
            <h3>Important Notes:</h3>
            <ul>
              <li>API keys are tied to your wallet address and can only access your assets</li>
              <li>For blockchain operations, you must first delegate permission to the FuseVault server</li>
              <li>Keep your API keys secure and never share them publicly</li>
              <li>Revoked keys cannot be restored</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Delegation Dialog */}
      <DelegationDialog
        isOpen={delegationDialogOpen}
        onClose={() => setDelegationDialogOpen(false)}
      />
    </div>
  );
};

export default ApiKeysPage;
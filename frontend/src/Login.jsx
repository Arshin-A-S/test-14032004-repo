import React, { useState } from 'react';
import './App.css';
import Login from './Login.jsx';
import Dashboard from './Dashboard.jsx';
import FileList from './FileList.jsx';
import UploadFile from './UploadFile.js';
import Navigation from './Navigation.js'; // Import our new navigation

function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' or 'files'
  const [refreshKey, setRefreshKey] = useState(0);

  const handleLoginSuccess = (loggedInUser) => {
    setUser(loggedInUser);
    setActiveTab('dashboard'); // Default to dashboard on login
  };

  const handleLogout = () => {
    setUser(null);
  };

  const handleUploadSuccess = () => {
    setRefreshKey(prevKey => prevKey + 1);
    setActiveTab('files'); // Switch to the file list after a successful upload
  };

  return (
    <div className="App">
      <header>
        <h1>Secure Data Governance Hub</h1>
        {user && (
          <div className="card">
            <p>Welcome, {user.id}!</p>
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </header>
      <main>
        {user ? (
          // ---- LOGGED-IN VIEW ----
          <>
            <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />
            
            {activeTab === 'dashboard' && (
              <div className="card">
                <Dashboard />
              </div>
            )}
            
            {activeTab === 'files' && (
              <>
                <div className="card">
                  <UploadFile user={user} onUploadSuccess={handleUploadSuccess} />
                </div>
                <div className="card">
                  <FileList user={user} key={refreshKey} />
                </div>
              </>
            )}
          </>
        ) : (
          // ---- LOGGED-OUT VIEW ----
          <div className="card">
            <Login onLoginSuccess={handleLoginSuccess} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
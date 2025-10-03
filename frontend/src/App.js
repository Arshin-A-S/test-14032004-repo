import React, { useState } from 'react';
import './App.css';
import Login from './Login.js';
import Dashboard from './Dashboard.js'; // Import the new Dashboard

function App() {
  const [user, setUser] = useState(null);

  const handleLoginSuccess = (loggedInUser) => {
    setUser(loggedInUser);
  };

  const handleLogout = () => {
    setUser(null);
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
          <div className="card">
            <Dashboard />
          </div>
        ) : (
          <div className="card">
            <Login onLoginSuccess={handleLoginSuccess} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
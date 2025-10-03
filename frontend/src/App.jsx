import React, { useState } from 'react';
import './App.css';
import Login from './Login.jsx';
import Dashboard from './Dashboard.jsx';
import FileList from './FileList.jsx';
import UploadFile from './UploadFile.jsx';
import Navigation from './Navigation.jsx';

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
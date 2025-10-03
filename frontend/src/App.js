import React, { useState } from 'react';
import './App.css';
import FileList from './FileList';
import Login from './Login';

function App() {
  const [user, setUser] = useState(null); // State to hold the logged-in user

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
          <>
            <div className="card">
              <UploadFile user={user} onUploadSuccess={handleUploadSuccess} />
            </div>
            <div className="card">
              <FileList user={user} key={refreshKey} />
            </div>
          </>
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
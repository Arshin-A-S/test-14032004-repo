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
      <header className="App-header">
        <h1>Secure Data Governance Hub</h1>
        {user && (
          // Show user info and logout button if logged in
          <div>
            <p>Welcome, {user.id}!</p>
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </header>
      <main>
        {user ? (
          // If user is logged in, show the file list
          <FileList user={user} />
        ) : (
          // Otherwise, show the login form
          <Login onLoginSuccess={handleLoginSuccess} />
        )}
      </main>
    </div>
  );
}

export default App;
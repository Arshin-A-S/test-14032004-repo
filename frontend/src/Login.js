import React, { useState } from 'react';
import apiClient from './api';

function Login({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [error, setError] = useState(null);

  const handleLogin = async (e) => {
    e.preventDefault(); // Prevent the form from reloading the page
    if (!username) {
      setError('Username is required.');
      return;
    }
    setError(null);

    try {
      const response = await apiClient.login(username);
      if (response.data.ok) {
        // Pass the user data to the parent component (App.js)
        onLoginSuccess(response.data.user);
      } else {
        setError(response.data.error || 'Login failed.');
      }
    } catch (err) {
      setError('Login failed. Please check the username or if the server is running.');
      console.error(err);
    }
  };

  return (
    <div>
      <h2>Login</h2>
      <form onSubmit={handleLogin}>
        <div>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter your username"
          />
        </div>
        <button type="submit">Login</button>
      </form>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </div>
  );
}

export default Login;
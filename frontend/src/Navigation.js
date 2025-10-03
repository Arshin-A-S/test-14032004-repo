import React from 'react';

function Navigation({ activeTab, setActiveTab }) {
  const navStyle = {
    marginBottom: '1rem',
    borderBottom: '1px solid #333',
    paddingBottom: '1rem',
  };

  const buttonStyle = (tabName) => ({
    margin: '0 10px',
    backgroundColor: activeTab === tabName ? '#007bff' : '#1a1a1a',
    color: 'white',
  });

  return (
    <nav style={navStyle}>
      <button style={buttonStyle('dashboard')} onClick={() => setActiveTab('dashboard')}>
        Dashboard
      </button>
      <button style={buttonStyle('files')} onClick={() => setActiveTab('files')}>
        Manage Files
      </button>
    </nav>
  );
}

export default Navigation;
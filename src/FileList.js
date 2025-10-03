import React, { useState, useEffect } from 'react';
import apiClient from './api';

function FileList({ user }) {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const getFiles = async () => {
      try {
        const response = await apiClient.listFiles();
        setFiles(response.data.files);
      } catch (err) {
        setError('Could not fetch files.');
        console.error(err);
      }
    };

    getFiles();
  }, []);

  const handleDownload = async (file) => {
    // A simple mock context. We can make this more dynamic later.
    const userContext = {
      location: 'chennai',
      device: 'web_browser',
      department: 'cs',
    };

    try {
      const response = await apiClient.downloadFile(user.id, file.id, userContext);
      
      // Create a URL for the downloaded file blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.orig_filename);
      
      // Append to the document, click, and then remove
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);

    } catch (err) {
      alert('Download failed. You may not have the required attributes to access this file.');
      console.error(err);
    }
  };

  if (error) {
    return <div style={{ color: 'red' }}>{error}</div>;
  }

  return (
    <div>
      <h2>Available Files</h2>
      {files.length === 0 ? (
        <p>No files found.</p>
      ) : (
        <ul>
          {files.map((file) => (
            <li key={file.id}>
              {file.orig_filename}
              <button onClick={() => handleDownload(file)} style={{ marginLeft: '10px' }}>
                Download
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default FileList;
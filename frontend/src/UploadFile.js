import React, { useState } from 'react';
import apiClient from './api';

function UploadFile({ user, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [policy, setPolicy] = useState('');
  const [message, setMessage] = useState('');

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !policy) {
      setMessage('Please select a file and enter a policy.');
      return;
    }
    setMessage('Uploading...');

    try {
      await apiClient.uploadFile(file, user.id, policy);
      setMessage(`File "${file.name}" uploaded successfully!`);
      if (onUploadSuccess) {
        onUploadSuccess();
      }
    } catch (err) {
      setMessage('Upload failed. Please try again.');
      console.error(err);
    }
  };

  return (
    <div>
      <h2>Upload a New File</h2>
      <form onSubmit={handleUpload}>
        <div>
          <input type="file" onChange={handleFileChange} />
        </div>
        <div>
          <input
            type="text"
            value={policy}
            onChange={(e) => setPolicy(e.target.value)}
            placeholder="e.g., role:prof and dept:cs"
          />
        </div>
        <button type="submit">Upload File</button>
      </form>
      {message && <p>{message}</p>}
    </div>
  );
}

export default UploadFile;
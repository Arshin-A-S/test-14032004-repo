import axios from 'axios';

// The base URL of your Flask backend
const API_URL = 'http://127.0.0.1:5000';

const apiClient = {
  /**
   * Fetches the list of files from the server.
   */
    listFiles: () => {
        return axios.get(`${API_URL}/list_files`);
    },

  /**
   * Logs in a user.
   */
    login: (username) => {
        return axios.post(`${API_URL}/login`, { username });
    },

  /**
   * Downloads a file.
   */
    downloadFile: (username, fileId, context) => {
        return axios.post(`${API_URL}/download`, {
            username,
            file_id: fileId,
            context,
        }, {
            responseType: 'blob',
        });
    },

    uploadFile: (file, username, policy) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('username', username);
        formData.append('policy', policy);
        return axios.post(`${API_URL}/upload`, formData);
    },

    getEvents: () => {
        return axios.get(`${API_URL}/api/events`);
    },
};

    
export default apiClient;
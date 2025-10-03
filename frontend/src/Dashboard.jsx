import React, { useState, useEffect } from 'react';
import apiClient from './api';

function Dashboard() {
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiClient.getEvents()
      .then(response => {
        setEvents(response.data.events);
        setIsLoading(false);
      })
      .catch(error => {
        console.error("Error fetching events:", error);
        setIsLoading(false);
      });
  }, []);

  if (isLoading) {
    return <p>Loading events...</p>;
  }

  return (
    <div>
      <h2>Recent Security Events</h2>
      <ul>
        {events.map(event => (
          <li key={event.id} style={{ color: event.is_anomaly ? 'red' : 'inherit' }}>
            <strong>User:</strong> {event.user} | 
            <strong>Action:</strong> {event.action} | 
            <strong>Timestamp:</strong> {new Date(event.timestamp).toLocaleString()}
            {event.is_anomaly && <strong> (ANOMALY DETECTED)</strong>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Dashboard;
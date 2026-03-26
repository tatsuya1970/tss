import { useState, useEffect } from 'react';
import { TrendSidebar } from './components/TrendSidebar';
import { Map } from './components/Map';
import { type TrendEvent } from './data/mockData';

function App() {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [events, setEvents] = useState<TrendEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Fetch data from backend API
  const fetchEvents = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/events');
      if (response.status === 429) {
        const errorData = await response.json();
        alert(errorData.detail);
        return;
      }
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const data = await response.json();
      setEvents(data);
    } catch (error) {
      console.error('Failed to fetch events:', error);
    } finally {
      setLoading(false);
    }
  };

  // Only fetch once on initial load. Users can manually refresh later.
  useEffect(() => {
    fetchEvents();
  }, []);

  const handleEventSelect = (id: string) => {
    setSelectedEventId(id);
  };

  return (
    <div className="app-container">
      <TrendSidebar 
        events={events}
        onEventSelect={handleEventSelect} 
        selectedEventId={selectedEventId} 
        onRefresh={fetchEvents}
        isLoading={loading}
      />
      <Map events={events} selectedEventId={selectedEventId} />
      
      {loading && (
        <div style={{ position: 'absolute', top: 20, left: '50%', transform: 'translateX(-50%)', background: 'rgba(0,0,0,0.8)', padding: '10px 20px', borderRadius: '20px', color: '#fff', zIndex: 9999, display: 'flex', alignItems: 'center', gap: '10px' }}>
          データを最新に更新しています...
        </div>
      )}
    </div>
  );
}

export default App;

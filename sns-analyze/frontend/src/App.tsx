import { useState, useEffect } from 'react';
import { TrendSidebar } from './components/TrendSidebar';
import { Map } from './components/Map';
import { type TrendEvent } from './data/mockData';

function App() {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [events, setEvents] = useState<TrendEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const params = new URLSearchParams(window.location.search);
  const initialLat = params.get('lat') ? parseFloat(params.get('lat')!) : undefined;
  const initialLng = params.get('lng') ? parseFloat(params.get('lng')!) : undefined;
  const initialZoom = params.get('zoom') ? parseInt(params.get('zoom')!) : undefined;
  const mapOnly = params.get('maponly') === 'true';

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

  // 初回ロード + 1時間ごとに自動更新
  useEffect(() => {
    fetchEvents();
    const timer = setInterval(fetchEvents, 60 * 60 * 1000);
    return () => clearInterval(timer);
  }, []);

  const handleEventSelect = (id: string) => {
    setSelectedEventId(id);
  };

  return (
    <div className="app-container">
      {!mapOnly && (
        <TrendSidebar
          events={events}
          onEventSelect={handleEventSelect}
          selectedEventId={selectedEventId}
          onRefresh={fetchEvents}
          isLoading={loading}
        />
      )}
      <Map events={events} selectedEventId={selectedEventId} initialLat={initialLat} initialLng={initialLng} initialZoom={initialZoom} />
      
      {loading && (
        <div style={{ position: 'absolute', top: 20, left: '50%', transform: 'translateX(-50%)', background: 'rgba(0,0,0,0.8)', padding: '10px 20px', borderRadius: '20px', color: '#fff', zIndex: 9999, display: 'flex', alignItems: 'center', gap: '10px' }}>
          データを最新に更新しています...
        </div>
      )}
    </div>
  );
}

export default App;

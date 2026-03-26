import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { type TrendEvent } from '../data/mockData';
import { useEffect } from 'react';
import { Flame } from 'lucide-react';

const createCustomIcon = (heatScore: number, category: string) => {
  let color = 'var(--accent)';
  if (category === 'event') color = 'var(--cat-event)';
  if (category === 'gourmet') color = 'var(--cat-gourmet)';
  if (category === 'incident') color = 'var(--cat-incident)';
  if (category === 'other') color = 'var(--cat-other)';

  // Scale marker size based on heat
  const size = Math.max(20, (heatScore / 100) * 40);

  return L.divIcon({
    className: 'custom-icon',
    html: `<div class="pulse-marker" style="width: ${size}px; height: ${size}px; background-color: ${color}; box-shadow: 0 0 ${size}px ${color};"></div>`,
    iconSize: [size, size],
    iconAnchor: [size/2, size/2],
  });
};

type Props = {
  events: TrendEvent[];
  selectedEventId: string | null;
}

const MapController = ({ events, selectedEventId }: { events: TrendEvent[], selectedEventId: string | null }) => {
  const map = useMap();
  
  useEffect(() => {
    if (selectedEventId) {
      const target = events.find(e => e.id === selectedEventId);
      if (target) {
        map.setView([target.lat, target.lng], 16, { animate: true });
      }
    }
  }, [selectedEventId, events, map]);

  return null;
};

export const Map = ({ events, selectedEventId }: Props) => {
  return (
    <div className="map-container">
      <MapContainer 
        center={[34.3853, 132.4553]} // Hiroshima City Center
        zoom={11} 
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        />
        
        {events.map(event => (
          <Marker 
            key={event.id} 
            position={[event.lat, event.lng]}
            icon={createCustomIcon(event.heatScore, event.category)}
          >
            <Popup closeButton={false}>
              <div className="popup-content">
                <h3>{event.name}</h3>
                <p>{event.description}</p>
                <div className="popup-heat">
                  <Flame size={14} />
                  Heat Score: {event.heatScore}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
        
        <MapController events={events} selectedEventId={selectedEventId} />
      </MapContainer>
    </div>
  );
};

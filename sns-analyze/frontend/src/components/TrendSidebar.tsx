import { Flame, MapPin, RefreshCw } from 'lucide-react';
import { type TrendEvent } from '../data/mockData';

type Props = {
  events: TrendEvent[];
  onEventSelect: (eventId: string) => void;
  selectedEventId: string | null;
  onRefresh: () => void;
  isLoading: boolean;
}

export const TrendSidebar = ({ events, onEventSelect, selectedEventId, onRefresh, isLoading }: Props) => {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="brand" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <MapPin size={28} color="#38bdf8" />
            <span style={{ fontSize: '1.5rem', fontWeight: 700 }}>GeoTrend</span>
          </div>
          <button 
            className="refresh-btn" 
            onClick={onRefresh} 
            disabled={isLoading}
            style={{ 
              background: 'rgba(255,255,255,0.05)', 
              border: '1px solid rgba(255,255,255,0.1)', 
              color: 'var(--text-main)',
              padding: '8px',
              borderRadius: '8px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              transition: 'background 0.2s'
            }}
            title="最新のデータを取得 (APIを利用します)"
          >
            <RefreshCw size={18} className={isLoading ? "spinning" : ""} />
          </button>
        </div>
        <p className="sidebar-desc">
          SNSの投稿データからリアルタイムに盛り上がっている場所やイベントを特定。
        </p>
      </div>
      
      <div className="trend-list">
        {events.length === 0 ? (
          <div style={{color: 'var(--text-muted)', textAlign: 'center', marginTop: '20px'}}>No events found.</div>
        ) : null}
        
        {[...events]
          .sort((a, b) => b.heatScore - a.heatScore)
          .map((event) => (
          <div key={event.id} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div 
              className="trend-card"
              style={{ 
                borderColor: event.id === selectedEventId ? 'var(--accent)' : ''
              }}
              onClick={() => onEventSelect(event.id)}
            >
              <div className="trend-card-header">
                <div className="trend-title">{event.name}</div>
                <div className="category-badge cat-event" style={{
                  color: `var(--cat-${event.category})`,
                  borderColor: `var(--cat-${event.category})`
                }}>
                  {event.category.toUpperCase()}
                </div>
              </div>
              
              <p className="trend-desc">{event.description}</p>
              
              <div className="pill-container">
                {event.keywords.map(kw => (
                  <span key={kw} className="tag-pill">{kw}</span>
                ))}
              </div>
              
              <div className="trend-footer">
                <span className="trend-heat">
                  <Flame size={14} /> Heat: {event.heatScore}
                </span>
                <span>{event.trendingTime}</span>
              </div>
            </div>

            {/* Expander for Tweets (Only visible if selected) */}
            {selectedEventId === event.id && event.tweets && event.tweets.length > 0 && (
              <div className="tweet-feed-container">
                {event.tweets.map(tweet => (
                  <div key={tweet.id} className="tweet-ui-card">
                    <div className="tweet-header">
                      <div className="author-avatar" style={{ backgroundColor: tweet.platform === 'Instagram' ? '#E1306C' : '#1d9bf0' }}>{tweet.author_name[0]}</div>
                      <div className="author-info">
                        <span className="author-name">{tweet.author_name}</span>
                        <span className="author-handle">@{tweet.author_username}</span>
                      </div>
                    </div>
                    <p className="tweet-text">{tweet.text}</p>
                    <div className="tweet-footer">
                      <span className="tweet-time">{tweet.created_at}</span>
                      <a 
                        href={tweet.url && tweet.url !== "#" ? tweet.url : (tweet.platform === "Instagram" ? "https://instagram.com" : "https://x.com")} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="tweet-link"
                        style={{ 
                          padding: '4px 8px', 
                          backgroundColor: tweet.platform === "Instagram" ? 'rgba(225, 48, 108, 0.1)' : 'rgba(29, 155, 240, 0.1)', 
                          color: tweet.platform === "Instagram" ? '#E1306C' : '#1d9bf0',
                          borderRadius: '99px',
                          textDecoration: 'none',
                          fontWeight: 600
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        {tweet.platform === "Instagram" ? "Instagramで見る" : "Xで見る"}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

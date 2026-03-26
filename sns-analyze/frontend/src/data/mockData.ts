export interface TweetInfo {
  id: string;
  text: string;
  url: string;
  created_at: string;
  author_name: string;
  author_username: string;
  platform?: string;
}

export interface TrendEvent {
  id: string;
  name: string;
  category: 'event' | 'gourmet' | 'incident' | 'other';
  lat: number;
  lng: number;
  heatScore: number; 
  description: string;
  keywords: string[];
  trendingTime: string;
  tweetUrl?: string;
  tweets?: TweetInfo[];
  platform?: string;
}

export const mockEvents: TrendEvent[] = [];

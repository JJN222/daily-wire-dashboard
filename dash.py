import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import openai
import json
import time
from typing import Dict, List, Tuple
import isodate
# Add these lines after the existing imports at the top of dashboard.py
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get API keys from environment
DEFAULT_YOUTUBE_KEYS = [
    os.getenv('YOUTUBE_API_KEY', ''),
    os.getenv('YOUTUBE_API_KEY_2', ''),
    os.getenv('YOUTUBE_API_KEY_3', '')
]
DEFAULT_YOUTUBE_KEYS = [key for key in DEFAULT_YOUTUBE_KEYS if key]  # Remove empty keys
DEFAULT_OPENAI_KEY = os.getenv('OPENAI_API_KEY', '')

# Page config
st.set_page_config(
    page_title="Multi-Channel Competitor Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS based on your design system
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
  --primary-text: #221F1F;
  --accent-blue: #BCE5F7;
  --secondary-beige: #E6DDC1;
  --background: #FFFFFF;
  --footer-grey: #666666;
}

.main .block-container {
  padding-top: 2rem;
  max-width: 1400px;
  padding-left: 3rem;
  padding-right: 3rem;
}

/* Hero section */
.dashboard-header {
  font-family: 'Inter', sans-serif;
  font-size: 72px;
  font-weight: 900;
  text-transform: uppercase;
  color: var(--primary-text);
  line-height: 0.9;
  letter-spacing: -3px;
  margin-bottom: 1rem;
}

.dashboard-header .accent {
  color: var(--accent-blue);
}

.subheader {
  font-family: 'Inter', sans-serif;
  font-size: 24px;
  font-weight: 300;
  color: var(--primary-text);
  margin-bottom: 2rem;
}

/* Metric cards */
.metric-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.metric-card h3 {
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #666;
  margin-bottom: 0.5rem;
}

.metric-card .value {
  font-family: 'Inter', sans-serif;
  font-size: 32px;
  font-weight: 800;
  color: var(--primary-text);
}

.metric-card .change {
  font-family: 'Inter', sans-serif;
  font-size: 14px;
  font-weight: 500;
  margin-top: 0.5rem;
}

.metric-card .change.positive {
  color: #10b981;
}

.metric-card .change.negative {
  color: #ef4444;
}

/* Buttons */
.stButton > button {
  background: var(--accent-blue);
  color: var(--primary-text);
  border: none;
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 4px;
  padding: 0.75rem 1.5rem;
  transition: all 0.3s ease;
}

.stButton > button:hover {
  background: var(--primary-text);
  color: var(--accent-blue);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* Section headers */
h1, h2, h3 {
  font-family: 'Inter', sans-serif;
  font-weight: 800;
  color: var(--primary-text);
}

/* AI Analysis box */
.ai-analysis {
  background: #f8f9fa;
  border-left: 4px solid var(--accent-blue);
  padding: 1.5rem;
  margin: 1.5rem 0;
  font-family: 'Inter', sans-serif;
  border-radius: 4px;
}

.ai-analysis h4 {
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 1rem;
  color: var(--primary-text);
}

/* Data tables */
.dataframe {
  font-family: 'Inter', sans-serif !important;
  font-size: 14px;
}

.dataframe th {
  background-color: var(--secondary-beige) !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 2rem;
  border-bottom: 2px solid #e0e0e0;
}

.stTabs [data-baseweb="tab"] {
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stTabs [aria-selected="true"] {
  color: var(--accent-blue);
  border-bottom: 3px solid var(--accent-blue);
}
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'youtube_data' not in st.session_state:
    st.session_state.youtube_data = {}
if 'current_key_index' not in st.session_state:
    st.session_state.current_key_index = 0
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None
if 'ai_analysis' not in st.session_state:
    st.session_state.ai_analysis = {}

# Channel configurations for both dashboards
POLITICAL_CHANNELS = {
    'Megyn Kelly': 'UCzJXNzqz6VMHSNInQt_7q6w',
    'Bill Maher': 'UCy6kyFxaMqGtpE3pQTflK8A',
    'The Daily Show': 'UCwWhs_6x42TyRM4Wstoq8HA',
    'David Pakman Show': 'UCvixJtaXuNdMPUGdOPcY8Ag',
    'Michael Knowles': 'UCr4kgAUTFkGIwlWSodg43QA',
    'The Weekly Show with Jon Stewart': 'UCQlJ7XpBtiMLKNSd4RAJmRQ',
    'Brian Tyler Cohen': 'UCQANb2YPwAtK-IQJrLaaUFw',
    'Nick Freitas': 'UCPFzA28Hw9tYDxXAeidDk6w',
    'Matt Walsh': 'UCO01ytfzgXYy4glnPJm4PPQ',
    'Ben Shapiro': 'UCnQC_G5Xsjhp9fEJKuIcrSw',
    'Timcast IRL': 'UCLwNTXWEjVd2qIHLcXxQWxA',
    'Benny Johnson': 'UCLdP3jmBYe9lAZQbY6OSYjw',
    'Candace Owens': 'UCL0u5uz7KZ9q-pe-VC8TY-w',
    'Dr. Jordan B. Peterson': 'UCL_f53ZEJxp8TtlOkHwMV9Q',
    'The Rubin Report': 'UCJdKr0Bgd_5saZYqLCa9mng',
    'Tucker Carlson': 'UCGttrUON87gWfU6dMWm1fcA',
    'Amala Ekpunobi': 'UCgEvEKgmQ-CHPIeOSaGCffw',
    'The Bulwark': 'UCG4Hp1KbGw4e02N7FpPXDgQ',
    'Charlie Kirk': 'UCfaIu2jO-fppCQV_lchCRIQ',
    'Brett Cooper': 'UCdFcGPb4xQ6X4QOoRU6ROYw',
    'Trish Regan': 'UCBlMo25WDUKJNQ7G8sAk4Zw',
    'The Officer Tatum': 'UCaYw_yJ_YLPEv6zR2c7hgHA',
    'Piers Morgan Uncensored': 'UCatt7TBjfBkiJWx8khav_Gg',
    'MeidasTouch': 'UC9r9HYFxEQOBXSopFS61ZWg',
    'Destiny': 'UC554eY5jNUfDq3yDOJYirOQ',
    'LastWeekTonight': 'UC3XTzVzaHQEd30rQbuvCtTQ',
    'The Majority Report w/ Sam Seder': 'UC-3jIAlnQmbbVMV6gR7K8aQ'
}

SPORTS_CHANNELS = {
    'Josh Pate\'s College Football Show': 'UCG-q_MDEWqrijzr1VPLEPYg',
    'On3': 'UCn2g2Wy8uiE9BhDPV4knT7A',
    'FortunateYouth': 'UCJn33SOv86632dLg_qWIcg',
    'Adapt & Respond with RJ Young': 'UC2g1DShTjHNcjBQ-PC-4aHA',
    'Cover 3 Podcast': 'UCODwphyohBn9u8-FWWfbQ7g',
    'CFB ON FOX': 'UCpwix-O6ceqMgdxhqlynzFA',
    'The Film Guy Network': 'UCqipe2jOlQZke4AN3-K9DJA',
    'Bleacher Report': 'UC9-OpMMVoNP5o10_Iyq7Ndw',
    'SEC Shorts': 'UCUOzVgb9Q8AgZjJlYcLWztQ',
    'Locked On College Football': 'UCqNQsWmyf0LCFUkr01QZ2LQ',
    'Strictly Football': 'UCGAOAB1tD432c5pyXMzS-6w',
    'College Football City': 'UCrjdiWSTYMLEHGYs5yfp56Q',
    'MattBeGreat': 'UCCQfkgVy-f814HGAwKQFPaw',
    'See Ball Get Ball with David Pollack': 'UC3-r8FzHqjr-O3KvPU26ZEA',
    'Crain & Company': 'UC-LeIYApj-NTHYGAzU4cPBQ'
}

# Define default channels for each dashboard
DEFAULT_POLITICAL_CHANNELS = [
    'Ben Shapiro',
    'Matt Walsh', 
    'Michael Knowles',
]

DEFAULT_SPORTS_CHANNELS = [
    'Crain & Company',
    'Josh Pate\'s College Football Show',
    'SEC Shorts'
]

# Add caching for YouTube data
@st.cache_data(ttl=21600)  # Cache for 6 hours
def fetch_all_channels_data(channel_list, start_date, api_key, channels_dict):
    """Fetch data for all channels with caching"""
    all_videos = []
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    for channel_name in channel_list:
        channel_id = channels_dict[channel_name]
        try:
            videos = fetch_channel_videos(youtube, channel_id, start_date)
            for video in videos:
                video['channel'] = channel_name
                all_videos.append(video)
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                continue
            else:
                continue
        except Exception as e:
            continue
        time.sleep(0.5)  # Rate limiting
    
    return all_videos

# Sidebar configuration
with st.sidebar:
    st.markdown('<h2 style="font-family: Inter; font-weight: 800;">Configuration</h2>', unsafe_allow_html=True)
    
    # Dashboard Type Selector
    st.markdown('<h3 style="font-family: Inter; font-weight: 700;">Dashboard Type</h3>', unsafe_allow_html=True)
    dashboard_type = st.selectbox(
        "Select Dashboard",
        ["Ben Shapiro (Political)", "Crain & Co (Sports)"],
        index=0
    )
    
    # Set channels and defaults based on dashboard type
    if dashboard_type == "Ben Shapiro (Political)":
        CHANNELS = POLITICAL_CHANNELS
        DEFAULT_CHANNELS = DEFAULT_POLITICAL_CHANNELS
        dashboard_focus = "political"
    else:
        CHANNELS = SPORTS_CHANNELS
        DEFAULT_CHANNELS = DEFAULT_SPORTS_CHANNELS
        dashboard_focus = "sports"
    
    # Use API keys directly from environment
    youtube_api_key = DEFAULT_YOUTUBE_KEYS[st.session_state.current_key_index] if DEFAULT_YOUTUBE_KEYS else ''
    openai_api_key = DEFAULT_OPENAI_KEY
    
    st.markdown('<h3 style="font-family: Inter; font-weight: 700;">Time Range</h3>', unsafe_allow_html=True)
    time_range = st.selectbox(
        "Select Analysis Period",
        ["Last 7 Days", "Last 14 Days", "Last 30 Days", "Last 90 Days"],
        index=0
    )
    
    # Calculate and display the actual date range (excluding today)
    end_date = datetime.now() - timedelta(days=1)  # Yesterday
    if time_range == "Last 7 Days":
        start_date = end_date - timedelta(days=6)  # 7 days total
    elif time_range == "Last 14 Days":
        start_date = end_date - timedelta(days=13)  # 14 days total
    elif time_range == "Last 30 Days":
        start_date = end_date - timedelta(days=29)  # 30 days total
    else:  # Last 90 Days
        start_date = end_date - timedelta(days=89)  # 90 days total
    
    # Display the date range
    st.markdown(f"**Date Range:** {start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}")
    
    st.markdown("---")
    
    st.markdown('<h3 style="font-family: Inter; font-weight: 700;">Channels</h3>', unsafe_allow_html=True)
    selected_channels = st.multiselect(
        "Select Channels to Analyze",
        list(CHANNELS.keys()),
        default=DEFAULT_CHANNELS
    )
    
    st.markdown("---")
    
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()  # Clear cache to force refresh
        st.rerun()

# Dynamic header based on dashboard type
if dashboard_type == "Ben Shapiro (Political)":
    header_text = "SHORTHAND STUDIOS<span style='color: #BCE5F7;'>.</span>"
    subheader_text = "DAILY WIRE COMPETITOR ANALYTICS DASHBOARD"
    description_text = "Real-time YouTube Performance Tracking & Strategic Insights"
else:
    header_text = "CRAIN & COMPANY<span style='color: #BCE5F7;'>.</span>"
    subheader_text = "SPORTS CONTENT ANALYTICS DASHBOARD"
    description_text = "College Football & Sports YouTube Performance Analysis"

st.markdown(f"""
    <div style="font-family: 'Inter', sans-serif;">
        <div style="font-size: 96px; font-weight: 900; text-transform: uppercase; color: #221F1F; line-height: 0.9; letter-spacing: -4px;">
            {header_text}
        </div>
        <div style="font-size: 36px; font-weight: 700; text-transform: uppercase; color: #221F1F; margin-top: 20px; letter-spacing: -1px;">
            {subheader_text}
        </div>
        <div style="font-size: 20px; font-weight: 300; color: #221F1F; margin-top: 15px;">
            {description_text}
        </div>
    </div>
""", unsafe_allow_html=True)

# Helper functions
def get_time_range_dates(time_range: str) -> Tuple[datetime, datetime]:
    """Convert time range string to datetime objects (excluding today)"""
    end_date = datetime.now() - timedelta(days=1)  # Yesterday at current time
    end_date = end_date.replace(hour=23, minute=59, second=59)  # End of yesterday
    
    if time_range == "Last 7 Days":
        start_date = end_date - timedelta(days=6)
    elif time_range == "Last 14 Days":
        start_date = end_date - timedelta(days=13)
    elif time_range == "Last 30 Days":
        start_date = end_date - timedelta(days=29)
    else:  # Last 90 Days
        start_date = end_date - timedelta(days=89)
    
    start_date = start_date.replace(hour=0, minute=0, second=0)  # Start of day
    
    return start_date, end_date

def fetch_channel_videos(youtube, channel_id: str, start_date: datetime, max_results: int = 100) -> List[Dict]:
    """Fetch ALL videos from a channel within date range using pagination"""
    global DEFAULT_YOUTUBE_KEYS
    
    all_videos = []
    next_page_token = None
    
    try:
        while True:
            request = youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                maxResults=50,  # API allows up to 50 per page
                order="date",
                type="video",
                publishedAfter=start_date.isoformat() + "Z",
                pageToken=next_page_token  # Add pagination
            )
            response = request.execute()
            
            video_ids = [item['id']['videoId'] for item in response.get('items', [])]
            
            if video_ids:
                # Get video details including duration and statistics
                videos_request = youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=",".join(video_ids)
                )
                videos_response = videos_request.execute()
                
                for video in videos_response.get('items', []):
                    duration = isodate.parse_duration(video['contentDetails']['duration'])
                    duration_seconds = duration.total_seconds()
                    
                    all_videos.append({
                        'id': video['id'],
                        'title': video['snippet']['title'],
                        'published_at': video['snippet']['publishedAt'],
                        'duration_seconds': duration_seconds,
                        'is_short': duration_seconds <= 181,
                        'views': int(video['statistics'].get('viewCount', 0)),
                        'likes': int(video['statistics'].get('likeCount', 0)),
                        'comments': int(video['statistics'].get('commentCount', 0)),
                        'thumbnail': video['snippet']['thumbnails']['medium']['url']
                    })
            
            # Check if there are more pages
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
        return all_videos
        
    except HttpError as e:
        if 'quotaExceeded' in str(e) and DEFAULT_YOUTUBE_KEYS and len(DEFAULT_YOUTUBE_KEYS) > 1:
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(DEFAULT_YOUTUBE_KEYS)
            youtube = build('youtube', 'v3', developerKey=DEFAULT_YOUTUBE_KEYS[st.session_state.current_key_index])
            return fetch_channel_videos(youtube, channel_id, start_date, max_results)
        else:
            return []
        
def generate_ai_insights(data: pd.DataFrame, openai_client, dashboard_focus: str) -> str:
    """Generate Strategic Insights from the data based on dashboard type"""
    try:
        # Get top and bottom performing videos with titles
        top_videos = data.nlargest(10, 'views')[['title', 'views', 'channel', 'is_short']]
        bottom_videos = data.nsmallest(10, 'views')[['title', 'views', 'channel', 'is_short']]
        
        # Calculate engagement rates
        data['engagement_rate'] = ((data['likes'] + data['comments']) / data['views'] * 100).fillna(0)
        high_engagement = data.nlargest(10, 'engagement_rate')[['title', 'engagement_rate', 'views']]
        
        # Create detailed prompt for topic analysis
        top_titles = "\n".join([f"- {v['title']} ({v['views']:,} views, {v['channel']})" for v in top_videos.to_dict('records')])
        bottom_titles = "\n".join([f"- {v['title']} ({v['views']:,} views, {v['channel']})" for v in bottom_videos.to_dict('records')])
        high_engagement_titles = "\n".join([f"- {v['title']} ({v['engagement_rate']:.1f}% engagement, {v['views']:,} views)" for v in high_engagement.to_dict('records')])
        
        if dashboard_focus == "political":
            content_type = "conservative political commentary"
            context_note = "ALL content is political, so don't mention that politics works - be VERY SPECIFIC about what types of political content work."
        else:
            content_type = "sports and college football commentary"
            context_note = "ALL content is sports-related, so don't mention that sports content works - be VERY SPECIFIC about what types of sports content, teams, players, or topics work."

        prompt = f"""You are analyzing YouTube performance data for {content_type} channels. {context_note}

TOP 10 PERFORMING VIDEOS:
{top_titles}

BOTTOM 10 PERFORMING VIDEOS:
{bottom_titles}

HIGHEST ENGAGEMENT VIDEOS:
{high_engagement_titles}

Provide 5 SPECIFIC insights about content performance. BE EXTREMELY SPECIFIC - mention actual names, events, and topics from the titles above:

1. WINNING TOPICS: What SPECIFIC subjects, people, or events are driving views? (Use actual examples from the titles)

2. LOSING TOPICS: What SPECIFIC subjects or approaches are failing? Look at the bottom performers - what topics/people/events appear there but NOT in top performers?

3. TITLE PATTERNS: Compare successful vs unsuccessful titles. What specific words, phrases, or formats work? (e.g., questions vs statements, name-dropping, specific trigger words)

4. ENGAGEMENT DRIVERS: Which specific topics get high engagement even if views are lower? What controversial subjects or people drive comments?

5. CONTENT GAPS: Based on what's working, what SPECIFIC related topics are missing that could perform well?

DO NOT give generic advice. 
DO mention specific people's names, specific events, specific controversies from the actual titles.
Base everything on the actual video titles provided above."""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"AI analysis temporarily unavailable: {str(e)}"
    
# Main content area
if youtube_api_key and selected_channels:
    try:
        # Initialize YouTube API
        youtube = build('youtube', 'v3', developerKey=youtube_api_key)
        
        # Initialize OpenAI if key provided
        openai_client = None
        if openai_api_key:
            openai.api_key = openai_api_key
            from openai import OpenAI
            openai_client = OpenAI(api_key=openai_api_key)
        
        # Get date range
        start_date, end_date = get_time_range_dates(time_range)
        
        # Use cached function
        all_videos = fetch_all_channels_data(selected_channels, start_date, youtube_api_key, CHANNELS)

        if len(all_videos) == 0:
            st.warning("No videos fetched. This could be due to:")
            st.write("- API quota exceeded")
            st.write("- No videos in selected time range")
            st.write("- API key issues")
            
            if st.button("Clear Cache and Retry"):
                st.cache_data.clear()
                st.rerun()

        if all_videos:
            df = pd.DataFrame(all_videos)
            df['published_at'] = pd.to_datetime(df['published_at'])
            
            # Overview metrics
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.markdown("""
                    <div class="metric-card" style="min-height: 150px;">
                        <h3>Total Videos</h3>
                        <div class="value">{:,}</div>
                        <div class="change positive">{} Shorts, {} Regular</div>
                    </div>
                """.format(
                    len(df),
                    len(df[df['is_short']]),
                    len(df[~df['is_short']])
                ), unsafe_allow_html=True)

            with col2:
                total_views = df['views'].sum()
                st.markdown("""
                    <div class="metric-card" style="min-height: 150px;">
                        <h3>Total Views</h3>
                        <div class="value">{}</div>
                        <div class="change positive">Avg: {}/video</div>
                    </div>
                """.format(
                    f"{total_views/1_000_000:.1f}M" if total_views >= 1_000_000 else f"{total_views/1_000:.0f}K",
                    f"{df['views'].mean()/1_000_000:.1f}M" if df['views'].mean() >= 1_000_000 else f"{df['views'].mean()/1_000:.0f}K" if df['views'].mean() >= 1_000 else f"{df['views'].mean():.0f}"
                ), unsafe_allow_html=True)

            with col3:
                total_engagement = df['likes'].sum() + df['comments'].sum()
                st.markdown("""
                    <div class="metric-card" style="min-height: 150px;">
                        <h3>Total Engagement</h3>
                        <div class="value">{}</div>
                        <div class="change positive">{:.1f}% rate</div>
                    </div>
                """.format(
                    f"{total_engagement/1_000_000:.1f}M" if total_engagement >= 1_000_000 else f"{total_engagement/1_000:.0f}K" if total_engagement >= 1_000 else f"{total_engagement:.0f}",
                    (total_engagement / total_views * 100) if total_views > 0 else 0
                ), unsafe_allow_html=True)

            with col4:
                top_channel = df.groupby('channel')['views'].sum().idxmax()
                top_channel_views = df.groupby('channel')['views'].sum().max()
                st.markdown("""
                    <div class="metric-card" style="min-height: 150px;">
                        <h3>Top Channel</h3>
                        <div class="value" style="font-size: 28px; line-height: 1.2;">{}</div>
                        <div class="change positive">{} views</div>
                    </div>
                """.format(
                    top_channel,
                    f"{top_channel_views/1_000_000:.1f}M" if top_channel_views >= 1_000_000 else f"{top_channel_views/1_000:.0f}K"
                ), unsafe_allow_html=True)

            st.markdown("---")
            
            # Tabs for different analyses
            tab1, tab2, tab3, tab4 = st.tabs(["Performance Overview", "Shorts vs Videos", "Top Content", "Strategic Insights"])
            
            with tab1:
                st.markdown("### Channel Performance Comparison")
                
                # Create a base dataframe with all selected channels
                all_channels_data = []
                
                for channel in selected_channels:
                    channel_data = df[df['channel'] == channel] if len(df) > 0 else pd.DataFrame()
                    
                    if len(channel_data) > 0:
                        shorts_views = channel_data[channel_data['is_short']]['views'].sum()
                        regular_views = channel_data[~channel_data['is_short']]['views'].sum()
                    else:
                        shorts_views = 0
                        regular_views = 0
                    
                    all_channels_data.append({
                        'channel': channel,
                        'Shorts': shorts_views,
                        'Regular Videos': regular_views,
                        'Total': shorts_views + regular_views
                    })
                
                # Create DataFrame and sort by total views
                channel_format_stats = pd.DataFrame(all_channels_data)
                
                if not channel_format_stats.empty:
                    channel_format_stats = channel_format_stats.set_index('channel')
                    channel_format_stats = channel_format_stats.sort_values('Total', ascending=True)
                    
                    # Create stacked bar chart
                    fig = go.Figure()
                    
                    if 'Regular Videos' in channel_format_stats.columns:
                        fig.add_trace(go.Bar(
                            y=channel_format_stats.index,
                            x=channel_format_stats['Regular Videos'],
                            name='Regular Videos',
                            orientation='h',
                            marker_color='#E6DDC1',
                            text=[f"{val/1_000_000:.1f}M" if val >= 1_000_000 else f"{val/1_000:.0f}K" if val >= 1_000 else "" 
                                for val in channel_format_stats['Regular Videos']],
                            textposition='inside',
                            textfont=dict(color='#221F1F', size=11, family='Inter'),
                            hovertemplate='%{y}<br>Regular Videos: %{x:,.0f}<extra></extra>'
                        ))
                    
                    if 'Shorts' in channel_format_stats.columns:
                        fig.add_trace(go.Bar(
                            y=channel_format_stats.index,
                            x=channel_format_stats['Shorts'],
                            name='Shorts',
                            orientation='h',
                            marker_color='#BCE5F7',
                            text=[f"{val/1_000_000:.1f}M" if val >= 1_000_000 else f"{val/1_000:.0f}K" if val >= 1_000 else ""
                                for val in channel_format_stats['Shorts']],
                            textposition='inside',
                            textfont=dict(color='#221F1F', size=11, family='Inter'),
                            hovertemplate='%{y}<br>Shorts: %{x:,.0f}<extra></extra>'
                        ))
                    
                    fig.update_layout(
                        title="Total Views by Channel (Shorts vs Regular Videos)",
                        xaxis_title="Views",
                        yaxis_title="",
                        font=dict(family="Inter"),
                        height=500,
                        barmode='stack',
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        xaxis=dict(
                            tickformat='.2s',
                            gridcolor='rgba(0,0,0,0.1)'
                        ),
                        yaxis=dict(
                            categoryorder='total ascending'
                        ),
                        plot_bgcolor='white',
                        margin=dict(l=150, r=50, t=80, b=50)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Add summary stats with error checking
                    col1, col2, col3 = st.columns(3)
                    
                    total_regular = channel_format_stats['Regular Videos'].sum() if 'Regular Videos' in channel_format_stats.columns else 0
                    total_shorts = channel_format_stats['Shorts'].sum() if 'Shorts' in channel_format_stats.columns else 0
                    total_all = total_regular + total_shorts
                    
                    with col1:
                        st.metric(
                            "Total Regular Video Views",
                            f"{total_regular/1_000_000:.1f}M" if total_regular >= 1_000_000 else f"{total_regular/1_000:.0f}K",
                            f"{(total_regular/total_all*100):.1f}% of total" if total_all > 0 else "0%"
                        )
                    
                    with col2:
                        st.metric(
                            "Total Shorts Views", 
                            f"{total_shorts/1_000_000:.1f}M" if total_shorts >= 1_000_000 else f"{total_shorts/1_000:.0f}K",
                            f"{(total_shorts/total_all*100):.1f}% of total" if total_all > 0 else "0%"
                        )
                    
                    with col3:
                        st.metric(
                            "Best Format Performer",
                            "Regular Videos" if total_regular > total_shorts else "Shorts",
                            f"by {abs(total_regular - total_shorts)/1_000_000:.1f}M views" if abs(total_regular - total_shorts) >= 1_000_000 else f"by {abs(total_regular - total_shorts)/1_000:.0f}K views"
                        )
                    
                    # Add Top 5 Videos and Shorts tables at the bottom
                    st.markdown("---")
                    st.markdown("### Top Performing Content")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("#### Top 5 Regular Videos")
                        
                        top_regular = df[~df['is_short']].nlargest(5, 'views')[['title', 'views', 'id', 'channel']]
                        
                        if len(top_regular) > 0:
                            for idx, video in top_regular.iterrows():
                                thumb_col, content_col = st.columns([1, 3])
                                
                                with thumb_col:
                                    thumbnail_url = f"https://img.youtube.com/vi/{video['id']}/mqdefault.jpg"
                                    st.image(thumbnail_url, use_container_width=True)
                                
                                with content_col:
                                    if video['views'] >= 1_000_000:
                                        views_formatted = f"{video['views']/1_000_000:.1f}M"
                                    elif video['views'] >= 1_000:
                                        views_formatted = f"{video['views']/1_000:.0f}K"
                                    else:
                                        views_formatted = str(video['views'])
                                    
                                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                                    title_text = f"{video['title'][:50]}{'...' if len(video['title']) > 50 else ''}"
                                    
                                    st.markdown(f'<a href="{video_url}" target="_blank">{title_text}</a>', unsafe_allow_html=True)
                                    st.markdown(f"*{video['channel']}*")
                                    st.markdown(f"**{views_formatted} views**")
                                
                                st.markdown("")
                        else:
                            st.info("No regular videos found")

                    with col2:
                        st.markdown("#### Top 5 Shorts")
                        
                        top_shorts = df[df['is_short']].nlargest(5, 'views')[['title', 'views', 'id', 'channel']]
                        
                        if len(top_shorts) > 0:
                            for idx, video in top_shorts.iterrows():
                                thumb_col, content_col = st.columns([1, 3])
                                
                                with thumb_col:
                                    thumbnail_url = f"https://img.youtube.com/vi/{video['id']}/mqdefault.jpg"
                                    st.image(thumbnail_url, use_container_width=True)
                                
                                with content_col:
                                    if video['views'] >= 1_000_000:
                                        views_formatted = f"{video['views']/1_000_000:.1f}M"
                                    elif video['views'] >= 1_000:
                                        views_formatted = f"{video['views']/1_000:.0f}K"
                                    else:
                                        views_formatted = str(video['views'])
                                    
                                    video_url = f"https://www.youtube.com/watch?v={video['id']}"
                                    title_text = f"{video['title'][:50]}{'...' if len(video['title']) > 50 else ''}"
                                    
                                    st.markdown(f'<a href="{video_url}" target="_blank">{title_text}</a>', unsafe_allow_html=True)
                                    st.markdown(f"*{video['channel']}*")
                                    st.markdown(f"**{views_formatted} views**")
                                
                                st.markdown("")
                        else:
                            st.info("No shorts found")
                else:
                    st.info("No data available for the selected channels and time range.")
                       
            with tab2:
                st.markdown("### Shorts vs Regular Videos Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Regular videos performance
                    regular_df = df[~df['is_short']]
                    if len(regular_df) > 0:
                        regular_by_channel = regular_df.groupby('channel').agg({
                            'views': ['sum', 'mean', 'count']
                        }).round(0)
                        regular_by_channel.columns = ['total_views', 'avg_views', 'video_count']
                        regular_by_channel = regular_by_channel.sort_values('total_views', ascending=False)
                        
                        st.markdown("**Regular Videos Overview**")
                        metric_col1, metric_col2 = st.columns(2)
                        with metric_col1:
                            st.metric("Total Videos", f"{regular_by_channel['video_count'].sum():.0f}")
                        with metric_col2:
                            total_views = regular_by_channel['total_views'].sum()
                            st.metric("Total Views", f"{total_views/1_000_000:.1f}M" if total_views >= 1_000_000 else f"{total_views/1_000:.0f}K")
                        
                        # Charts for regular videos (same as original)
                        fig_regular_total = go.Figure()
                        fig_regular_total.add_trace(go.Bar(
                            x=regular_by_channel.index,
                            y=regular_by_channel['total_views'],
                            marker_color='#E6DDC1',
                            text=[f"{v/1_000_000:.1f}M" if v >= 1_000_000 else f"{v/1000:.0f}K" if v >= 1000 else f"{v:.0f}" for v in regular_by_channel['total_views']],
                            textposition='outside',
                            hovertemplate='%{x}<br>Total Views: %{y:,.0f}<extra></extra>'
                        ))
                        
                        fig_regular_total.update_layout(
                            title="Total Views - Regular Videos",
                            xaxis_title="",
                            yaxis_title="Total Views",
                            font=dict(family="Inter"),
                            height=350,
                            xaxis_tickangle=-45,
                            yaxis=dict(
                                gridcolor='rgba(0,0,0,0.1)',
                                range=[0, regular_by_channel['total_views'].max() * 1.2]
                            ),
                            plot_bgcolor='white',
                            margin=dict(t=50, b=40)
                        )
                        st.plotly_chart(fig_regular_total, use_container_width=True)
                        
                        # Additional charts would go here (avg views, uploads, engagement)
                        
                    else:
                        st.info("No regular videos found in selected time range")
                
                with col2:
                    # Shorts performance (similar structure)
                    shorts_df = df[df['is_short']]
                    if len(shorts_df) > 0:
                        shorts_by_channel = shorts_df.groupby('channel').agg({
                            'views': ['sum', 'mean', 'count']
                        }).round(0)
                        shorts_by_channel.columns = ['total_views', 'avg_views', 'video_count']
                        shorts_by_channel = shorts_by_channel.sort_values('total_views', ascending=False)
                        
                        st.markdown("**Shorts Overview**")
                        metric_col1, metric_col2 = st.columns(2)
                        with metric_col1:
                            st.metric("Total Shorts", f"{shorts_by_channel['video_count'].sum():.0f}")
                        with metric_col2:
                            total_views = shorts_by_channel['total_views'].sum()
                            st.metric("Total Views", f"{total_views/1_000_000:.1f}M" if total_views >= 1_000_000 else f"{total_views/1_000:.0f}K")
                        
                        # Charts for shorts
                        fig_shorts_total = go.Figure()
                        fig_shorts_total.add_trace(go.Bar(
                            x=shorts_by_channel.index,
                            y=shorts_by_channel['total_views'],
                            marker_color='#BCE5F7',
                            text=[f"{v/1_000_000:.1f}M" if v >= 1_000_000 else f"{v/1000:.0f}K" if v >= 1000 else f"{v:.0f}" for v in shorts_by_channel['total_views']],
                            textposition='outside',
                            hovertemplate='%{x}<br>Total Views: %{y:,.0f}<extra></extra>'
                        ))
                        
                        fig_shorts_total.update_layout(
                            title="Total Views - Shorts",
                            xaxis_title="",
                            yaxis_title="Total Views",
                            font=dict(family="Inter"),
                            height=350,
                            xaxis_tickangle=-45,
                            yaxis=dict(
                                gridcolor='rgba(0,0,0,0.1)',
                                range=[0, shorts_by_channel['total_views'].max() * 1.2]
                            ),
                            plot_bgcolor='white',
                            margin=dict(t=50, b=40)
                        )
                        st.plotly_chart(fig_shorts_total, use_container_width=True)
                        
                    else:
                        st.info("No Shorts found in selected time range")
            
            with tab3:
                st.markdown("### Top Performing Content")
                
                # Top videos table with thumbnails
                top_videos = df.nlargest(10, 'views')[['channel', 'title', 'views', 'likes', 'comments', 'is_short', 'published_at', 'id']]
                
                # Add header row
                header_cols = st.columns([1.5, 2, 4, 1.2, 1.2, 1.2, 1, 1.2])
                with header_cols[0]:
                    st.markdown("**Thumbnail**")
                with header_cols[1]:
                    st.markdown("**Channel**")
                with header_cols[2]:
                    st.markdown("**Title**")
                with header_cols[3]:
                    st.markdown("**Views**")
                with header_cols[4]:
                    st.markdown("**Likes**")
                with header_cols[5]:
                    st.markdown("**Comments**")
                with header_cols[6]:
                    st.markdown("**Format**")
                with header_cols[7]:
                    st.markdown("**Published**")
                
                st.markdown("---")
                
                # Helper function to format numbers
                def format_number(num):
                    if num >= 1_000_000:
                        return f"{num/1_000_000:.1f}M"
                    elif num >= 1_000:
                        return f"{num/1_000:.1f}K"
                    else:
                        return str(num)
                
                # Display each video as a row with columns
                for _, video in top_videos.iterrows():
                    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.5, 2, 4, 1.2, 1.2, 1.2, 1, 1.2])
                    
                    with col1:
                        thumbnail_url = f"https://img.youtube.com/vi/{video['id']}/mqdefault.jpg"
                        st.image(thumbnail_url, use_container_width=True)
                    
                    with col2:
                        st.markdown(f"**{video['channel']}**")
                    
                    with col3:
                        video_url = f"https://www.youtube.com/watch?v={video['id']}"
                        title_text = f"{video['title'][:45]}{'...' if len(video['title']) > 45 else ''}"
                        st.markdown(f'<a href="{video_url}" target="_blank">{title_text}</a>', unsafe_allow_html=True)
                    
                    with col4:
                        st.markdown(f"**{format_number(video['views'])}**")
                    
                    with col5:
                        st.markdown(f"{format_number(video['likes'])}")
                    
                    with col6:
                        st.markdown(f"{format_number(video['comments'])}")
                    
                    with col7:
                        if video['is_short']:
                            st.markdown('**Short**')
                        else:
                            st.markdown('**Video**')
                    
                    with col8:
                        st.markdown(f"{video['published_at'].strftime('%m/%d/%Y')}")
                    
                    st.markdown("---")
                            
            with tab4:
                st.markdown("### Strategic Insights")
                
                if openai_client:
                    with st.spinner("Generating Strategic Insights..."):
                        insights = generate_ai_insights(df, openai_client, dashboard_focus)
                        
                        st.markdown(f"""
                            <div class="ai-analysis">
                                <h4>Strategic Analysis for {time_range}</h4>
                                {insights.replace(chr(10), '<br>')}
                            </div>
                        """, unsafe_allow_html=True)
                        
                else:
                    st.info("Add your OpenAI API key to enable Strategic Insights")
        
        else:
            st.warning("No videos found for the selected channels and time range.")
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please check your API keys and ensure they have the correct permissions.")

else:
    # Show setup instructions
    st.info("""
    ### Getting Started
    
    1. **Add your API Keys** in the sidebar:
       - YouTube Data API v3 key (required)
       - OpenAI API key (optional, for Strategic Insights)
    
    2. **Select Dashboard Type** (Political or Sports)
    
    3. **Select Time Range** for your analysis
    
    4. **Choose Channels** to monitor
    
    5. **Click Refresh Data** to fetch the latest metrics
    
    ---
    
    **Need API Keys?**
    - YouTube: [Google Cloud Console](https://console.cloud.google.com/)
    - OpenAI: [OpenAI Platform](https://platform.openai.com/api-keys)
    """)

# Footer
st.markdown("---")
if dashboard_type == "Ben Shapiro (Political)":
    footer_text = "Shorthand Studios | Daily Wire Competitor Dashboard"
else:
    footer_text = "Crain & Company | Sports Content Analytics Dashboard"

st.markdown(f"""
    <div style="text-align: center; color: #666; font-family: Inter; font-size: 14px; padding: 2rem 0;">
        {footer_text}
    </div>
""", unsafe_allow_html=True)
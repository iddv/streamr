# Friend Interface UI Requirements

## StreamrP2P Elevator Pitch

### The 30-Second Version

**"StreamrP2P turns your friends into your streaming infrastructure through tokenized rewards. Instead of paying Amazon for bandwidth, streamers build community networks where friends earn tokens (converted to real money) by helping distribute streams. We've cracked the code on 'friends supporting friends' - creators keep 90% of revenue instead of 50%, and supporters earn $50-200/month through our contribution-weighted token distribution system."**

---

### The 60-Second Version

**"Streaming platforms take 30-50% of creator revenue to pay for massive server farms. StreamrP2P flips this: your friends become your streaming infrastructure and earn rewards for helping.**

**Here's how it works: When you stream, friends run our simple app that helps relay your content to viewers. They earn tokens based on actual contribution (uptime, bandwidth, quality) that convert to real money - our testing shows $50-200/month - while you keep 90% of revenue instead of giving half to corporate platforms.**

**We've just proven this actually works. Our system handles live 8 Mbps streams, calculates token rewards in real-time based on contribution metrics, and prevents fraud automatically. It's like Twitch, but instead of enriching Amazon, you're enriching your community through fair tokenomics.**

**We're moving from tech validation to real friend networks. The future of streaming isn't corporate servers - it's communities supporting creators they believe in, and everyone earning together."**

---

### Key Value Props

- **For Creators**: Keep 90% revenue (vs 50% on traditional platforms)
- **For Supporters**: Earn $50-200/month through tokenized rewards for helping friends stream  
- **For Everyone**: Community ownership through transparent tokenomics instead of corporate extraction
- **Proven Technology**: Complete working system with real-time token distribution validated end-to-end

### The Problem We Solve

Traditional streaming platforms are extraction machines - they take 30-50% of creator revenue to pay for infrastructure that viewers consume but never benefit from. StreamrP2P makes viewers part of the solution AND the economy through tokenized contribution rewards.

### Why Now?

We've achieved the breakthrough that eluded others: a working "friends supporting friends" tokenized economy that's technically sound, economically viable, and socially compelling. The technology works, the tokenomics work, and the community dynamics work.

---

## Tech Stack
- Next.js 14+ with App Router
- TypeScript 
- Tailwind CSS
- Shadcn/ui components
- SWR for data fetching
- PostHog for analytics

## Core Components Required

### 1. Friend Dashboard (`/dashboard/[nodeId]`)
```javascript
// Primary interface - single page application
Components needed:
- HeroStats (earnings, status, toggle)
- TeamView (friend list with avatars)
- StatusIndicator (online/offline/earning)
- EarningsDisplay (real-time updates)
- DetailsModal (transparency layer)
```

### 2. Data Integration
```javascript
// API endpoints to consume
GET /nodes/{nodeId}/earnings?days_back=1
GET /dashboard  
GET /payouts?hours_back=1

// Polling strategy
- Refresh every 15 seconds using SWR
- Handle error states gracefully
- Show loading indicators during fetch
```

### 3. Core UI Elements

#### Magic Box Section
- Large toggle switch (Shadcn Switch component)
- Text: "Start Helping" / "Stop Helping" 
- Status indicator with color coding (green=active, gray=offline)
- Real-time earnings display: "$X.XX earned today"

#### Team Section  
- Title: "The Support Crew ({count} friends)"
- Horizontal avatar list using Shadcn Avatar component
- Friend status indicators (green dot=online, gray=offline)
- Team impact stat: "Together we've helped X viewers"

#### Transparency Layer
- "Show Details" button triggering Shadcn Dialog/Sheet
- Individual stats translated to human language:
  - "You've been helping for X hours today"
  - "Your share of team reward: X%"
  - "Performance score: X% uptime"

## Data Transformations Required

### Token to USD Conversion
```javascript
// Backend should provide both values
final_payout_tokens: 400.0
final_payout_usd: 2.34  // Pre-calculated by API
```

### Node ID to Friend Names
```javascript
// Map technical IDs to human names
"friend_alice_node" → "Alice"
"friend_bob_node" → "Bob"
```

### Technical Metrics to Human Language
```javascript
uptime_percentage: 0.95 → "95% uptime score"
contribution_percentage: 0.4 → "40% of team reward"
total_polls: 120 → "You've been helping for 2 hours"
```

## Styling Requirements

### Color Scheme
- Primary: Use CSS custom properties for easy theming
- Success states: Green variants
- Warning/offline: Orange/red variants  
- Neutral: Gray scale for secondary text

### Typography
- Headings: Bold, friendly (not corporate)
- Money amounts: Large, prominent display
- Secondary stats: Smaller, muted

### Layout
- Mobile-first responsive design
- Card-based layout using Shadcn Card component
- Consistent spacing using Tailwind spacing scale

## Analytics Events to Track
```javascript
// Critical user journey events
'friend_dashboard_viewed'
'helping_toggle_activated' 
'helping_toggle_deactivated'
'details_modal_opened'
'earnings_amount_viewed'
'team_section_interacted'
```

## Component Structure
```
app/
├── dashboard/
│   └── [nodeId]/
│       ├── page.tsx
│       └── components/
│           ├── HeroStats.tsx
│           ├── TeamView.tsx
│           ├── EarningsDisplay.tsx
│           ├── StatusToggle.tsx
│           └── DetailsModal.tsx
├── lib/
│   ├── api.ts           // API client functions
│   ├── utils.ts         // Data transformation helpers
│   └── analytics.ts     // PostHog event tracking
└── components/ui/       // Shadcn components
```

## API Response Handling
```javascript
// Transform API data to UI-friendly format
function transformEarningsData(apiResponse) {
  return {
    earningsUSD: apiResponse.total_estimated_earnings,
    earningsDisplay: `$${apiResponse.total_estimated_earnings.toFixed(2)}`,
    uptimeScore: Math.round(apiResponse.stream_details[0].uptime_percentage * 100),
    hoursActive: Math.round(apiResponse.stream_details[0].successful_polls / 60),
    isActive: apiResponse.stream_details[0].uptime_percentage > 0
  }
}
```

## Error States
- API failure: "Unable to load earnings data"
- Node offline: "Your connection appears to be offline"
- No data: "No activity yet today"

## Performance Requirements
- Initial page load: <3 seconds
- Data refresh: <1 second
- Mobile optimization: 60fps scroll performance
- Accessibility: Full screen reader support

## Authentication Integration
- Expect nodeId from URL parameters
- Handle authentication state with existing backend
- Redirect to login if unauthorized 
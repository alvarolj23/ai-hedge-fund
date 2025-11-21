# AI Hedge Fund - Analytics Dashboard

A lightweight, cost-efficient analytics dashboard for monitoring and managing your AI-powered hedge fund trading system.

## Features

- **📊 Portfolio Overview** - Real-time portfolio summary from Alpaca Paper Trading
- **📈 Trading Analytics** - Performance metrics, win rates, and agent leaderboard
- **📋 Trade History** - Complete trade log with filtering and pagination
- **🔧 System Monitoring** - Health checks for all Azure components
- **⚙️ Configuration** - Manage market monitor and trading settings

## Tech Stack

- **Frontend**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS (minimal bundle size)
- **Data Fetching**: TanStack React Query
- **Charts**: Recharts (lightweight)
- **Routing**: React Router DOM
- **Backend**: FastAPI (existing aihedgefund-api)

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Access to your deployed `aihedgefund-api` Container App

### Installation

```bash
# Install dependencies
cd dashboard
npm install

# Create environment file
cp .env.example .env

# Edit .env and set your API URL
# VITE_API_URL=https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io
```

### Development

```bash
# Start development server
npm run dev

# Open http://localhost:3000
```

### Build for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview
```

## Deployment to Azure Static Web Apps (FREE)

### Option 1: Azure CLI (Recommended)

```bash
# Build the application
npm run build

# Create Static Web App (one-time setup)
az staticwebapp create \
  --name aihedgefund-dashboard \
  --resource-group rg-ai-hedge-fund-prod \
  --location westeurope \
  --sku Free \
  --source ./dist \
  --branch claude/document-infrastructure-01HTHbVYeUPcWjNPpjrdfFVg

# Get the deployment token
az staticwebapp secrets list \
  --name aihedgefund-dashboard \
  --resource-group rg-ai-hedge-fund-prod

# Deploy
npm run build
az staticwebapp deploy \
  --name aihedgefund-dashboard \
  --resource-group rg-ai-hedge-fund-prod \
  --source ./dist
```

### Option 2: GitHub Actions (Automated)

See `.github/workflows/dashboard-deploy.yml` for automated deployment configuration.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `https://aihedgefund-api.wittysand-2cb74b22.westeurope.azurecontainerapps.io` |

## Project Structure

```
dashboard/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── Card.tsx
│   │   └── Layout.tsx
│   ├── pages/          # Page components
│   │   ├── PortfolioPage.tsx
│   │   ├── AnalyticsPage.tsx
│   │   ├── TradesPage.tsx
│   │   ├── MonitoringPage.tsx
│   │   └── ConfigPage.tsx
│   ├── lib/            # Utilities and API client
│   │   ├── api.ts
│   │   └── utils.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── README.md
```

## Cost

**Total Additional Cost: ~$0-2.30/month**

- Azure Static Web Apps: **FREE** (100GB bandwidth, 2 custom domains)
- Backend API endpoints: **$0** (uses existing Container App)
- Application Insights: **~$2.30/month** (minimal data ingestion)

## API Endpoints Used

### Dashboard Endpoints
- `GET /dashboard/portfolio` - Portfolio summary from Alpaca
- `GET /dashboard/metrics?days=30` - Performance metrics
- `GET /dashboard/trades` - Trade history
- `GET /dashboard/agent-performance?days=30` - Agent leaderboard
- `GET /dashboard/system-health` - System health status
- `GET /dashboard/portfolio-history?days=30` - Historical portfolio values

### Configuration Endpoints
- `GET /config/monitor` - Get market monitor settings
- `PUT /config/monitor` - Validate new monitor settings
- `GET /config/trading` - Get trading configuration
- `PUT /config/trading` - Validate trading configuration

## Performance

- **Bundle Size**: ~200KB (gzipped)
- **First Load**: <1 second
- **Time to Interactive**: <2 seconds
- **Data Refresh**: 30 seconds (portfolio), 5 minutes (metrics)

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## License

MIT

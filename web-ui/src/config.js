// API Configuration
const config = {
  // FastAPI backend URL - change this to match your server
  API_BASE_URL: process.env.REACT_APP_API_URL || 'https://18.177.92.181:8000',

  // API endpoints
  endpoints: {
    microservices: '/bot1api/microservices',
    positions: '/bot1api/positions',
    positionsOpen: '/bot1api/positions/open',
    positionsOpenHedge: '/bot1api/positions/open-hedge',
    positionsEstimate: '/bot1api/positions/estimate',
    assetReport: '/bot1api/asset-report',
    assetSnapshot: '/bot1api/asset-report/snapshot',
    assetCurrent: '/bot1api/asset-report/current',
    funding: '/bot1api/funding'
  }
};

export default config;

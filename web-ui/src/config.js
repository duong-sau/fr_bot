// API Configuration
const config = {
  // FastAPI backend URL - change this to match your server
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://18.177.92.181:8000',

  // API endpoints
  endpoints: {
    microservices: '/bot1api/microservices',
    positions: '/bot1api/positions',
    positionsOpen: '/bot1api/positions/open',
    positionsEstimate: '/bot1api/positions/estimate'
  }
};

export default config;

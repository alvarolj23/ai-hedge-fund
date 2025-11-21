import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import PortfolioPage from './pages/PortfolioPage';
import AnalyticsPage from './pages/AnalyticsPage';
import TradesPage from './pages/TradesPage';
import MonitoringPage from './pages/MonitoringPage';
import ConfigPage from './pages/ConfigPage';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/portfolio" replace />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/trades" element={<TradesPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/config" element={<ConfigPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;

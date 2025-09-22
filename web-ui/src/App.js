import React from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu, Tag } from 'antd';
import {
  DashboardOutlined,
  ControlOutlined,
  PlusOutlined,
  SettingOutlined
} from '@ant-design/icons';
import PositionManagement from './pages/PositionManagement';
import MicroserviceControl from './pages/MicroserviceControl';
import OrderEntry from './pages/OrderEntry';
import Settings from './pages/Settings';
import { getServers } from './services/api';
import './App.css';

const { Header, Content, Sider } = Layout;

function App() {
  const location = useLocation();
  const navigate = useNavigate();

  const keyToPath = {
    positions: '/positions',
    microservices: '/microservices',
    orders: '/orders',
    settings: '/settings',
  };

  const pathToKey = {
    '/positions': 'positions',
    '/microservices': 'microservices',
    '/orders': 'orders',
    '/settings': 'settings',
  };

  const selectedKey = pathToKey[location.pathname] || 'positions';

  const menuItems = [
    {
      key: 'positions',
      icon: <DashboardOutlined />,
      label: 'Quản lý Position',
    },
    {
      key: 'microservices',
      icon: <ControlOutlined />,
      label: 'Microservices',
    },
    {
      key: 'orders',
      icon: <PlusOutlined />,
      label: 'Vào lệnh',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Cài đặt',
    },
  ];

  const handleMenuClick = ({ key }) => {
    const path = keyToPath[key] || '/positions';
    if (location.pathname !== path) {
      navigate(path);
    }
  };

  const headerTitle = menuItems.find(item => item.key === selectedKey)?.label || 'FR Bot Control';

  const servers = getServers();
  let currentBase = servers.A;
  if (servers.active === 'B') currentBase = servers.B;
  if (servers.active === 'C') currentBase = servers.C;
  if (servers.active === 'D') currentBase = servers.D;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={250}>
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: '18px',
          fontWeight: 'bold'
        }}>
          FR Bot Control
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>

      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center'
        }}>
          <h2 style={{ margin: 0 }}>
            {headerTitle}
          </h2>
          <div style={{ marginLeft: 'auto' }}>
            <Tag color="geekblue" onClick={() => navigate('/settings')} style={{ cursor: 'pointer' }}>
              Server {servers.active}: {currentBase || 'N/A'}
            </Tag>
          </div>
        </Header>

        <Content style={{
          margin: '24px',
          padding: '24px',
          background: '#fff',
          minHeight: 280
        }}>
          <Routes>
            <Route path="/positions" element={<PositionManagement />} />
            <Route path="/microservices" element={<MicroserviceControl />} />
            <Route path="/orders" element={<OrderEntry />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/" element={<Navigate to="/positions" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;

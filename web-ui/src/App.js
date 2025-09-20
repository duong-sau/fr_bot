import React from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  ControlOutlined,
  PlusOutlined
} from '@ant-design/icons';
import PositionManagement from './pages/PositionManagement';
import MicroserviceControl from './pages/MicroserviceControl';
import OrderEntry from './pages/OrderEntry';
import './App.css';

const { Header, Content, Sider } = Layout;

function App() {
  const location = useLocation();
  const navigate = useNavigate();

  const keyToPath = {
    positions: '/positions',
    microservices: '/microservices',
    orders: '/orders',
  };

  const pathToKey = {
    '/positions': 'positions',
    '/microservices': 'microservices',
    '/orders': 'orders',
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
  ];

  const handleMenuClick = ({ key }) => {
    const path = keyToPath[key] || '/positions';
    if (location.pathname !== path) {
      navigate(path);
    }
  };

  const headerTitle = menuItems.find(item => item.key === selectedKey)?.label || 'FR Bot Control';

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
            <Route path="/" element={<Navigate to="/positions" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;

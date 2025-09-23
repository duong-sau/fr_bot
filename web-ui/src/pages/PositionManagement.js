import React, { useState, useEffect } from 'react';
import { Table, Card, Tag, Button, Spin, message, Row, Col, Statistic } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import apiService from '../services/api';

const PositionManagement = () => {
  const [positions, setPositions] = useState([]);
  const [loading, setLoading] = useState(false);

  const columns = [
    {
      title: 'Symbol',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (text) => <strong>{text}</strong>
    },
    {
      title: 'Size (USDT)',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount) => `$${Number(amount || 0).toFixed(2)}`
    },
    {
      title: 'Entry Price',
      dataIndex: 'entry',
      key: 'entry',
      render: (price) => `$${Number(price || 0).toFixed(4)}`
    },
    {
      title: 'Funding 1',
      dataIndex: 'funding1',
      key: 'funding1',
      render: (funding) => (
        <Tag color={(funding || 0) >= 0 ? 'green' : 'red'}>
          ${(Number(funding || 0)).toFixed(4)}
        </Tag>
      )
    },
    {
      title: 'Funding 2',
      dataIndex: 'funding2',
      key: 'funding2',
      render: (funding) => (
        <Tag color={(funding || 0) >= 0 ? 'green' : 'red'}>
          ${(Number(funding || 0)).toFixed(4)}
        </Tag>
      )
    },
    {
      title: 'Exchange 1',
      dataIndex: 'exchange1',
      key: 'exchange1',
      render: (exchange) => <Tag color="blue">{exchange}</Tag>
    },
    {
      title: 'Exchange 2',
      dataIndex: 'exchange2',
      key: 'exchange2',
      render: (exchange) => <Tag color="purple">{exchange}</Tag>
    }
  ];

  const fetchPositions = async () => {
    setLoading(true);
    try {
      const data = await apiService.getPositions();
      setPositions(data || []);
    } catch (error) {
      message.error('Không thể tải danh sách position: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
    // Auto refresh every 30 seconds
    const interval = setInterval(fetchPositions, 30000);
    return () => clearInterval(interval);
  }, []);

  // Calculate totals
  const totalFunding1 = positions.reduce((sum, pos) => sum + (pos.funding1 || 0), 0);
  const totalFunding2 = positions.reduce((sum, pos) => sum + (pos.funding2 || 0), 0);
  const totalSizeUSDT = positions.reduce((sum, pos) => sum + (pos.amount || 0), 0);

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Tổng Position"
              value={positions.length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Tổng Size (USDT)"
              value={Number(totalSizeUSDT).toFixed(2)}
              prefix="$"
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Tổng Funding 1"
              value={totalFunding1.toFixed(4)}
              prefix="$"
              valueStyle={{ color: totalFunding1 >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Tổng Funding 2"
              value={totalFunding2.toFixed(4)}
              prefix="$"
              valueStyle={{ color: totalFunding2 >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="Danh sách Position hiện tại"
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchPositions}
            loading={loading}
          >
            Làm mới
          </Button>
        }
      >
        <Spin spinning={loading}>
          <Table
            columns={columns}
            dataSource={positions}
            rowKey="symbol"
            pagination={{ pageSize: 10 }}
            scroll={{ x: 800 }}
          />
        </Spin>
      </Card>
    </div>
  );
};

export default PositionManagement;

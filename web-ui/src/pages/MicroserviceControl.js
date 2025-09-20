import React, { useState, useEffect } from 'react';
import { Card, Button, Tag, Table, message, Space, Popconfirm } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import apiService from '../services/api';

const MicroserviceControl = () => {
  const [microservices, setMicroservices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  const columns = [
    {
      title: 'Tên Service',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <strong>{name}</strong>
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const isRunning = status === 'running';
        return (
          <Tag
            color={isRunning ? 'green' : 'red'}
            icon={isRunning ? <CheckCircleOutlined /> : <ExclamationCircleOutlined />}
          >
            {isRunning ? 'Đang chạy' : 'Đã dừng'}
          </Tag>
        );
      }
    },
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      render: (id) => <code style={{ fontSize: '12px' }}>{id.substring(0, 8)}...</code>
    },
    {
      title: 'Hành động',
      key: 'actions',
      render: (_, record) => {
        const isRunning = record.status === 'running';
        const isLoading = actionLoading[record.id];

        return (
          <Space>
            {!isRunning ? (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => handleStart(record.id)}
                loading={isLoading}
                size="small"
              >
                Khởi động
              </Button>
            ) : (
              <Popconfirm
                title="Bạn có chắc muốn dừng service này?"
                onConfirm={() => handleStop(record.id)}
                okText="Có"
                cancelText="Không"
              >
                <Button
                  danger
                  icon={<PauseCircleOutlined />}
                  loading={isLoading}
                  size="small"
                >
                  Dừng
                </Button>
              </Popconfirm>
            )}
          </Space>
        );
      }
    }
  ];

  const fetchMicroservices = async () => {
    setLoading(true);
    try {
      const data = await apiService.getMicroservices();
      setMicroservices(data || []);
    } catch (error) {
      message.error('Không thể tải danh sách microservices: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (id) => {
    setActionLoading(prev => ({ ...prev, [id]: true }));
    try {
      await apiService.startMicroservice(id);
      message.success('Đã khởi động service thành công!');
      fetchMicroservices(); // Refresh list
    } catch (error) {
      message.error('Không thể khởi động service: ' + error.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleStop = async (id) => {
    setActionLoading(prev => ({ ...prev, [id]: true }));
    try {
      await apiService.stopMicroservice(id);
      message.success('Đã dừng service thành công!');
      fetchMicroservices(); // Refresh list
    } catch (error) {
      message.error('Không thể dừng service: ' + error.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: false }));
    }
  };

  useEffect(() => {
    fetchMicroservices();
    // Auto refresh every 10 seconds
    const interval = setInterval(fetchMicroservices, 10000);
    return () => clearInterval(interval);
  }, []);

  const runningCount = microservices.filter(ms => ms.status === 'running').length;
  const totalCount = microservices.length;

  return (
    <div>
      <Card
        title={
          <div>
            Quản lý Microservices
            <Tag color="blue" style={{ marginLeft: 16 }}>
              {runningCount}/{totalCount} đang chạy
            </Tag>
          </div>
        }
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchMicroservices}
            loading={loading}
          >
            Làm mới
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={microservices}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="middle"
        />
      </Card>

      <Card
        title="Hướng dẫn"
        style={{ marginTop: 24 }}
        size="small"
      >
        <ul>
          <li><strong>ADLControl:</strong> Theo dõi và cân bằng position giữa các sàn giao dịch</li>
          <li><strong>AssetControl:</strong> Quản lý cân bằng tài sản giữa các sàn</li>
          <li>Hệ thống tự động tạo Docker container khi khởi động lần đầu</li>
          <li>Log được lưu trong Docker volume <code>frbot_logs</code></li>
        </ul>
      </Card>
    </div>
  );
};

export default MicroserviceControl;

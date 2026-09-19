import React, { useEffect, useState, useCallback } from 'react';
import { Table, Button, Space, message, Typography, InputNumber, Statistic, Card } from 'antd';
import { ReloadOutlined, CameraOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { apiService } from '../services/api';

const { Title } = Typography;

export default function AssetReport() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(100);
  const [current, setCurrent] = useState(null);
  const [loadingCurrent, setLoadingCurrent] = useState(false);

  const fetchReport = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiService.getAssetReport(limit);
      // attach row keys
      const rows = (res || []).map((r, idx) => ({ key: `${r.timestamp}-${idx}`, ...r }));
      setData(rows);
    } catch (e) {
      message.error('Không tải được báo cáo tài sản');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  const fetchCurrent = useCallback(async () => {
    setLoadingCurrent(true);
    try {
      const res = await apiService.getAssetCurrent();
      setCurrent(res || null);
    } catch (e) {
      message.error('Không tải được tài sản hiện tại');
    } finally {
      setLoadingCurrent(false);
    }
  }, []);

  useEffect(() => {
    fetchReport();
    fetchCurrent();
  }, [fetchReport, fetchCurrent]);

  const handleSnapshot = async () => {
    setLoading(true);
    try {
      const r = await apiService.createAssetSnapshot();
      message.success(`Đã chụp snapshot: ${r?.timestamp || ''}`);
      await fetchReport();
    } catch (e) {
      message.error('Không thể chụp snapshot');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Thời gian', dataIndex: 'timestamp', key: 'timestamp', width: 220 },
    { title: 'Bên 1 (USDT)', dataIndex: 'side1', key: 'side1', align: 'right', render: (v) => Number(v).toFixed(2) },
    { title: 'Bên 2 (USDT)', dataIndex: 'side2', key: 'side2', align: 'right', render: (v) => Number(v).toFixed(2) },
    { title: 'Tổng (USDT)', dataIndex: 'total', key: 'total', align: 'right', render: (v) => <b>{Number(v).toFixed(2)}</b> },
  ];

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Báo cáo tài sản (định kỳ 0h, 4h, 8h, 12h, 16h)</Title>
        <Space>
          <span>Giới hạn dòng:</span>
          <InputNumber min={10} max={10000} step={10} value={limit} onChange={setLimit} />
          <Button icon={<ReloadOutlined />} onClick={fetchReport} loading={loading}>Làm mới</Button>
          <Button type="primary" icon={<CameraOutlined />} onClick={handleSnapshot} loading={loading}>Chụp snapshot</Button>
        </Space>
      </Space>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space size={24} align="center" wrap>
          <Statistic title="Tài sản hiện tại - Bên 1 (USDT)" value={current?.side1 ?? 0} precision={2} />
          <Statistic title="Tài sản hiện tại - Bên 2 (USDT)" value={current?.side2 ?? 0} precision={2} />
          <Statistic title="Tổng hiện tại (USDT)" value={current?.total ?? 0} precision={2} prefix={<ThunderboltOutlined style={{ color: '#faad14' }} />} />
          <Button icon={<ReloadOutlined />} loading={loadingCurrent} onClick={fetchCurrent}>Làm mới hiện tại</Button>
          {current?.timestamp ? <span style={{ color: '#888' }}>Cập nhật: {current.timestamp}</span> : null}
        </Space>
      </Card>

      <Table
        loading={loading}
        columns={columns}
        dataSource={data}
        pagination={{ pageSize: 20 }}
        size="middle"
      />
    </div>
  );
}

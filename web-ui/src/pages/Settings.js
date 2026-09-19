import React, { useEffect, useState } from 'react';
import { Card, Input, Radio, Button, Space, Typography, Tag, message } from 'antd';
import { SettingOutlined, GlobalOutlined, SyncOutlined } from '@ant-design/icons';
import { getServers, setActiveServer, setServerUrl, refreshApiBaseUrl } from '../services/api';

const { Text } = Typography;

const Settings = () => {
  const [serverA, setServerA] = useState('');
  const [serverB, setServerB] = useState('');
  const [serverC, setServerC] = useState('');
  const [serverD, setServerD] = useState(''); // fixed readonly
  const [active, setActive] = useState('A');
  const [applying, setApplying] = useState(false);
  const [currentBase, setCurrentBase] = useState('');

  const load = () => {
    const s = getServers();
    setServerA(s.A || '');
    setServerB(s.B || '');
    setServerC(s.C || '');
    setServerD(s.D || 'http://127.0.0.1:8000');
    setActive(s.active || 'A');
    setCurrentBase(refreshApiBaseUrl());
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSaveUrls = () => {
    const normA = setServerUrl('A', serverA);
    const normB = setServerUrl('B', serverB);
    const normC = setServerUrl('C', serverC);
    setServerA(normA);
    setServerB(normB);
    setServerC(normC);
    if (!normA && !normB && !normC) {
      message.warning('Bạn chưa cấu hình địa chỉ cho Server A/B/C');
    } else {
      message.success('Đã lưu địa chỉ server');
    }
    const base = refreshApiBaseUrl();
    setCurrentBase(base);
  };

  const handleApplyActive = () => {
    const s = getServers();
    let targetUrl = '';
    if (active === 'A') targetUrl = s.A || '';
    if (active === 'B') targetUrl = s.B || '';
    if (active === 'C') targetUrl = s.C || '';
    if (active === 'D') targetUrl = s.D || '';

    if (active !== 'D' && !targetUrl) {
      message.warning(`Địa chỉ của Server ${active} đang trống. Vui lòng nhập và lưu trước khi áp dụng.`);
      return;
    }

    setApplying(true);
    try {
      const base = setActiveServer(active);
      setCurrentBase(base);
      message.success(`Đã chuyển sang server ${active}`);
    } catch (e) {
      message.error('Không thể áp dụng cấu hình server');
    } finally {
      setApplying(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Card
        title={<span><SettingOutlined /> Thiết lập kết nối server</span>}
        extra={<Tag color="blue">Đang dùng: {currentBase || 'N/A'}</Tag>}
      >
        <Space direction="vertical" size="middle" style={{ width: 600, maxWidth: '100%' }}>
          <div>
            <Text type="secondary">Định dạng: http(s)://IP:PORT (ví dụ: http://192.168.1.10:8000). Nếu chỉ nhập IP/PORT sẽ tự thêm http://</Text>
          </div>

          <div>
            <Text strong>Server A</Text>
            <Input
              size="large"
              placeholder="Ví dụ: 18.177.92.181:8000"
              prefix={<GlobalOutlined />}
              value={serverA}
              onChange={e => setServerA(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>

          <div>
            <Text strong>Server B</Text>
            <Input
              size="large"
              placeholder="Ví dụ: 192.168.1.20:8000"
              prefix={<GlobalOutlined />}
              value={serverB}
              onChange={e => setServerB(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>

          <div>
            <Text strong>Server C</Text>
            <Input
              size="large"
              placeholder="Ví dụ: 10.0.0.5:8000"
              prefix={<GlobalOutlined />}
              value={serverC}
              onChange={e => setServerC(e.target.value)}
              style={{ marginTop: 8 }}
            />
          </div>

          <div>
            <Text strong>Server D (cố định)</Text>
            <Input
              size="large"
              disabled
              prefix={<GlobalOutlined />}
              value={serverD}
              style={{ marginTop: 8 }}
            />
          </div>

          <div>
            <Space>
              <Button onClick={handleSaveUrls} type="default">Lưu địa chỉ</Button>
              <Button onClick={load} icon={<SyncOutlined />}>Tải lại</Button>
            </Space>
          </div>

          <div>
            <Text strong>Chọn server đang sử dụng</Text>
            <div style={{ marginTop: 8 }}>
              <Radio.Group value={active} onChange={e => setActive(e.target.value)}>
                <Radio.Button value="A">Server A</Radio.Button>
                <Radio.Button value="B">Server B</Radio.Button>
                <Radio.Button value="C">Server C</Radio.Button>
                <Radio.Button value="D">Server D</Radio.Button>
              </Radio.Group>
            </div>
          </div>

          <div>
            <Button type="primary" onClick={handleApplyActive} loading={applying}>
              Áp dụng server đang dùng
            </Button>
          </div>
        </Space>
      </Card>

      <Card title="Ghi chú" size="small">
        <ul>
          <li>Server D được cố định: 127.0.0.1:8000</li>
          <li>Chức năng này chỉ thay đổi địa chỉ IP/URL của server backend. Không ảnh hưởng tới dữ liệu.</li>
          <li>Việc chuyển server sẽ áp dụng ngay cho các API tiếp theo trong phiên hiện tại.</li>
        </ul>
      </Card>
    </Space>
  );
};

export default Settings;

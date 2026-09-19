import React, { useEffect, useState, useCallback } from 'react';
import { Table, Button, Space, Typography, Tag, message, Tooltip } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { apiService } from '../services/api';

const { Title } = Typography;

function formatPct(v) {
  if (v === null || v === undefined) return '-';
  const pct = Number(v) * 100;
  if (!isFinite(pct)) return '-';
  return `${pct.toFixed(4)}%`;
}

function fundingStyle(rate) {
  if (rate === null || rate === undefined || Number.isNaN(rate)) {
    return { bg: undefined, fg: undefined };
  }
  const vPct = Number(rate) * 100; // compare in percent units
  const absPct = Math.abs(vPct);
  // Thresholds (in percent):
  // > 0.05% => dark red; > 0.005% => light red
  // |v| <= 0.005% => neutral gray
  // < -0.005% => light green; < -0.05% => dark green
  if (vPct > 0.05) return { bg: '#ff4d4f', fg: '#fff' };        // dark red
  if (vPct > 0.005) return { bg: '#ffd8d6', fg: '#a8071a' };    // light red
  if (absPct <= 0.005) return { bg: '#f0f0f0', fg: '#595959' }; // neutral
  if (vPct < -0.05) return { bg: '#52c41a', fg: '#fff' };       // dark green
  if (vPct < -0.005) return { bg: '#d9f7be', fg: '#135200' };   // light green
  return { bg: undefined, fg: undefined };
}

function FundingTag({ rate }) {
  if (rate === null || rate === undefined) return <span>-</span>;
  const { bg, fg } = fundingStyle(rate);
  if (!bg) return <Tag>{formatPct(rate)}</Tag>;
  return <Tag style={{ backgroundColor: bg, color: fg, border: 'none' }}>{formatPct(rate)}</Tag>;
}

function MiniRates({ points }) {
  const arr = Array.isArray(points) ? points : [];
  if (!arr.length) return <span style={{ color: '#999' }}>N/A</span>;
  return (
    <Space size={4} wrap>
      {arr.map((p, idx) => {
        const { bg, fg } = fundingStyle(p.rate);
        return (
          <Tooltip key={`${p.timestamp}-${idx}`} title={new Date(p.timestamp).toLocaleString()}>
            <Tag style={{ backgroundColor: bg || undefined, color: fg || undefined, border: bg ? 'none' : undefined }}>
              {formatPct(p.rate)}
            </Tag>
          </Tooltip>
        );
      })}
    </Space>
  );
}

function getSideData(rec, exName) {
  // exName should be 'bitget' or 'gate'
  if (!rec) return { next: null, recent: [] };
  const { exchange1, exchange2, nextRate1, nextRate2, recent1, recent2 } = rec;
  const match = (ex) => {
    if (exName === 'bitget') return ex === 'bitget' || ex === 'bitget_sub';
    return ex === 'gate';
  };
  if (match(exchange1)) return { next: nextRate1 ?? null, recent: Array.isArray(recent1) ? recent1 : [] };
  if (match(exchange2)) return { next: nextRate2 ?? null, recent: Array.isArray(recent2) ? recent2 : [] };
  return { next: null, recent: [] };
}

export default function FundingRates() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiService.getFundingStats();
      const data = (res || []).map((r, idx) => {
        const bitget = getSideData(r, 'bitget');
        const gate = getSideData(r, 'gate');
        return {
          key: `${r.symbol}-${idx}`,
          symbol: r.symbol,
          bitgetNext: bitget.next,
          bitgetRecent: bitget.recent,
          gateNext: gate.next,
          gateRecent: gate.recent,
        };
      });
      setRows(data);
    } catch (e) {
      console.error(e);
      message.error('Không tải được Funding Rates');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const columns = [
    { title: 'Symbol', dataIndex: 'symbol', key: 'symbol', width: 120 },
    { title: 'Bitget - Tiếp theo', key: 'bg_next', width: 160, render: (_, r) => <FundingTag rate={r.bitgetNext} /> },
    { title: '3 lần trước (Bitget)', key: 'bg_prev', render: (_, r) => <MiniRates points={r.bitgetRecent} /> },
    { title: 'Gate - Tiếp theo', key: 'gt_next', width: 160, render: (_, r) => <FundingTag rate={r.gateNext} /> },
    { title: '3 lần trước (Gate)', key: 'gt_prev', render: (_, r) => <MiniRates points={r.gateRecent} /> },
  ];

  return (
    <div>
      <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>Funding Rates (Bitget trái, Gate phải)</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>Làm mới</Button>
        </Space>
      </Space>

      <Table
        loading={loading}
        columns={columns}
        dataSource={rows}
        pagination={{ pageSize: 20 }}
        size="middle"
      />
    </div>
  );
}

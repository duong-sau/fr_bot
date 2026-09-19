import React, { useState } from 'react';
import { Card, Form, InputNumber, Button, Select, Input, message, Row, Col, Divider, Alert, Radio, Descriptions, Space, Typography } from 'antd';
import { CalculatorOutlined, ThunderboltOutlined } from '@ant-design/icons';
import apiService from '../services/api';

const { Option } = Select;
const { Text } = Typography;

const OrderEntry = () => {
  const [estimateForm] = Form.useForm();
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [estimateResult, setEstimateResult] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [lastEstimateError, setLastEstimateError] = useState('');

  // Common cryptocurrency symbols
  const commonSymbols = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT',
    'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'XLMUSDT', 'VETUSDT',
    'EOSUSDT', 'TRXUSDT', 'XRPUSDT', 'ATOMUSDT', 'SOLUSDT'
  ];

  // Helper matchers for exchange naming variations
  const isGate = (name) => {
    const n = (name || '').toString().toLowerCase();
    return n === 'gate' || n === 'gateio' || n === 'gate_io' || n === 'gate.io';
  };
  const isBitget = (name) => {
    const n = (name || '').toString().toLowerCase();
    return n === 'bitget' || n.startsWith('bitget'); // covers bitget_sub, etc.
  };

  // Normalize user input to a USDT pair if missing (e.g., "ETH" -> "ETHUSDT")
  const normalizeSymbol = (sym) => {
    const s = (sym || '').trim().toUpperCase();
    if (!s) return s;
    // If already in a pair format or contains quote info, keep as-is
    if (s.includes('/') || s.includes(':')) return s;
    // If ends with USDT already, keep
    if (s.endsWith('USDT')) return s;
    // Otherwise, assume USDT quote
    return s + 'USDT';
  };

  const handleEstimate = async (values) => {
    setEstimateLoading(true);
    try {
      const symbol = normalizeSymbol(values.symbol);
      const result = await apiService.estimatePosition(symbol, values.size);
      if (!result) throw new Error('Empty result');
      setEstimateResult(result);
      setLastEstimateError('');
      // default selection: prefer Long Gate / Short Bitget if available
      if (Array.isArray(result.options) && result.options.length > 0) {
        const preferred = result.options.find(o => isGate(o?.long?.exchange) && isBitget(o?.short?.exchange));
        setSelectedOption((preferred || result.options[0]).key);
      } else {
        setSelectedOption(null);
      }
      message.success('Đã tính toán ước tính thành công!');
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || '';
      message.error('Không thể tính toán ước tính: ' + detail);
      setEstimateResult(null);
      setSelectedOption(null);
      setLastEstimateError(String(detail));
    } finally {
      setEstimateLoading(false);
    }
  };

  const handleConfirmOpen = async () => {
    if (!estimateResult) return;
    const opts = Array.isArray(estimateResult.options) ? estimateResult.options : [];
    const chosen = opts.find(o => o.key === selectedOption) || opts[0];
    if (!chosen) {
      message.warning('Vui lòng chọn chiến lược Long/Short');
      return;
    }

    const payload = {
      symbol: estimateResult.symbol,
      longExchange: chosen.long.exchange,
      longContracts: Number(chosen.long.contracts || 0),
      shortExchange: chosen.short.exchange,
      shortContracts: Number(chosen.short.contracts || 0)
    };

    if (!payload.longContracts || !payload.shortContracts) {
      message.error('Số hợp đồng trên một trong hai sàn bằng 0, không thể mở lệnh.');
      return;
    }

    setConfirmLoading(true);
    try {
      const res = await apiService.openHedgePosition(payload);
      message.success('Đã gửi mở lệnh hedge thành công');
      // Show server feedback: executed orders or dry-run plan
      if (res?.orders && Array.isArray(res.orders)) {
        const summary = res.orders.map(p => `${p.exchange} ${p.side} ${p.request} ${p.symbol}`).join(' | ');
        message.info(summary, 8);
      } else if (res?.plan) {
        const summary = res.plan.map(p => `${p.exchange} ${p.side} ${p.contracts} ${p.symbol}`).join(' | ');
        message.info(summary, 8);
      }
    } catch (error) {
      const detail = error?.response?.data?.detail || error?.message || '';
      message.error('Không thể mở lệnh hedge: ' + detail);
    } finally {
      setConfirmLoading(false);
    }
  };

  return (
    <div>
      <Row gutter={24}>
        {/* Estimate Position Form */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <CalculatorOutlined style={{ marginRight: 8 }} />
                Ước tính & Chọn chiến lược
              </span>
            }
          >
            <Form
              form={estimateForm}
              layout="vertical"
              onFinish={handleEstimate}
              initialValues={{
                size: 100
              }}
            >
              <Form.Item
                label="Symbol"
                name="symbol"
                rules={[
                  { required: true, message: 'Vui lòng nhập symbol!' },
                  { pattern: /^[A-Za-z0-9/:.-]+$/, message: 'Symbol chỉ gồm chữ, số, /, : , . , -' }
                ]}
              >
                <Input placeholder="Ví dụ: ETH (tự thêm USDT) hoặc ETHUSDT hay ETH/USDT:USDT" allowClear />
              </Form.Item>

              <Form.Item
                label="Kích thước (USDT) mỗi bên"
                name="size"
                rules={[
                  { required: true, message: 'Vui lòng nhập kích thước!' },
                  { type: 'number', min: 5, message: 'Kích thước phải >= 5 USDT!' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Nhập số USDT muốn vào cho mỗi bên"
                  min={5}
                  step={5}
                  precision={2}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={estimateLoading}
                  block
                  size="large"
                >
                  Tính toán ước tính
                </Button>
              </Form.Item>
            </Form>

            {lastEstimateError ? (
              <Alert
                type="warning"
                showIcon
                message="Không thể ước tính"
                description={lastEstimateError}
              />
            ) : (
              <Alert
                message="Quy trình mới"
                description="Bước 1: Nhập symbol (có thể chỉ nhập tên như ETH, hệ thống tự thêm USDT) và kích thước. Bước 2: Ước tính để xem contracts, bước tối thiểu và contract size từng sàn. Bước 3: Chọn Long/Short (mặc định ưu tiên Long Gate / Short Bitget) và ấn OK."
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            )}
          </Card>
        </Col>

        {/* Estimate Result & Confirm */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <ThunderboltOutlined style={{ marginRight: 8, color: '#faad14' }} />
                Kết quả ước tính & Xác nhận
              </span>
            }
          >
            {!estimateResult ? (
              <Alert type="warning" showIcon message="Chưa có ước tính" description="Hãy nhập thông tin và ấn Tính toán ước tính ở bên trái." />
            ) : (
              <>
                <Descriptions size="small" bordered column={1} style={{ marginBottom: 12 }}>
                  <Descriptions.Item label="Symbol">{estimateResult.symbol}</Descriptions.Item>
                  <Descriptions.Item label="Kích thước yêu cầu (USDT)">{estimateResult.requestedSizeUSDT}</Descriptions.Item>
                </Descriptions>

                <Row gutter={12}>
                  <Col span={12}>
                    <Card size="small" title="Bitget" bordered>
                      <Space direction="vertical" size={4}>
                        <Text type="secondary">Symbol: {estimateResult.bitget?.symbol}</Text>
                        <Text>Giá: {Number(estimateResult.bitget?.price ?? 0).toFixed(4)}</Text>
                        <Text>Contract Size: {estimateResult.bitget?.contractSize}</Text>
                        <Text>Bước hợp đồng tối thiểu: {estimateResult.bitget?.amountStep}</Text>
                        <Text strong>Contracts: {estimateResult.bitget?.contracts}</Text>
                        {estimateResult.bitget?.minUsdtFor1Contract !== undefined && (
                          <Text type="secondary">USDT tối thiểu cho 1 contract: {estimateResult.bitget.minUsdtFor1Contract}</Text>
                        )}
                        {estimateResult.bitget?.minUsdtForMinStep !== undefined && (
                          <Text type="secondary">USDT tối thiểu cho 1 bước: {estimateResult.bitget.minUsdtForMinStep}</Text>
                        )}
                        {estimateResult.bitget?.openInterestUSDT != null && (
                          <Text type="secondary">Open Interest (USDT): {Number(estimateResult.bitget.openInterestUSDT).toLocaleString(undefined, { maximumFractionDigits: 2 })}</Text>
                        )}
                      </Space>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card size="small" title="Gate.io" bordered>
                      <Space direction="vertical" size={4}>
                        <Text type="secondary">Symbol: {estimateResult.gate?.symbol}</Text>
                        <Text>Giá: {Number(estimateResult.gate?.price ?? 0).toFixed(4)}</Text>
                        <Text>Contract Size: {estimateResult.gate?.contractSize}</Text>
                        <Text>Bước hợp đồng tối thiểu: {estimateResult.gate?.amountStep}</Text>
                        <Text strong>Contracts: {estimateResult.gate?.contracts}</Text>
                        {estimateResult.gate?.minUsdtFor1Contract !== undefined && (
                          <Text type="secondary">USDT tối thiểu cho 1 contract: {estimateResult.gate.minUsdtFor1Contract}</Text>
                        )}
                        {estimateResult.gate?.minUsdtForMinStep !== undefined && (
                          <Text type="secondary">USDT tối thiểu cho 1 bước: {estimateResult.gate.minUsdtForMinStep}</Text>
                        )}
                        {estimateResult.gate?.openInterestUSDT != null && (
                          <Text type="secondary">Open Interest (USDT): {Number(estimateResult.gate.openInterestUSDT).toLocaleString(undefined, { maximumFractionDigits: 2 })}</Text>
                        )}
                      </Space>
                    </Card>
                  </Col>
                </Row>

                {estimateResult.minUsdtForBothMinStep !== undefined && (
                  <Alert
                    style={{ marginTop: 12 }}
                    type="info"
                    showIcon
                    message={`USDT tối thiểu đề xuất để mở được cả hai bên (1 bước): ${estimateResult.minUsdtForBothMinStep}`}
                  />
                )}

                <Divider />

                <div style={{ marginBottom: 8 }}>Chọn chiến lược (mặc định ưu tiên Long Gate / Short Bitget):</div>
                <Radio.Group
                  value={selectedOption}
                  onChange={(e) => setSelectedOption(e.target.value)}
                  style={{ display: 'block' }}
                >
                  {(estimateResult.options || []).map(opt => (
                    <Radio key={opt.key} value={opt.key} style={{ display: 'block', marginBottom: 8 }}>
                      {opt.label}
                      <div style={{ color: '#999', fontSize: 12 }}>
                        Long {opt.long.exchange} ({opt.long.contracts} contracts) / Short {opt.short.exchange} ({opt.short.contracts} contracts)
                      </div>
                    </Radio>
                  ))}
                </Radio.Group>

                <Button
                  type="primary"
                  onClick={handleConfirmOpen}
                  loading={confirmLoading}
                  disabled={!selectedOption}
                  style={{ marginTop: 12 }}
                  block
                >
                  OK - Mở lệnh hai bên theo lựa chọn
                </Button>
              </>
            )}
          </Card>
        </Col>
      </Row>

      <Divider />

      <Card title="Hướng dẫn sử dụng" size="small">
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <h4>Quy trình mở lệnh mới:</h4>
            <ul>
              <li>Nhập symbol và kích thước (USDT) mỗi bên</li>
              <li>Nhấn "Tính toán ước tính" để xem contracts, bước tối thiểu và contract size từng sàn</li>
              <li>Chọn chiến lược: Long Gate/Short Bitget hoặc Long Bitget/Short Gate</li>
              <li>Nhấn "OK" để mở lệnh hai bên tương ứng</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <h4>Lưu ý:</h4>
            <ul>
              <li>Nếu sàn hỗ trợ số thập phân (ví dụ 0.01), ứng dụng sẽ tự lượng hóa theo bước tối thiểu</li>
              <li>Hãy đảm bảo đủ USDT trên cả hai sàn</li>
              <li>Hiện tại server sẽ đặt lệnh thực tế; nếu chân thứ 2 lỗi, hệ thống cố gắng đóng ngay chân thứ 1 (reduce-only)</li>
            </ul>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default OrderEntry;

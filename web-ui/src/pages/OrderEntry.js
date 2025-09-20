import React, { useState } from 'react';
import { Card, Form, Input, InputNumber, Button, Select, message, Row, Col, Divider, Alert } from 'antd';
import { DollarOutlined, CalculatorOutlined } from '@ant-design/icons';
import apiService from '../services/api';

const { Option } = Select;

const OrderEntry = () => {
  const [form] = Form.useForm();
  const [estimateForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [estimateResult, setEstimateResult] = useState(null);

  // Common cryptocurrency symbols
  const commonSymbols = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT',
    'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'XLMUSDT', 'VETUSDT',
    'EOSUSDT', 'TRXUSDT', 'XRPUSDT', 'ATOMUSDT', 'SOLUSDT'
  ];

  const handleOpenPosition = async (values) => {
    setLoading(true);
    try {
      const result = await apiService.openPosition(values.symbol, values.size);
      message.success('Đã mở position thành công!');
      form.resetFields();
      console.log('Position opened:', result);
    } catch (error) {
      message.error('Không thể mở position: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEstimate = async (values) => {
    setEstimateLoading(true);
    try {
      const result = await apiService.estimatePosition(values.symbol, values.size);
      setEstimateResult(result);
      message.success('Đã tính toán ước tính thành công!');
    } catch (error) {
      message.error('Không thể tính toán ước tính: ' + error.message);
      setEstimateResult(null);
    } finally {
      setEstimateLoading(false);
    }
  };

  return (
    <div>
      <Row gutter={24}>
        {/* Open Position Form */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <DollarOutlined style={{ marginRight: 8 }} />
                Mở Position Mới
              </span>
            }
          >
            <Form
              form={form}
              layout="vertical"
              onFinish={handleOpenPosition}
              initialValues={{
                size: 100
              }}
            >
              <Form.Item
                label="Symbol"
                name="symbol"
                rules={[
                  { required: true, message: 'Vui lòng chọn symbol!' },
                  { pattern: /^[A-Z0-9]+$/, message: 'Symbol phải là chữ hoa và số!' }
                ]}
              >
                <Select
                  showSearch
                  placeholder="Chọn hoặc nhập symbol"
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                >
                  {commonSymbols.map(symbol => (
                    <Option key={symbol} value={symbol}>{symbol}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="Kích thước Position"
                name="size"
                rules={[
                  { required: true, message: 'Vui lòng nhập kích thước!' },
                  { type: 'number', min: 0.01, message: 'Kích thước phải lớn hơn 0.01!' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Nhập kích thước position"
                  min={0.01}
                  step={0.01}
                  precision={4}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  size="large"
                >
                  Mở Position
                </Button>
              </Form.Item>
            </Form>

            <Alert
              message="Lưu ý quan trọng"
              description="Hệ thống sẽ tự động mở position trên cả hai sàn để thực hiện arbitrage. Hãy đảm bảo có đủ balance trên cả hai sàn."
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
            />
          </Card>
        </Col>

        {/* Estimate Position Form */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <span>
                <CalculatorOutlined style={{ marginRight: 8 }} />
                Ước tính Position
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
                  { required: true, message: 'Vui lòng chọn symbol!' },
                  { pattern: /^[A-Z0-9]+$/, message: 'Symbol phải là chữ hoa và số!' }
                ]}
              >
                <Select
                  showSearch
                  placeholder="Chọn hoặc nhập symbol"
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                  }
                >
                  {commonSymbols.map(symbol => (
                    <Option key={symbol} value={symbol}>{symbol}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item
                label="Kích thước Position"
                name="size"
                rules={[
                  { required: true, message: 'Vui lòng nhập kích thước!' },
                  { type: 'number', min: 0.01, message: 'Kích thước phải lớn hơn 0.01!' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Nhập kích thước position"
                  min={0.01}
                  step={0.01}
                  precision={4}
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="default"
                  htmlType="submit"
                  loading={estimateLoading}
                  block
                  size="large"
                >
                  Tính toán ước tính
                </Button>
              </Form.Item>
            </Form>

            {estimateResult && (
              <Card
                size="small"
                title="Kết quả ước tính"
                style={{ marginTop: 16 }}
              >
                <pre style={{
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  fontSize: '12px',
                  whiteSpace: 'pre-wrap'
                }}>
                  {JSON.stringify(estimateResult, null, 2)}
                </pre>
              </Card>
            )}
          </Card>
        </Col>
      </Row>

      <Divider />

      <Card title="Hướng dẫn sử dụng" size="small">
        <Row gutter={16}>
          <Col xs={24} md={12}>
            <h4>Mở Position:</h4>
            <ul>
              <li>Chọn symbol từ danh sách hoặc nhập thủ công</li>
              <li>Nhập kích thước position (USDT)</li>
              <li>Hệ thống sẽ tự động mở position trên cả hai sàn</li>
              <li>Kiểm tra balance trước khi thực hiện</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <h4>Ước tính Position:</h4>
            <ul>
              <li>Sử dụng để xem trước kết quả trước khi mở position thật</li>
              <li>Hiển thị thông tin chi tiết về position sẽ được tạo</li>
              <li>Giúp đánh giá rủi ro và lợi nhuận tiềm năng</li>
              <li>Không tốn phí và không ảnh hưởng đến tài khoản</li>
            </ul>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default OrderEntry;

import React, { useState, useEffect } from 'react';
import { Card, Table, InputNumber, Button, Tag, Radio, Message, Typography, Space, Alert } from '@arco-design/web-react';
import { listRechargeCodes, createRechargeCodes } from '../../api/admin';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const RechargeCodes: React.FC = () => {
  const [codes, setCodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('all');
  const [amount, setAmount] = useState(50);
  const [quantity, setQuantity] = useState(10);
  const [generating, setGenerating] = useState(false);
  const [newCodes, setNewCodes] = useState<string[]>([]);

  const fetchCodes = async () => {
    setLoading(true);
    try {
      const resp = await listRechargeCodes();
      if (Array.isArray(resp)) {
        setCodes(resp);
        setTotal(resp.length);
      } else {
        setCodes(resp?.items || []);
        setTotal(resp?.total || 0);
      }
    } catch {
      Message.error('获取充值码列表失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchCodes(); }, []);

  const handleGenerate = async () => {
    if (quantity < 1 || quantity > 100) { Message.warning('数量范围 1-100'); return; }
    setGenerating(true);
    try {
      const resp = await createRechargeCodes({ amount, quantity });
      const generated = resp?.codes?.map((c: any) => c.code || c) || [];
      setNewCodes(generated);
      Message.success('已生成 ' + (resp?.count || generated.length) + ' 个兑换码');
      fetchCodes();
    } catch { Message.error('生成失败'); }
    setGenerating(false);
  };

  const filteredCodes = filter === 'all' ? codes : codes.filter((c: any) => c.status === filter);

  const columns = [
    { title: '兑换码', dataIndex: 'code', render: (v: string) => <Text copyable code>{v}</Text> },
    { title: '面值', dataIndex: 'amount', render: (v: number) => <Text style={{ color: '#165DFF' }}>¥{(v || 0).toFixed(2)}</Text> },
    { title: '状态', dataIndex: 'status', render: (v: string) => {
      const isUsed = v === 'used' || v === 'USED';
      return <Tag color={isUsed ? 'green' : 'orange'}>{isUsed ? '已使用' : '未使用'}</Tag>;
    }},
    { title: '使用者', dataIndex: 'used_by', render: (v: string) => v || '-' },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-' },
  ];

  return (
    <div>
      <Title heading={5} style={{ marginBottom: 16 }}>充值码管理</Title>

      {newCodes.length > 0 && (
        <Alert
          type="success"
          title="已生成兑换码（请妥善保存）"
          content={
            <div style={{ fontFamily: 'monospace', fontSize: 13, lineHeight: 2 }}>
              {newCodes.map((c, i) => <div key={i}>{c}</div>)}
            </div>
          }
          closable
          onClose={() => setNewCodes([])}
          style={{ marginBottom: 16 }}
        />
      )}

      <Card style={{ marginBottom: 16 }} bordered={false}>
        <Space>
          <span>面值：</span>
          <InputNumber value={amount} onChange={(v) => setAmount(v || 50)} min={1} max={10000} style={{ width: 120 }} prefix="¥" />
          <span>数量：</span>
          <InputNumber value={quantity} onChange={(v) => setQuantity(v || 10)} min={1} max={100} style={{ width: 120 }} />
          <Button type="primary" loading={generating} onClick={handleGenerate}>批量生成</Button>
        </Space>
      </Card>
      <Card bordered={false}>
        <div style={{ marginBottom: 12 }}>
          <Radio.Group value={filter} onChange={setFilter} type="button" options={[
            { label: '全部', value: 'all' },
            { label: '未使用', value: 'unused' },
            { label: '已使用', value: 'used' },
          ]} />
        </div>
        <Table columns={columns} data={filteredCodes} loading={loading} rowKey="id" size="small" />
      </Card>
    </div>
  );
};

export default RechargeCodes;

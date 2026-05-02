import React, { useState, useEffect } from 'react';
import { Card, Input, Button, Table, Message, Typography, Space, Tag } from '@arco-design/web-react';
import { IconGift } from '@arco-design/web-react/icon';
import { recharge as rechargeApi, getBalance } from '../../api/billing';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const Recharge: React.FC = () => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [balance, setBalance] = useState(0);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    getBalance().then(b => setBalance(b.balance || 0)).catch(() => {});
  }, []);

  const handleRecharge = async () => {
    if (!code.trim()) { Message.warning('请输入兑换码'); return; }
    setLoading(true);
    try {
      const res = await rechargeApi({ code: code.trim() });
      Message.success('充值成功！余额：¥' + (res.new_balance ?? res.balance ?? 0).toFixed(2));
      setCode('');
      setBalance(res.new_balance ?? res.balance ?? balance);
      setHistory(prev => [{
        key: Date.now().toString(),
        code: code.trim().slice(0, 8) + '...',
        amount: res.amount ?? 0,
        time: new Date().toISOString(),
        status: 'completed',
      }, ...prev]);
    } catch (err: any) {
      Message.error(err?.response?.data?.detail?.error || '充值失败，请检查兑换码');
    }
    setLoading(false);
  };

  const columns = [
    { title: '兑换码', dataIndex: 'code', render: (v: string) => <Text code>{v}</Text> },
    { title: '金额', dataIndex: 'amount', render: (v: number) => <Text style={{ color: '#165DFF', fontWeight: 600 }}>¥{(v || 0).toFixed(2)}</Text> },
    { title: '时间', dataIndex: 'time', render: (v: string) => dayjs(v).format('YYYY-MM-DD HH:mm') },
    { title: '状态', dataIndex: 'status', render: () => <Tag color="green">成功</Tag> },
  ];

  return (
    <div>
      <Title heading={5} style={{ marginBottom: 16 }}>充值</Title>
      <Card style={{ marginBottom: 20 }} bordered={false}>
        <div style={{ marginBottom: 16 }}>
          <Text type="secondary">当前余额：</Text>
          <Text bold style={{ fontSize: 20, color: '#165DFF' }}>¥{balance.toFixed(2)}</Text>
        </div>
        <Space>
          <IconGift style={{ fontSize: 20, color: '#165DFF' }} />
          <Input
            placeholder="请输入兑换码"
            value={code}
            onChange={setCode}
            style={{ width: 300 }}
            onPressEnter={handleRecharge}
            size="large"
          />
          <Button type="primary" loading={loading} onClick={handleRecharge} size="large">兑换</Button>
        </Space>
      </Card>
      {history.length > 0 && (
        <Card title="充值记录" bordered={false}>
          <Table columns={columns} data={history} rowKey="key" size="small" />
        </Card>
      )}
    </div>
  );
};

export default Recharge;

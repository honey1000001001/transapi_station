import React, { useState, useEffect } from 'react';
import { Table, Tag, Typography, Message } from '@arco-design/web-react';
import { listPayments } from '../../api/admin';
import dayjs from 'dayjs';

const { Title } = Typography;

const Payments: React.FC = () => {
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const resp = await listPayments(page, 20);
        if (Array.isArray(resp)) {
          setPayments(resp);
          setTotal(resp.length);
        } else {
          setPayments(resp?.items || []);
          setTotal(resp?.total || 0);
        }
      } catch {
        Message.error('获取支付记录失败');
      }
      setLoading(false);
    };
    fetch();
  }, [page]);

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 200, render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span> },
    { title: '用户', dataIndex: 'user_id', width: 200, render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span> },
    { title: '金额', dataIndex: 'amount', render: (v: number) => <span style={{ color: '#165DFF', fontWeight: 600 }}>¥{(v || 0).toFixed(2)}</span> },
    { title: '方式', dataIndex: 'method', render: (v: string) => <Tag color="blue">{v === 'recharge_code' ? '兑换码' : v}</Tag> },
    { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'completed' ? 'green' : v === 'pending' ? 'orange' : 'red'}>{v === 'completed' ? '完成' : v === 'pending' ? '待处理' : '失败'}</Tag> },
    { title: '时间', dataIndex: 'created_at', render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-' },
  ];

  return (
    <div>
      <Title heading={5} style={{ marginBottom: 16 }}>支付记录</Title>
      <Table
        columns={columns}
        data={payments}
        loading={loading}
        rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        size="small"
      />
    </div>
  );
};

export default Payments;

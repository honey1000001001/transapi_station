import React, { useState, useEffect } from 'react';
import { Card, Grid, Table, Tabs, Spin, Tag, Typography, Button } from '@arco-design/web-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import StatCard from '../../components/StatCard';
import { getUsage, getLogs, getBalance } from '../../api/billing';
import dayjs from 'dayjs';

const { Row, Col } = Grid;
const { Title } = Typography;

const Billing: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState<any[]>([]);
  const [stats, setStats] = useState({ totalRequests: 0, totalTokens: 0, totalCost: 0 });
  const [balance, setBalance] = useState(0);
  const [aggregateData] = useState([
    { date: '04-19', requests: 45, cost: 2.10 },
    { date: '04-20', requests: 62, cost: 3.50 },
    { date: '04-21', requests: 38, cost: 1.80 },
    { date: '04-22', requests: 89, cost: 5.20 },
    { date: '04-23', requests: 56, cost: 2.90 },
    { date: '04-24', requests: 73, cost: 4.10 },
    { date: '04-25', requests: 91, cost: 5.60 },
  ]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [usage, bal, logsResp] = await Promise.all([
          getUsage(), getBalance(), getLogs(page, 20)
        ]);
        setStats({
          totalRequests: usage.total_requests || 0,
          totalTokens: (usage.prompt_tokens || 0) + (usage.completion_tokens || 0),
          totalCost: usage.total_cost || 0,
        });
        setBalance(bal.balance || 0);
        const logItems = (logsResp as any)?.items || (Array.isArray(logsResp) ? logsResp : []);
        setLogs(logItems);
        setTotal((logsResp as any)?.total || 0);
      } catch (e) {
        console.warn('Failed to load billing data', e);
      }
      setLoading(false);
    };
    fetchData();
  }, [page]);

  const columns = [
    { title: '时间', dataIndex: 'created_at', width: 170, render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm:ss') : '-' },
    { title: '模型', dataIndex: 'model', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: 'Prompt Token', dataIndex: 'prompt_tokens', render: (v: number) => (v || 0).toLocaleString() },
    { title: 'Completion Token', dataIndex: 'completion_tokens', render: (v: number) => (v || 0).toLocaleString() },
    { title: '费用', dataIndex: 'cost', render: (v: number) => '¥' + (v || 0).toFixed(4) },
    { title: '耗时', dataIndex: 'latency_ms', render: (v: number) => v ? (v/1000).toFixed(1) + 's' : '-' },
    { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'success' ? 'green' : 'red'}>{v === 'success' ? '成功' : '失败'}</Tag> },
  ];

  const handleExportCSV = () => {
    const headers = '时间,模型,Prompt Token,Completion Token,费用,状态\n';
    const rows = logs.map((l: any) => `${l.created_at},${l.model},${l.prompt_tokens},${l.completion_tokens},${l.cost},${l.status}`).join('\n');
    const blob = new Blob([headers + rows], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'billing_' + dayjs().format('YYYYMMDD') + '.csv';
    a.click(); URL.revokeObjectURL(url);
  };

  return (
    <Spin loading={loading} style={{ display: 'block' }}>
      <div className="page-header">
        <Title heading={5} style={{ margin: 0 }}>账单明细</Title>
      </div>
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col span={6}><StatCard label="余额" value={'¥' + balance.toFixed(2)} /></Col>
        <Col span={6}><StatCard label="总请求" value={stats.totalRequests.toLocaleString()} /></Col>
        <Col span={6}><StatCard label="总 Token" value={stats.totalTokens.toLocaleString()} /></Col>
        <Col span={6}><StatCard label="总费用" value={'¥' + stats.totalCost.toFixed(2)} /></Col>
      </Row>
      <Tabs defaultActiveTab="detail">
        <Tabs.TabPane key="detail" title="明细">
          <div style={{ marginBottom: 12, textAlign: 'right' }}>
            <Button onClick={handleExportCSV}>导出 CSV</Button>
          </div>
          <Table
            columns={columns}
            data={logs}
            rowKey="id"
            pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
            size="small"
          />
        </Tabs.TabPane>
        <Tabs.TabPane key="aggregate" title="汇总">
          <Card title="每日费用与请求数" bordered={false}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={aggregateData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Bar yAxisId="left" dataKey="requests" fill="#165DFF" name="请求数" />
                <Bar yAxisId="right" dataKey="cost" fill="#14C9C9" name="费用(¥)" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </Spin>
  );
};

export default Billing;

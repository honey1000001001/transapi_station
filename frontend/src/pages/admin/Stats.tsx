import React, { useState, useEffect } from 'react';
import { Card, Grid, Table, Typography, Tag, Spin } from '@arco-design/web-react';
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { getStats } from '../../api/admin';
import dayjs from 'dayjs';

const { Row, Col } = Grid;
const { Title } = Typography;

const COLORS = ['#165DFF', '#14C9C9', '#F7BA1E', '#9FDB1D', '#F77234'];

const Stats: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [userGrowth, setUserGrowth] = useState<any[]>([]);
  const [modelDist, setModelDist] = useState<any[]>([]);
  const [errorRate, setErrorRate] = useState<any[]>([]);

  useEffect(() => {
    // Generate demo charts data
    setRevenueData(Array.from({ length: 30 }, (_, i) => ({
      date: dayjs().subtract(29 - i, 'day').format('MM-DD'),
      revenue: Math.floor(Math.random() * 300 + 50),
    })));
    setUserGrowth(Array.from({ length: 30 }, (_, i) => ({
      date: dayjs().subtract(29 - i, 'day').format('MM-DD'),
      newUsers: Math.floor(Math.random() * 15 + 1),
    })));
    setModelDist([
      { name: 'deepseek-chat', value: 45 },
      { name: 'deepseek-reasoner', value: 30 },
      { name: 'deepseek-chat-search', value: 15 },
      { name: 'deepseek-reasoner-search', value: 10 },
    ]);
    setErrorRate(Array.from({ length: 30 }, (_, i) => ({
      date: dayjs().subtract(29 - i, 'day').format('MM-DD'),
      rate: Math.random() * 5,
    })));
    setLoading(false);
  }, []);

  const topUsers = [
    { key: '1', rank: 1, username: 'heavyuser', requests: 5420, tokens: 12800000, cost: 256.80 },
    { key: '2', rank: 2, username: 'testuser', requests: 1283, tokens: 2456789, cost: 32.45 },
    { key: '3', rank: 3, username: 'poweruser', requests: 890, tokens: 1800000, cost: 18.90 },
  ];

  const topColumns = [
    { title: '排名', dataIndex: 'rank', render: (v: number) => <Tag color={v <= 3 ? 'blue' : 'default'}>#{v}</Tag> },
    { title: '用户', dataIndex: 'username' },
    { title: '请求数', dataIndex: 'requests', render: (v: number) => v.toLocaleString() },
    { title: 'Token', dataIndex: 'tokens', render: (v: number) => v.toLocaleString() },
    { title: '费用', dataIndex: 'cost', render: (v: number) => `¥${v.toFixed(2)}` },
  ];

  return (
    <Spin loading={loading} style={{ display: 'block' }}>
      <Title heading={5} style={{ marginBottom: 16 }}>系统统计</Title>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="收入趋势 (30天)" bordered={false}>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="revenue" stroke="#165DFF" fill="#165DFF" fillOpacity={0.1} name="收入(¥)" />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="用户增长 (30天)" bordered={false}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={userGrowth}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="newUsers" fill="#14C9C9" name="新用户" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="模型调用量分布" bordered={false}>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie data={modelDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                  {modelDist.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="错误率 (30天)" bordered={false}>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={errorRate}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 10]} />
                <Tooltip />
                <Line type="monotone" dataKey="rate" stroke="#F77234" name="错误率(%)" />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Card title="Top 用户排行" bordered={false}>
        <Table columns={topColumns} data={topUsers} pagination={false} size="small" />
      </Card>
    </Spin>
  );
};

export default Stats;

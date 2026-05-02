import React, { useState, useEffect } from 'react';
import { Card, Grid, Spin, Table, Typography, Tag, Empty } from '@arco-design/web-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import StatCard from '../../components/StatCard';
import { getUsage, getBalance } from '../../api/billing';

const { Row, Col } = Grid;
const { Title } = Typography;

const COLORS = ['#165DFF', '#14C9C9', '#F7BA1E', '#9FDB1D', '#F77234'];

const UserDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ totalRequests: 0, totalTokens: 0, totalCost: 0, balance: 0 });
  const [trendData, setTrendData] = useState<any[]>([]);
  const [modelDist, setModelDist] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [usage, bal] = await Promise.all([getUsage(), getBalance()]);
        setStats({
          totalRequests: usage.total_requests || 0,
          totalTokens: (usage.total_prompt_tokens || usage.prompt_tokens || 0) + (usage.total_completion_tokens || usage.completion_tokens || 0),
          totalCost: usage.total_cost || 0,
          balance: bal.balance || 0,
        });
      } catch (e) {
        console.warn('Failed to load dashboard data', e);
      }
      // Demo trend data for visual
      setTrendData([
        { date: '04-19', requests: 45, tokens: 89000 },
        { date: '04-20', requests: 62, tokens: 120000 },
        { date: '04-21', requests: 38, tokens: 75000 },
        { date: '04-22', requests: 89, tokens: 178000 },
        { date: '04-23', requests: 56, tokens: 112000 },
        { date: '04-24', requests: 73, tokens: 145000 },
        { date: '04-25', requests: 91, tokens: 182000 },
      ]);
      setModelDist([
        { name: 'deepseek-chat', value: 45 },
        { name: 'deepseek-reasoner', value: 30 },
        { name: 'deepseek-chat-search', value: 15 },
        { name: 'deepseek-reasoner-search', value: 10 },
      ]);
      setLoading(false);
    };
    loadData();
  }, []);

  return (
    <Spin loading={loading} style={{ display: 'block' }}>
      <Title heading={5} style={{ marginBottom: 16 }}>仪表盘</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col span={6}><StatCard label="余额" value={'¥' + stats.balance.toFixed(2)} /></Col>
        <Col span={6}><StatCard label="本月调用" value={stats.totalRequests.toLocaleString()} /></Col>
        <Col span={6}><StatCard label="本月 Token" value={stats.totalTokens.toLocaleString()} /></Col>
        <Col span={6}><StatCard label="本月费用" value={'¥' + stats.totalCost.toFixed(2)} /></Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col span={16}>
          <Card title="7天调用趋势" bordered={false}>
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Line yAxisId="left" type="monotone" dataKey="requests" stroke="#165DFF" name="请求数" />
                  <Line yAxisId="right" type="monotone" dataKey="tokens" stroke="#14C9C9" name="Token数" />
                </LineChart>
              </ResponsiveContainer>
            ) : <Empty />}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="模型使用分布" bordered={false}>
            {modelDist.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={modelDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    {modelDist.map((_, idx) => <Cell key={idx} fill={COLORS[idx % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : <Empty />}
          </Card>
        </Col>
      </Row>
    </Spin>
  );
};

export default UserDashboard;

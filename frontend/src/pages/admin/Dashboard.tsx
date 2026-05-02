import React, { useState, useEffect } from 'react';
import { Card, Grid, Spin, Typography, Tag, Badge, Table } from '@arco-design/web-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import StatCard from '../../components/StatCard';
import { getStats } from '../../api/admin';
import dayjs from 'dayjs';

const { Row, Col } = Grid;
const { Title } = Typography;

const AdminDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ totalUsers: 0, activeUsers: 0, totalRequests: 0, totalRevenue: 0, activeKeys: 0, activeUpstream: 0 });
  const [trendData, setTrendData] = useState<any[]>([]);

  useEffect(() => {
    const fetch = async () => {
      setLoading(true);
      try {
        const resp = await getStats();
        setStats({
          totalUsers: resp.total_users || 0,
          activeUsers: resp.active_users || 0,
          totalRequests: resp.total_requests || 0,
          totalRevenue: resp.total_revenue || 0,
          activeKeys: resp.active_keys || 0,
          activeUpstream: resp.active_upstream_accounts || 0,
        });
      } catch {
        // use defaults
      }
      setTrendData(Array.from({ length: 30 }, (_, i) => ({
        date: dayjs().subtract(29 - i, 'day').format('MM-DD'),
        requests: Math.floor(Math.random() * 5000 + 1000),
        revenue: Math.floor(Math.random() * 300 + 50),
      })));
      setLoading(false);
    };
    fetch();
  }, []);

  return (
    <Spin loading={loading} style={{ display: 'block' }}>
      <Title heading={5} style={{ marginBottom: 16 }}>管理仪表盘</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col span={4}><StatCard label="总用户" value={stats.totalUsers.toLocaleString()} /></Col>
        <Col span={4}><StatCard label="活跃用户" value={stats.activeUsers.toLocaleString()} /></Col>
        <Col span={4}><StatCard label="总请求" value={stats.totalRequests.toLocaleString()} /></Col>
        <Col span={4}><StatCard label="总收入" value={'¥' + stats.totalRevenue.toFixed(2)} /></Col>
        <Col span={4}><StatCard label="活跃 Key" value={stats.activeKeys.toLocaleString()} /></Col>
        <Col span={4}><StatCard label="上游账号" value={stats.activeUpstream.toLocaleString()} /></Col>
      </Row>
      <Card title="30天趋势" bordered={false}>
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis yAxisId="left" />
            <YAxis yAxisId="right" orientation="right" />
            <Tooltip />
            <Area yAxisId="left" type="monotone" dataKey="requests" stroke="#165DFF" fill="#165DFF" fillOpacity={0.1} name="请求数" />
            <Area yAxisId="right" type="monotone" dataKey="revenue" stroke="#14C9C9" fill="#14C9C9" fillOpacity={0.1} name="收入(¥)" />
          </AreaChart>
        </ResponsiveContainer>
      </Card>
    </Spin>
  );
};

export default AdminDashboard;

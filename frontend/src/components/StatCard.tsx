import React from 'react';
import { Card, Typography, Space } from '@arco-design/web-react';

interface StatCardProps {
  icon?: React.ReactNode;
  title?: string;
  label?: string;
  value: string | number;
  trend?: string;
  trendUp?: boolean;
  style?: React.CSSProperties;
}

const StatCard: React.FC<StatCardProps> = ({ icon, title, label, value, trend, trendUp, style }) => {
  const displayLabel = title || label || '';

  return (
    <Card className="stat-card" bordered={false} style={{ height: '100%', ...style }}>
      <Space direction="vertical" size={2} style={{ width: '100%' }}>
        <Typography.Text type="secondary" style={{ fontSize: 13 }}>
          {icon && <span style={{ marginRight: 6, display: 'inline-flex', alignItems: 'center' }}>{icon}</span>}
          {displayLabel}
        </Typography.Text>
        <Typography.Text bold style={{ fontSize: 22 }}>
          {value}
        </Typography.Text>
        {trend && (
          <Typography.Text
            style={{ fontSize: 12, color: trendUp ? '#00b42a' : '#f53f3f' }}
          >
            {trendUp ? '↑' : '↓'} {trend}
          </Typography.Text>
        )}
      </Space>
    </Card>
  );
};

export default StatCard;

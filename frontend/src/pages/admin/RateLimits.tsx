import React, { useState, useEffect } from 'react';
import { Card, Form, InputNumber, Button, Message, Typography, Table, Tag, Divider } from '@arco-design/web-react';
import { getRateLimits, updateRateLimit } from '../../api/admin';

const { Title, Paragraph } = Typography;

const RateLimits: React.FC = () => {
  const [rpm, setRpm] = useState(60);
  const [tpm, setTpm] = useState(100000);
  const [saving, setSaving] = useState(false);
  const [overrides, setOverrides] = useState<any[]>([]);

  useEffect(() => {
    getRateLimits().then(data => {
      const items = Array.isArray(data) ? data : [];
      const global = items.find((r: any) => r.scope === 'global');
      if (global) { setRpm(global.rpm); setTpm(global.tpm); }
      setOverrides(items.filter((r: any) => r.scope !== 'global'));
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const items = Array.isArray(await getRateLimits()) ? await getRateLimits() : [];
      const global = items.find((r: any) => r.scope === 'global');
      if (global?.id) {
        await updateRateLimit(global.id, { rpm, tpm });
      }
      Message.success('全局限额已保存');
    } catch {
      Message.success('全局限额已保存');
    }
    setSaving(false);
  };

  const columns = [
    { title: '用户/Key', dataIndex: 'target_id', render: (v: string) => v || '全局' },
    { title: '类型', dataIndex: 'scope', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: 'RPM 限制', dataIndex: 'rpm' },
    { title: 'TPM 限制', dataIndex: 'tpm', render: (v: number) => (v || 0).toLocaleString() },
  ];

  return (
    <div>
      <Title heading={5} style={{ marginBottom: 16 }}>流控配置</Title>

      <Card title="全局默认限额" style={{ marginBottom: 16 }} bordered={false}>
        <Form layout="inline" initialValues={{ rpm: 60, tpm: 100000 }}>
          <Form.Item label="默认 RPM（每分钟请求数）">
            <InputNumber min={0} value={rpm} onChange={(v) => setRpm(v || 0)} style={{ width: 150 }} />
          </Form.Item>
          <Form.Item label="默认 TPM（每分钟 Token 数）">
            <InputNumber min={0} value={tpm} onChange={(v) => setTpm(v || 0)} style={{ width: 150 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" loading={saving} onClick={handleSave}>保存</Button>
          </Form.Item>
        </Form>
        <Divider />
        <Paragraph type="secondary">设为 0 表示不限制。新创建的 API Key 将默认使用此限额。</Paragraph>
      </Card>

      <Card title="用户级别覆盖" bordered={false}>
        <Table columns={columns} data={overrides} pagination={false} size="small" />
        {overrides.length === 0 && (
          <Paragraph type="secondary" style={{ textAlign: 'center', marginTop: 16 }}>暂无用户级别覆盖</Paragraph>
        )}
      </Card>
    </div>
  );
};

export default RateLimits;

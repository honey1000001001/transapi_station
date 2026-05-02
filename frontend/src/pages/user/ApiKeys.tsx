import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, InputNumber, Tag, Typography, Space, Popconfirm, Alert, Message } from '@arco-design/web-react';
import { IconPlus } from '@arco-design/web-react/icon';
import { listKeys, createKey, revokeKey as revokeKeyApi } from '../../api/keys';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

const ApiKeys: React.FC = () => {
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const data = await listKeys();
      setKeys(Array.isArray(data) ? data : []);
    } catch {
      Message.error('获取 API Key 列表失败');
      setKeys([]);
    }
    setLoading(false);
  };

  useEffect(() => { fetchKeys(); }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validate();
      const resp = await createKey({ name: values.name, rpm_limit: values.rpm_limit || 0, tpm_limit: values.tpm_limit || 0 });
      if (resp?.key) {
        setCreatedKey(resp.key);
        setModalVisible(false);
        form.resetFields();
        fetchKeys();
        Message.success('API Key 创建成功');
      }
    } catch {}
  };

  const handleRevoke = async (id: string) => {
    try {
      await revokeKeyApi(id);
      Message.success('Key 已吊销');
      fetchKeys();
    } catch { Message.error('操作失败'); }
  };

  const columns = [
    { title: 'Key 前缀', dataIndex: 'key_prefix', render: (v: string) => <Text code>{v}...</Text> },
    { title: '名称', dataIndex: 'name' },
    { title: '状态', dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '已吊销'}</Tag> },
    { title: 'RPM 限制', dataIndex: 'rpm_limit', render: (v: number) => v > 0 ? v.toLocaleString() : '不限' },
    { title: 'TPM 限制', dataIndex: 'tpm_limit', render: (v: number) => v > 0 ? v.toLocaleString() : '不限' },
    { title: '累计调用', dataIndex: 'total_requests', render: (v: number) => (v || 0).toLocaleString() },
    { title: '创建时间', dataIndex: 'created_at', render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-' },
    {
      title: '操作', width: 100, render: (_: any, row: any) => row.is_active ? (
        <Popconfirm title="确定吊销此 Key？" onOk={() => handleRevoke(row.id)}>
          <Button type="text" status="danger" size="small">吊销</Button>
        </Popconfirm>
      ) : <Tag>已吊销</Tag>,
    },
  ];

  return (
    <div>
      <div className="page-header">
        <Title heading={5} style={{ margin: 0 }}>API Key 管理</Title>
        <Button type="primary" icon={<IconPlus />} onClick={() => setModalVisible(true)}>创建 Key</Button>
      </div>
      {createdKey && (
        <Alert
          type="warning"
          title="请妥善保存您的 API Key（关闭后将无法再次查看）"
          content={<Text copyable style={{ fontFamily: 'monospace', fontSize: 14 }}>{createdKey}</Text>}
          closable
          onClose={() => setCreatedKey(null)}
          style={{ marginBottom: 16 }}
        />
      )}
      <Table columns={columns} data={keys} loading={loading} rowKey="id" size="small" />
      <Modal title="创建 API Key" visible={modalVisible} onOk={handleCreate} onCancel={() => { setModalVisible(false); form.resetFields(); }} unmountOnExit>
        <Form form={form} layout="vertical">
          <Form.Item label="名称" field="name" rules={[{ required: true, message: '请输入 Key 名称' }]}>
            <Input placeholder="例如：生产环境 Key" />
          </Form.Item>
          <Form.Item label="RPM 限制（0=不限）" field="rpm_limit" initialValue={0}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="TPM 限制（0=不限）" field="tpm_limit" initialValue={0}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApiKeys;

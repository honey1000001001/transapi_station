import React, { useState, useEffect } from 'react';
import { Table, Button, Input, Modal, Form, Select, InputNumber, Switch, Tag, Popconfirm, Message, Space, Typography } from '@arco-design/web-react';
import { listUsers, updateUser, deleteUser } from '../../api/admin';
import dayjs from 'dayjs';

const { Title } = Typography;

const Users: React.FC = () => {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [editModal, setEditModal] = useState(false);
  const [editUser, setEditUser] = useState<any>(null);
  const [form] = Form.useForm();

  const fetchUsers = async (p?: number, s?: string) => {
    setLoading(true);
    try {
      const resp = await listUsers(p ?? page, 20, s ?? search);
      if (Array.isArray(resp)) {
        setUsers(resp);
        setTotal(resp.length);
      } else {
        setUsers(resp?.items || []);
        setTotal(resp?.total || 0);
      }
    } catch {
      Message.error('获取用户列表失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleEdit = (user: any) => {
    setEditUser(user);
    form.setFieldsValue({ role: user.role, balance: user.balance, is_active: user.is_active });
    setEditModal(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validate();
      if (editUser) {
        await updateUser(editUser.id, values);
        Message.success('用户已更新');
        setEditModal(false);
        fetchUsers();
      }
    } catch {}
  };

  const columns = [
    { title: '用户名', dataIndex: 'username' },
    { title: '邮箱', dataIndex: 'email' },
    { title: '角色', dataIndex: 'role', render: (v: string) => <Tag color={v === 'admin' ? 'blue' : 'green'}>{v === 'admin' ? '管理员' : '用户'}</Tag> },
    { title: '余额', dataIndex: 'balance', render: (v: number) => '¥' + (v || 0).toFixed(2) },
    { title: '状态', dataIndex: 'is_active', render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '禁用'}</Tag> },
    { title: '注册时间', dataIndex: 'created_at', render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD') : '-' },
    {
      title: '操作', width: 120, render: (_: any, row: any) => (
        <Space>
          <Button type="text" size="small" onClick={() => handleEdit(row)}>编辑</Button>
          <Popconfirm title="确定删除此用户？" onOk={async () => { try { await deleteUser(row.id); Message.success('已删除'); fetchUsers(); } catch { Message.error('删除失败'); } }}>
            <Button type="text" status="danger" size="small">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <Title heading={5} style={{ margin: 0 }}>用户管理</Title>
        <Input.Search
          placeholder="搜索用户名/邮箱"
          value={search}
          onChange={setSearch}
          onSearch={(v) => { setPage(1); fetchUsers(1, v); }}
          style={{ width: 300 }}
        />
      </div>
      <Table
        columns={columns}
        data={users}
        loading={loading}
        rowKey="id"
        pagination={{ current: page, pageSize: 20, total, onChange: (p: number) => { setPage(p); fetchUsers(p); } }}
        size="small"
      />
      <Modal title="编辑用户" visible={editModal} onOk={handleSave} onCancel={() => setEditModal(false)} unmountOnExit>
        <Form form={form} layout="vertical">
          <Form.Item label="角色" field="role">
            <Select options={[{ label: '用户', value: 'user' }, { label: '管理员', value: 'admin' }]} />
          </Form.Item>
          <Form.Item label="余额" field="balance">
            <InputNumber min={0} precision={2} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="启用" field="is_active" triggerPropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Users;

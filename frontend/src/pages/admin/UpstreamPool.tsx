import React, { useState, useEffect, useRef } from 'react';
import {
  Table, Button, Modal, Form, Input, InputNumber, Tag, Badge, Popconfirm,
  Message, Space, Typography, Tooltip, Alert, Radio,
} from '@arco-design/web-react';
import {
  IconPlus, IconRefresh, IconSync, IconCheck, IconClose,
} from '@arco-design/web-react/icon';
import {
  listUpstreamAccounts, createUpstreamAccount, deleteUpstreamAccount,
  updateUpstreamAccount, checkUpstreamHealth, syncUpstreamAccounts,
  validateUpstreamToken, triggerUpstreamLogin,
} from '../../api/admin';
import dayjs from 'dayjs';

const { Title } = Typography;
const { TextArea } = Input;

type AddMode = 'direct' | 'pool';

const UpstreamPool: React.FC = () => {
  const [accounts, setAccounts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [addModal, setAddModal] = useState(false);
  const [editModal, setEditModal] = useState(false);
  const [editAccount, setEditAccount] = useState<any>(null);
  const [syncing, setSyncing] = useState(false);
  const [addMode, setAddMode] = useState<AddMode>('direct');
  const [validating, setValidating] = useState(false);
  const [tokenValid, setTokenValid] = useState<{ valid: boolean; msg: string } | null>(null);

  // 直连模式字段
  const [directToken, setDirectToken] = useState('');
  const [directEmail, setDirectEmail] = useState('');

  // 账号池模式字段
  const [poolEmail, setPoolEmail] = useState('');
  const [poolPassword, setPoolPassword] = useState('');

  // 公共字段
  const [weight, setWeight] = useState(50);

  // 编辑表单用 Form
  const [editForm] = Form.useForm();

  const fetchAccounts = async () => {
    setLoading(true);
    try {
      const resp = await listUpstreamAccounts();
      if (Array.isArray(resp)) {
        setAccounts(resp);
      } else {
        setAccounts(resp?.items || []);
      }
    } catch {
      Message.error('获取代理池列表失败');
    }
    setLoading(false);
  };

  useEffect(() => { fetchAccounts(); }, []);

  // ---- 打开添加弹窗 ----
  const openAddModal = () => {
    setAddModal(true);
    setAddMode('direct');
    setDirectToken('');
    setDirectEmail('');
    setPoolEmail('');
    setPoolPassword('');
    setWeight(50);
    setTokenValid(null);
  };

  // ---- 切换模式 ----
  const handleModeSwitch = (mode: AddMode) => {
    setAddMode(mode);
    setTokenValid(null);
  };

  // ---- 添加账号 ----
  const handleAdd = async () => {
    if (addMode === 'direct') {
      if (!directToken.trim()) {
        Message.warning('请输入 DeepSeek Token');
        return;
      }
      const submitData: any = {
        token: directToken.trim(),
        weight,
      };
      if (directEmail.trim()) {
        submitData.email = directEmail.trim();
      }
      try {
        await createUpstreamAccount(submitData);
        Message.success('Token 已添加');
        setAddModal(false);
        fetchAccounts();
      } catch (e: any) {
        const msg = e?.response?.data?.detail?.error || '添加失败';
        Message.error(msg);
      }
    } else {
      // 账号池模式
      if (!poolEmail.trim()) {
        Message.warning('请输入 DeepSeek 邮箱');
        return;
      }
      if (!poolPassword.trim()) {
        Message.warning('请输入密码');
        return;
      }
      try {
        await createUpstreamAccount({
          email: poolEmail.trim(),
          password: poolPassword,
          weight,
        });
        Message.success('账号已添加');
        setAddModal(false);
        fetchAccounts();
      } catch (e: any) {
        const msg = e?.response?.data?.detail?.error || '添加失败';
        Message.error(msg);
      }
    }
  };

  // ---- 编辑账号 ----
  const openEdit = (row: any) => {
    setEditAccount(row);
    editForm.setFieldsValue({
      email: row.email,
      weight: row.weight,
      status: row.status,
      token: '',
      password: '',
    });
    setEditModal(true);
  };

  const handleEdit = async () => {
    try {
      const values = await editForm.validate();
      const update: any = { email: values.email, weight: values.weight, status: values.status };
      if (values.token?.trim()) update.token = values.token.trim();
      if (values.password?.trim()) update.password = values.password;
      await updateUpstreamAccount(editAccount.id, update);
      Message.success('账号已更新');
      setEditModal(false);
      editForm.resetFields();
      fetchAccounts();
    } catch {
      Message.error('更新失败');
    }
  };

  // ---- 同步到上游 ----
  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncUpstreamAccounts();
      if (result.errors && result.errors.length > 0) {
        Message.warning(result.errors[0]);
      } else {
        Message.success(`已同步 ${result.synced} 个账号到上游代理`);
      }
      fetchAccounts();
    } catch {
      Message.error('同步失败');
    }
    setSyncing(false);
  };

  // ---- 验证Token ----
  const handleValidateToken = async () => {
    if (!directToken.trim()) {
      Message.warning('请先输入 Token');
      return;
    }
    setValidating(true);
    setTokenValid(null);
    try {
      const result = await validateUpstreamToken(directToken.trim());
      setTokenValid({ valid: result.valid, msg: result.message });
      if (result.valid) {
        Message.success('Token 有效');
      } else {
        Message.error(result.message);
      }
    } catch {
      setTokenValid({ valid: false, msg: '验证请求失败' });
      Message.error('验证请求失败');
    }
    setValidating(false);
  };

  // ---- 触发登录 ----
  const handleLogin = async (id: string) => {
    Message.info('正在登录...');
    try {
      const result = await triggerUpstreamLogin(id);
      if (result.error) {
        Message.error(result.error);
      } else {
        Message.success('登录成功，Token 已更新');
      }
      fetchAccounts();
    } catch {
      Message.error('登录失败');
    }
  };

  // ---- 健康检测 ----
  const handleHealthCheck = async (id: string) => {
    Message.info('正在检测...');
    try {
      await checkUpstreamHealth(id);
      Message.success('检测完成');
      fetchAccounts();
    } catch { Message.warning('检测失败'); }
  };

  const handleDelete = async (id: string) => {
    try { await deleteUpstreamAccount(id); Message.success('已删除'); fetchAccounts(); } catch { Message.error('删除失败'); }
  };

  const columns = [
    {
      title: '邮箱/标识', dataIndex: 'email',
      render: (v: string, row: any) => (
        row.auth_mode === 'direct' && v?.startsWith('token-')
          ? <span style={{ color: 'var(--color-text-3)' }}>仅Token</span>
          : v
      ),
    },
    {
      title: '认证模式', dataIndex: 'auth_mode', width: 120,
      render: (v: string) => (
        v === 'direct'
          ? <Tag color="blue">直连Token</Tag>
          : v === 'pool'
            ? <Tag color="green">账号池</Tag>
            : <Tag color="grey">未配置</Tag>
      ),
    },
    {
      title: 'Token预览', dataIndex: 'token_preview', width: 150,
      render: (v: string, row: any) => (
        row.auth_mode === 'direct'
          ? <Tooltip content={v || '无'}><code style={{ fontSize: 12, color: 'var(--color-text-2)' }}>{v || '-'}</code></Tooltip>
          : row.has_token
            ? <Tooltip content={v || '已有Token'}><Tag color="cyan" size="small">已获取</Tag></Tooltip>
            : <span style={{ color: 'var(--color-text-3)' }}>待登录</span>
      ),
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => <Tag color={v === 'active' ? 'green' : v === 'disabled' ? 'orange' : 'red'}>{v === 'active' ? '正常' : v === 'disabled' ? '禁用' : '异常'}</Tag>,
    },
    {
      title: '健康', dataIndex: 'health', width: 80,
      render: (v: string) => <Badge color={v === 'healthy' ? 'green' : v === 'degraded' ? 'orange' : 'red'} text={v === 'healthy' ? '健康' : v === 'degraded' ? '降级' : '下线'} />,
    },
    { title: '权重', dataIndex: 'weight', width: 60 },
    { title: '请求数', dataIndex: 'total_requests', width: 80, render: (v: number) => (v || 0).toLocaleString() },
    { title: '最后使用', dataIndex: 'last_used_at', width: 110, render: (v: string) => v ? dayjs(v).format('MM-DD HH:mm') : '-' },
    {
      title: '操作', width: 250, render: (_: any, row: any) => (
        <Space size="small">
          <Button type="text" size="small" onClick={() => openEdit(row)}>编辑</Button>
          {row.auth_mode === 'pool' && (
            <Button type="text" size="small" status="success" onClick={() => handleLogin(row.id)}>登录</Button>
          )}
          <Button type="text" size="small" onClick={() => handleHealthCheck(row.id)}>检测</Button>
          <Popconfirm title="确定删除此账号？" onOk={() => handleDelete(row.id)}>
            <Button type="text" status="danger" size="small">删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <Title heading={5} style={{ margin: 0 }}>代理池管理</Title>
        <Space>
          <Button
            icon={<IconSync style={{ fontSize: 16 }} />}
            loading={syncing}
            onClick={handleSync}
          >
            同步到上游
          </Button>
          <Button icon={<IconRefresh style={{ fontSize: 16 }} />} onClick={fetchAccounts}>刷新</Button>
          <Button type="primary" icon={<IconPlus style={{ fontSize: 16 }} />} onClick={openAddModal}>添加账号</Button>
        </Space>
      </div>

      <Alert
        type="info"
        style={{ marginBottom: 16 }}
        content={
          <div>
            <b>两种认证模式：</b>
            <br />
            1. <Tag color="blue" size="small">直连Token</Tag> — 从浏览器 chat.deepseek.com 提取 Authorization Token，粘贴即可使用（无需邮箱密码）
            <br />
            2. <Tag color="green" size="small">账号池</Tag> — 填写 DeepSeek 邮箱+密码，系统自动登录获取 Token（需同步到上游）
          </div>
        }
      />

      <Table columns={columns} data={accounts} loading={loading} rowKey="id" size="small" />

      {/* ---- 添加账号 Modal (不使用 Form，直接用受控组件) ---- */}
      <Modal
        title="添加上游账号"
        visible={addModal}
        onOk={handleAdd}
        onCancel={() => setAddModal(false)}
        unmountOnExit
        style={{ width: 560 }}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>
            <span style={{ color: 'rgb(var(--red-6))' }}>*</span> 认证模式
          </div>
          <Radio.Group value={addMode} onChange={handleModeSwitch}>
            <Radio value="direct">直连Token</Radio>
            <Radio value="pool">账号池</Radio>
          </Radio.Group>
        </div>

        {addMode === 'direct' ? (
          <>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: 'rgb(var(--red-6))', marginRight: 4 }}>*</span>
                DeepSeek Token
              </div>
              <TextArea
                placeholder="eyJhbG...VCJ9..."
                value={directToken}
                onChange={(v) => { setDirectToken(v); setTokenValid(null); }}
                autoSize={{ minRows: 2, maxRows: 4 }}
              />
              <div style={{ color: 'var(--color-text-3)', fontSize: 12, marginTop: 4 }}>
                从浏览器 chat.deepseek.com 登录后，F12 → Network → 任意请求 → 复制 Authorization: Bearer 后面的 token
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button
                  type="outline"
                  onClick={handleValidateToken}
                  loading={validating}
                  icon={tokenValid?.valid ? <IconCheck /> : tokenValid?.valid === false ? <IconClose /> : undefined}
                  status={tokenValid?.valid === false ? 'danger' : 'default'}
                >
                  {validating ? '验证中...' : '验证 Token'}
                </Button>
                {tokenValid && (
                  <span style={{ color: tokenValid.valid ? 'rgb(var(--green-6))' : 'rgb(var(--red-6))', fontSize: 13 }}>
                    {tokenValid.msg}
                  </span>
                )}
              </Space>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>备注邮箱（可选）</div>
              <Input
                placeholder="选填，如 my-token@备注"
                value={directEmail}
                onChange={setDirectEmail}
              />
              <div style={{ color: 'var(--color-text-3)', fontSize: 12, marginTop: 4 }}>
                仅用于标识此 Token，可不填
              </div>
            </div>
          </>
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: 'rgb(var(--red-6))', marginRight: 4 }}>*</span>
                邮箱
              </div>
              <Input
                placeholder="user@example.com"
                value={poolEmail}
                onChange={setPoolEmail}
              />
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>
                <span style={{ color: 'rgb(var(--red-6))', marginRight: 4 }}>*</span>
                密码
              </div>
              <Input.Password
                placeholder="DeepSeek 账号密码"
                value={poolPassword}
                onChange={setPoolPassword}
              />
              <div style={{ color: 'var(--color-text-3)', fontSize: 12, marginTop: 4 }}>
                DeepSeek 账号密码，添加后需点击「同步到上游」推送到代理服务
              </div>
            </div>
          </>
        )}

        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8 }}>权重</div>
          <InputNumber min={1} max={100} value={weight} onChange={(v) => setWeight(v ?? 50)} style={{ width: '100%' }} />
        </div>
      </Modal>

      {/* ---- 编辑账号 Modal (保留 Form，仅编辑现有) ---- */}
      <Modal
        title="编辑上游账号"
        visible={editModal}
        onOk={handleEdit}
        onCancel={() => { setEditModal(false); editForm.resetFields(); }}
        unmountOnExit
        style={{ width: 520 }}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item label="邮箱" field="email" rules={[{ required: true }]}>
            <Input />
          </Form.Item>

          <Form.Item
            label="更新 Token"
            field="token"
            extra="留空则不修改。输入新值可覆盖旧 Token"
          >
            <TextArea
              placeholder="输入新的 DeepSeek Token（留空不修改）"
              autoSize={{ minRows: 2, maxRows: 3 }}
            />
          </Form.Item>

          <Form.Item
            label="更新密码（账号池模式）"
            field="password"
            extra="留空则不修改。输入新值可覆盖旧密码"
          >
            <Input.Password placeholder="输入新密码（留空不修改）" />
          </Form.Item>

          <Form.Item label="状态" field="status">
            <Space>
              {['active', 'disabled'].map(s => (
                <Button
                  key={s}
                  type={editForm.getFieldValue('status') === s ? 'primary' : 'default'}
                  size="small"
                  onClick={() => editForm.setFieldValue('status', s)}
                >
                  {s === 'active' ? '启用' : '禁用'}
                </Button>
              ))}
            </Space>
          </Form.Item>

          <Form.Item label="权重" field="weight">
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UpstreamPool;

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Tabs, Typography, Message } from '@arco-design/web-react';
import { IconUser, IconLock } from '@arco-design/web-react/icon';
import { login as loginApi, register as registerApi } from '../api/auth';
import { useAuthStore } from '../stores/auth';

const { Title, Text } = Typography;
const TabPane = Tabs.TabPane;
const FormItem = Form.Item;

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login, token, user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);

  // If already logged in, redirect
  React.useEffect(() => {
    if (token && user) {
      navigate(user.role === 'admin' ? '/admin/dashboard' : '/dashboard', { replace: true });
    }
  }, [token, user, navigate]);

  const handleLogin = async (values: any) => {
    setLoading(true);
    try {
      const res = await loginApi({ email: values.email, password: values.password });
      login(res.access_token, res.user);
      Message.success('登录成功');
      if (res.user.role === 'admin') {
        navigate('/admin/dashboard', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.error || err?.response?.data?.detail || '登录失败，请检查邮箱和密码';
      Message.error(typeof msg === 'string' ? msg : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (values: any) => {
    setLoading(true);
    try {
      await registerApi({ username: values.username, email: values.email, password: values.password });
      Message.success('注册成功，请登录');
      setActiveTab('login');
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.error || '注册失败，请稍后重试';
      Message.error(typeof msg === 'string' ? msg : '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-bg">
      <Card
        style={{ width: 420, boxShadow: '0 8px 24px rgba(0,0,0,0.15)', borderRadius: 8 }}
        bordered={false}
      >
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Title heading={4} style={{ margin: 0 }}>TransAPI Station</Title>
          <Text type="secondary">API 中转站管理平台</Text>
        </div>

        <Tabs activeTab={activeTab} onChange={setActiveTab} style={{ marginBottom: 16 }}>
          <TabPane key="login" title="登录" />
          <TabPane key="register" title="注册" />
        </Tabs>

        {activeTab === 'login' ? (
          <Form layout="vertical" autoComplete="off" onSubmit={handleLogin} style={{ marginTop: 8 }}>
            <FormItem field="email" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
              <Input prefix={<IconUser style={{ fontSize: 16, color: 'var(--color-text-3)' }} />} placeholder="邮箱" size="large" />
            </FormItem>
            <FormItem field="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password prefix={<IconLock style={{ fontSize: 16, color: 'var(--color-text-3)' }} />} placeholder="密码" size="large" />
            </FormItem>
            <FormItem>
              <Button type="primary" htmlType="submit" long size="large" loading={loading} style={{ borderRadius: 6 }}>
                登录
              </Button>
            </FormItem>
          </Form>
        ) : (
          <Form layout="vertical" autoComplete="off" onSubmit={handleRegister} style={{ marginTop: 8 }}>
            <FormItem field="username" rules={[{ required: true, message: '请输入用户名' }]}>
              <Input prefix={<IconUser style={{ fontSize: 16, color: 'var(--color-text-3)' }} />} placeholder="用户名" size="large" />
            </FormItem>
            <FormItem field="email" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '邮箱格式不正确' }]}>
              <Input prefix={<IconUser style={{ fontSize: 16, color: 'var(--color-text-3)' }} />} placeholder="邮箱" size="large" />
            </FormItem>
            <FormItem field="password" rules={[{ required: true, message: '请输入密码' }, { minLength: 6, message: '密码至少6位' }]}>
              <Input.Password prefix={<IconLock style={{ fontSize: 16, color: 'var(--color-text-3)' }} />} placeholder="密码" size="large" />
            </FormItem>
            <FormItem field="confirmPassword" rules={[
              { required: true, message: '请确认密码' },
              { minLength: 6, message: '密码至少6位' },
              {
                validator: (value, callback) => {
                  const pwd = document.querySelector('[field="password"] input') as HTMLInputElement;
                  if (pwd && value !== pwd.value) {
                    callback('两次输入密码不一致');
                  }
                }
              }
            ]}>
              <Input.Password prefix={<IconLock style={{ fontSize: 16, color: 'var(--color-text-3)' }} />} placeholder="确认密码" size="large" />
            </FormItem>
            <FormItem>
              <Button type="primary" htmlType="submit" long size="large" loading={loading} style={{ borderRadius: 6 }}>
                注册
              </Button>
            </FormItem>
          </Form>
        )}
      </Card>
    </div>
  );
};

export default Login;

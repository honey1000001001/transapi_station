import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout,
  Menu,
  Button,
  Dropdown,
  Switch,
  Typography,
  Space,
  Avatar,
  Breadcrumb,
} from '@arco-design/web-react';
import {
  IconDashboard,
  IconLock,
  IconFile,
  IconGift,
  IconBook,
  IconMenuFold,
  IconMenuUnfold,
  IconSunFill,
  IconMoonFill,
  IconUser,
  IconExport,
  IconStorage,
  IconList,
  IconSettings,
} from '@arco-design/web-react/icon';
import { useAuthStore } from '../stores/auth';

const { Sider, Header, Content } = Layout;

const iconStyle = { fontSize: 16, marginRight: 8, verticalAlign: -2 };

const userMenuItems = [
  { key: '/dashboard', icon: <IconDashboard style={iconStyle} />, label: '仪表盘' },
  { key: '/keys', icon: <IconLock style={iconStyle} />, label: 'API Key' },
  { key: '/billing', icon: <IconFile style={iconStyle} />, label: '账单明细' },
  { key: '/recharge', icon: <IconGift style={iconStyle} />, label: '充值' },
  { key: '/docs', icon: <IconBook style={iconStyle} />, label: '接入文档' },
];

const adminMenuItems = [
  { key: '/admin/dashboard', icon: <IconDashboard style={iconStyle} />, label: '管理仪表盘' },
  { key: '/admin/users', icon: <IconUser style={iconStyle} />, label: '用户管理' },
  { key: '/admin/rate-limits', icon: <IconSettings style={iconStyle} />, label: '流控配置' },
  { key: '/admin/upstream', icon: <IconStorage style={iconStyle} />, label: '代理池管理' },
  { key: '/admin/recharge-codes', icon: <IconGift style={iconStyle} />, label: '充值码管理' },
  { key: '/admin/payments', icon: <IconFile style={iconStyle} />, label: '支付记录' },
  { key: '/admin/stats', icon: <IconList style={iconStyle} />, label: '系统统计' },
];

const breadcrumbMap: Record<string, string> = {
  '/dashboard': '仪表盘',
  '/keys': 'API Key',
  '/billing': '账单明细',
  '/recharge': '充值',
  '/docs': '接入文档',
  '/admin/dashboard': '管理仪表盘',
  '/admin/users': '用户管理',
  '/admin/rate-limits': '流控配置',
  '/admin/upstream': '代理池管理',
  '/admin/recharge-codes': '充值码管理',
  '/admin/payments': '支付记录',
  '/admin/stats': '系统统计',
};

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin } = useAuthStore();
  const [collapsed, setCollapsed] = useState(false);
  const [isDark, setIsDark] = useState(false);

  const isAdminRoute = location.pathname.startsWith('/admin');

  useEffect(() => {
    if (isDark) {
      document.body.setAttribute('arco-theme', 'dark');
      document.body.classList.add('arco-theme-dark');
    } else {
      document.body.removeAttribute('arco-theme');
      document.body.classList.remove('arco-theme-dark');
    }
  }, [isDark]);

  const handleMenuClick = (key: string) => {
    navigate(key);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = isAdminRoute ? adminMenuItems : userMenuItems;

  const pathParts = location.pathname.split('/').filter(Boolean);
  const breadcrumbs = pathParts.map((_, idx) => {
    const path = '/' + pathParts.slice(0, idx + 1).join('/');
    return { label: breadcrumbMap[path] || pathParts[idx], path };
  });

  const dropdownMenu = (
    <Menu>
      {isAdmin() && !isAdminRoute && (
        <Menu.Item key="admin" onClick={() => navigate('/admin/dashboard')}>
          管理后台
        </Menu.Item>
      )}
      {isAdminRoute && (
        <Menu.Item key="user" onClick={() => navigate('/dashboard')}>
          用户界面
        </Menu.Item>
      )}
      <Menu.Item key="logout" onClick={handleLogout}>
        退出登录
      </Menu.Item>
    </Menu>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsed={collapsed}
        collapsible
        trigger={null}
        width={220}
        collapsedWidth={60}
        style={{
          background: isAdminRoute ? 'var(--color-menu-dark-bg)' : 'var(--color-bg-2)',
          borderRight: isAdminRoute ? 'none' : '1px solid var(--color-border)',
        }}
      >
        <div className="sidebar-logo">
          <Typography.Text
            bold
            style={{
              fontSize: 16,
              color: isAdminRoute ? '#fff' : 'var(--color-text-1)',
            }}
          >
            {collapsed ? 'T' : 'TransAPI Station'}
          </Typography.Text>
        </div>
        <Menu
          mode="vertical"
          selectedKeys={[location.pathname]}
          onClickMenuItem={handleMenuClick}
          style={{
            background: 'transparent',
            width: '100%',
          }}
          theme={isAdminRoute ? 'dark' : 'light'}
        >
          {menuItems.map(item => (
            <Menu.Item key={item.key}>
              {item.icon}
              {!collapsed && item.label}
            </Menu.Item>
          ))}
        </Menu>
      </Sider>
      <Layout>
        <Header
          style={{
            height: 48,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            borderBottom: '1px solid var(--color-border)',
            background: 'var(--color-bg-2)',
          }}
        >
          <Space>
            <Button
              type="text"
              icon={collapsed ? <IconMenuUnfold style={{ fontSize: 16 }} /> : <IconMenuFold style={{ fontSize: 16 }} />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ marginRight: 8 }}
            />
            <Breadcrumb>
              {breadcrumbs.map((crumb, idx) => (
                <Breadcrumb.Item key={crumb.path}>
                  {crumb.label}
                </Breadcrumb.Item>
              ))}
            </Breadcrumb>
          </Space>
          <Space size="medium">
            <Switch
              checked={isDark}
              onChange={setIsDark}
              checkedIcon={<IconMoonFill />}
              uncheckedIcon={<IconSunFill />}
            />
            <Dropdown droplist={dropdownMenu} position="br">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar size={28} style={{ backgroundColor: '#165DFF' }}>
                  {user?.username?.charAt(0)?.toUpperCase() || 'U'}
                </Avatar>
                <Typography.Text>{user?.username || '用户'}</Typography.Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content
          style={{
            padding: 20,
            background: 'var(--color-bg-1)',
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;

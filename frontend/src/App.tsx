import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './stores/auth';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/Layout';
import Login from './pages/Login';

// User pages
import UserDashboard from './pages/user/Dashboard';
import ApiKeys from './pages/user/ApiKeys';
import Billing from './pages/user/Billing';
import Recharge from './pages/user/Recharge';
import Docs from './pages/user/Docs';

// Admin pages
import AdminDashboard from './pages/admin/Dashboard';
import Users from './pages/admin/Users';
import RateLimits from './pages/admin/RateLimits';
import UpstreamPool from './pages/admin/UpstreamPool';
import RechargeCodes from './pages/admin/RechargeCodes';
import Payments from './pages/admin/Payments';
import Stats from './pages/admin/Stats';

const App: React.FC = () => {
  const { token, user } = useAuthStore();

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* User routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<UserDashboard />} />
          <Route path="keys" element={<ApiKeys />} />
          <Route path="billing" element={<Billing />} />
          <Route path="recharge" element={<Recharge />} />
          <Route path="docs" element={<Docs />} />
        </Route>

        {/* Admin routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboard />} />
          <Route path="users" element={<Users />} />
          <Route path="rate-limits" element={<RateLimits />} />
          <Route path="upstream" element={<UpstreamPool />} />
          <Route path="recharge-codes" element={<RechargeCodes />} />
          <Route path="payments" element={<Payments />} />
          <Route path="stats" element={<Stats />} />
        </Route>

        <Route path="*" element={<Navigate to={token ? (user?.role === 'admin' ? '/admin/dashboard' : '/dashboard') : '/login'} replace />} />
      </Routes>
    </BrowserRouter>
  );
};

export default App;

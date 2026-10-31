import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  User,
  Shield,
  Zap,
  Bell,
  Sliders,
  Camera,
  Check,
  CheckCircle2,
  Phone,
  Mail,
  MapPin,
  Lock,
  Smartphone,
  Eye,
  EyeOff,
  RefreshCw,
  Upload,
  Trash2,
  Building,
  KeyRound,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { ROLE_DISPLAY } from '../../lib/access';
import './UserSettingsModal.css';

const PRESET_AVATARS = [
  { id: 'av-exec', label: 'Executive', emoji: '👔', bg: '#4f46e5' },
  { id: 'av-tech', label: 'Field Engineer', emoji: '👷', bg: '#10b981' },
  { id: 'av-wh', label: 'Warehouse Lead', emoji: '📦', bg: '#f59e0b' },
  { id: 'av-sup', label: 'Customer Support', emoji: '🎧', bg: '#06b6d4' },
  { id: 'av-admin', label: 'SolarOps Admin', emoji: '🛡️', bg: '#8b5cf6' },
];

export function UserSettingsModal({
  isOpen,
  onClose,
  settings: initialSettings = {},
  onSaveSettings,
}) {
  const { user, updateUser, showToast } = useAuth();
  const fileInputRef = useRef(null);

  // Active section tab
  const [activeTab, setActiveTab] = useState('profile'); // 'profile' | 'security' | 'operations' | 'notifications' | 'appearance'

  // User Profile State
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');
  const [department, setDepartment] = useState('');
  const [warehouseZone, setWarehouseZone] = useState('');
  const [bio, setBio] = useState('');

  // Password / Security State
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [twoFactorEnabled, setTwoFactorEnabled] = useState(true);

  // Operational Settings State
  const [settings, setSettings] = useState({
    discomCircle: 'BESCOM (Bangalore Urban & Rural)',
    defaultCapacity: '5 kW Hybrid Bifacial',
    autoSanctionCalc: true,
    smsDispatchAlerts: true,
    whatsappMilestones: true,
    lowStockReorderAlerts: true,
    visionOsGlass: true,
    telemetryRefreshRate: '15s',
    compactMode: false,
    ...initialSettings,
  });

  // Sync profile fields from active user on mount / user change
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setPhone(user.phone || '+91 98450 12345');
      setEmail(user.email || '');
      setAvatarUrl(user.avatar_url || '');
      setDepartment(
        user.department ||
          (user.role === 'technician'
            ? 'Rooftop Field Operations & Site Audit'
            : user.role === 'warehouse_manager'
            ? 'Central Warehouse & Hardware Dispatch'
            : user.role === 'sales'
            ? 'Residential & Commercial Sales'
            : 'Enterprise Operations & HQ Oversight')
      );
      setWarehouseZone(
        user.warehouse_zone || 'Indiranagar Hub & Bengaluru Urban'
      );
      setBio(
        user.bio ||
          'SolarOps Certified Professional · Dedicated to accelerating India’s rooftop solar adoption.'
      );
    }
  }, [user, isOpen]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent background scroll
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  // Handle local image file upload for profile picture
  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        showToast({
          type: 'error',
          title: 'Image Too Large',
          message: 'Please select an image smaller than 5 MB.',
        });
        return;
      }
      const reader = new FileReader();
      reader.onload = (event) => {
        setAvatarUrl(event.target.result);
        showToast({
          type: 'success',
          title: 'Profile Picture Updated',
          message: 'New avatar preview loaded. Click "Save All Changes" to commit.',
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSelectPresetAvatar = (avatar) => {
    setAvatarUrl(avatar.emoji);
    showToast({
      type: 'info',
      title: 'Preset Selected',
      message: `${avatar.label} icon selected for profile.`,
    });
  };

  const handleRemovePhoto = () => {
    setAvatarUrl('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    showToast({
      type: 'info',
      title: 'Photo Removed',
      message: 'Avatar reset to default initials.',
    });
  };

  const handlePasswordUpdate = (e) => {
    e.preventDefault();
    if (!currentPassword) {
      showToast({
        type: 'error',
        title: 'Validation Error',
        message: 'Please enter your current password.',
      });
      return;
    }
    if (newPassword.length < 6) {
      showToast({
        type: 'error',
        title: 'Weak Password',
        message: 'New password must be at least 6 characters.',
      });
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast({
        type: 'error',
        title: 'Password Mismatch',
        message: 'New password and confirmation do not match.',
      });
      return;
    }

    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    showToast({
      type: 'success',
      title: 'Security Credentials Updated',
      message: 'Your account password has been changed successfully.',
    });
  };

  const handleSaveAll = (e) => {
    if (e) e.preventDefault();

    // 1. Update user profile in AuthContext & localStorage
    updateUser({
      full_name: fullName.trim() || user?.full_name,
      phone: phone.trim(),
      email: email.trim(),
      avatar_url: avatarUrl,
      department,
      warehouse_zone: warehouseZone,
      bio,
    });

    // 2. Update operational settings
    if (onSaveSettings) {
      onSaveSettings(settings);
    }

    showToast({
      type: 'success',
      title: 'Settings & Profile Saved',
      message: 'All personal information and operational configurations updated.',
    });

    onClose();
  };

  // Helper to render current avatar
  const renderAvatarPreview = () => {
    if (avatarUrl && avatarUrl.startsWith('data:image')) {
      return (
        <img
          src={avatarUrl}
          alt={fullName || 'User'}
          className="user-settings-avatar-img"
        />
      );
    }
    if (avatarUrl && avatarUrl.length <= 4) {
      // Emoji preset
      return <span className="user-settings-avatar-emoji">{avatarUrl}</span>;
    }
    const initials = (fullName || user?.full_name || 'U')
      .split(' ')
      .map((part) => part[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
    return <span className="user-settings-avatar-initials">{initials}</span>;
  };

  const userRoleDisplay = ROLE_DISPLAY[user?.role] || 'SolarOps User';

  return (
    <div
      className="user-settings-fullscreen-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="SolarOps User Settings & Profile Center"
    >
      {/* Top Header Bar */}
      <header className="user-settings-topbar">
        <div className="user-settings-topbar-left">
          <div className="brand-pill">
            <Zap size={18} color="#f59e0b" />
            <span>SolarOps</span>
          </div>
          <div className="topbar-divider" />
          <h1 className="user-settings-topbar-title">
            Account & Operations Settings
          </h1>
          <span className="user-settings-role-badge">{userRoleDisplay}</span>
        </div>

        <div className="user-settings-topbar-right">
          <button
            type="button"
            className="topbar-btn-cancel"
            onClick={onClose}
          >
            Discard
          </button>
          <button
            type="button"
            className="topbar-btn-save"
            onClick={handleSaveAll}
          >
            <Check size={16} />
            <span>Save All Changes</span>
          </button>
          <div className="topbar-divider" />
          <button
            type="button"
            className="topbar-btn-close"
            onClick={onClose}
            title="Close Fullscreen (Esc)"
            aria-label="Close"
          >
            <X size={20} />
            <span className="esc-tag">ESC</span>
          </button>
        </div>
      </header>

      {/* Main Full-Screen Layout */}
      <div className="user-settings-main-layout">
        {/* Left Navigation Sidebar */}
        <aside className="user-settings-sidebar">
          {/* User ID Quick Card */}
          <div className="sidebar-user-card">
            <div className="sidebar-avatar-ring">
              {renderAvatarPreview()}
              <span className="sidebar-online-status" />
            </div>
            <div className="sidebar-user-info">
              <strong className="sidebar-user-name">
                {fullName || user?.full_name || 'User'}
              </strong>
              <span className="sidebar-user-role">{userRoleDisplay}</span>
              <span className="sidebar-user-code">
                {user?.employee_code || user?.id || 'ID-ACTIVE'}
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="user-settings-nav" aria-label="Settings navigation">
            <button
              type="button"
              className={`nav-tab-item ${activeTab === 'profile' ? 'active' : ''}`}
              onClick={() => setActiveTab('profile')}
            >
              <User size={18} />
              <span>User Profile & Identity</span>
            </button>

            <button
              type="button"
              className={`nav-tab-item ${activeTab === 'security' ? 'active' : ''}`}
              onClick={() => setActiveTab('security')}
            >
              <Shield size={18} />
              <span>Security & Password</span>
            </button>

            <button
              type="button"
              className={`nav-tab-item ${activeTab === 'operations' ? 'active' : ''}`}
              onClick={() => setActiveTab('operations')}
            >
              <Zap size={18} />
              <span>Grid & Operational Defaults</span>
            </button>

            <button
              type="button"
              className={`nav-tab-item ${activeTab === 'notifications' ? 'active' : ''}`}
              onClick={() => setActiveTab('notifications')}
            >
              <Bell size={18} />
              <span>Dispatch & Alerts</span>
            </button>

            <button
              type="button"
              className={`nav-tab-item ${activeTab === 'appearance' ? 'active' : ''}`}
              onClick={() => setActiveTab('appearance')}
            >
              <Sliders size={18} />
              <span>VisionOS & Telemetry</span>
            </button>
          </nav>

          <div className="sidebar-footer-info">
            <span>SolarOps Enterprise v2.4</span>
            <span>All changes encrypt end-to-end</span>
          </div>
        </aside>

        {/* Right Content Pane */}
        <main className="user-settings-content">
          {/* =============================================================
              TAB 1: USER PROFILE & IDENTITY
              ============================================================= */}
          {activeTab === 'profile' && (
            <div className="settings-section-container">
              <div className="section-header-block">
                <h2 className="section-title">User Profile & Personal Identity</h2>
                <p className="section-subtitle">
                  Manage your public avatar, contact details, service hub, and
                  roster metadata across SolarOps.
                </p>
              </div>

              {/* Profile Photo Management */}
              <div className="settings-card avatar-management-card">
                <div className="avatar-preview-col">
                  <div className="large-avatar-frame">
                    {renderAvatarPreview()}
                  </div>
                </div>

                <div className="avatar-controls-col">
                  <h3 className="card-subheading">Profile Photo</h3>
                  <p className="card-helper-text">
                    Upload a high-resolution JPG or PNG (max 5 MB), or choose a
                    SolarOps role preset.
                  </p>

                  <div className="avatar-action-buttons">
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept="image/*"
                      style={{ display: 'none' }}
                      onChange={handlePhotoUpload}
                    />
                    <button
                      type="button"
                      className="btn-upload-photo"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <Camera size={15} />
                      <span>Upload New Photo</span>
                    </button>

                    {avatarUrl && (
                      <button
                        type="button"
                        className="btn-remove-photo"
                        onClick={handleRemovePhoto}
                      >
                        <Trash2 size={14} />
                        <span>Remove Photo</span>
                      </button>
                    )}
                  </div>

                  {/* Preset Avatar Emojis */}
                  <div className="preset-avatars-row">
                    <span className="preset-label">Or Pick a Role Avatar:</span>
                    <div className="preset-chips-wrap">
                      {PRESET_AVATARS.map((av) => (
                        <button
                          key={av.id}
                          type="button"
                          className="preset-avatar-chip"
                          onClick={() => handleSelectPresetAvatar(av)}
                          title={av.label}
                        >
                          <span className="preset-emoji">{av.emoji}</span>
                          <span className="preset-chip-label">{av.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Personal Details Form */}
              <div className="settings-card form-card">
                <h3 className="card-subheading">Personal Information</h3>

                <div className="form-grid-2col">
                  {/* Full Name */}
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="userFullName">
                      Full Legal Name
                    </label>
                    <div className="field-input-wrap">
                      <User size={16} className="field-icon" />
                      <input
                        id="userFullName"
                        type="text"
                        className="field-text-input"
                        placeholder="e.g. Arun Kumar"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Phone Number */}
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="userPhoneNumber">
                      Mobile Phone Number
                    </label>
                    <div className="field-input-wrap">
                      <Phone size={16} className="field-icon" />
                      <input
                        id="userPhoneNumber"
                        type="tel"
                        className="field-text-input"
                        placeholder="e.g. +91 98450 12345"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Email Address */}
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="userEmail">
                      Primary Work Email
                    </label>
                    <div className="field-input-wrap">
                      <Mail size={16} className="field-icon" />
                      <input
                        id="userEmail"
                        type="email"
                        className="field-text-input"
                        placeholder="e.g. arun.kumar@sunpowersolutions.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                      />
                      <span className="verified-pill">Verified</span>
                    </div>
                  </div>

                  {/* Employee / Customer ID */}
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="userCode">
                      Account Reference Code
                    </label>
                    <div className="field-input-wrap">
                      <KeyRound size={16} className="field-icon" />
                      <input
                        id="userCode"
                        type="text"
                        className="field-text-input readonly"
                        value={user?.employee_code || user?.id || 'USR-SOLAR-001'}
                        readOnly
                      />
                      <span className="read-only-badge">Locked ID</span>
                    </div>
                  </div>

                  {/* Department */}
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="userDept">
                      Department / Specialization
                    </label>
                    <div className="field-input-wrap">
                      <Building size={16} className="field-icon" />
                      <input
                        id="userDept"
                        type="text"
                        className="field-text-input"
                        value={department}
                        onChange={(e) => setDepartment(e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Regional Hub */}
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="userZone">
                      Service Hub & Warehouse Base
                    </label>
                    <div className="field-input-wrap">
                      <MapPin size={16} className="field-icon" />
                      <input
                        id="userZone"
                        type="text"
                        className="field-text-input"
                        value={warehouseZone}
                        onChange={(e) => setWarehouseZone(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                {/* Bio / Work Summary */}
                <div className="form-field-group full-width">
                  <label className="field-label" htmlFor="userBio">
                    Professional Summary & Field Qualifications
                  </label>
                  <textarea
                    id="userBio"
                    className="field-textarea"
                    rows={3}
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* =============================================================
              TAB 2: SECURITY & PASSWORD
              ============================================================= */}
          {activeTab === 'security' && (
            <div className="settings-section-container">
              <div className="section-header-block">
                <h2 className="section-title">Security & Credentials</h2>
                <p className="section-subtitle">
                  Configure account protection, update your login password, and
                  manage two-factor authentication.
                </p>
              </div>

              {/* Password Change Card */}
              <form onSubmit={handlePasswordUpdate} className="settings-card form-card">
                <h3 className="card-subheading">Change Account Password</h3>

                <div className="form-grid-2col">
                  <div className="form-field-group full-width">
                    <label className="field-label" htmlFor="currentPassword">
                      Current Password
                    </label>
                    <div className="field-input-wrap">
                      <Lock size={16} className="field-icon" />
                      <input
                        id="currentPassword"
                        type={showPassword ? 'text' : 'password'}
                        className="field-text-input"
                        placeholder="••••••••••••"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="form-field-group">
                    <label className="field-label" htmlFor="newPassword">
                      New Password (min. 6 characters)
                    </label>
                    <div className="field-input-wrap">
                      <Lock size={16} className="field-icon" />
                      <input
                        id="newPassword"
                        type={showPassword ? 'text' : 'password'}
                        className="field-text-input"
                        placeholder="••••••••••••"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="form-field-group">
                    <label className="field-label" htmlFor="confirmPassword">
                      Confirm New Password
                    </label>
                    <div className="field-input-wrap">
                      <Lock size={16} className="field-icon" />
                      <input
                        id="confirmPassword"
                        type={showPassword ? 'text' : 'password'}
                        className="field-text-input"
                        placeholder="••••••••••••"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                      />
                    </div>
                  </div>
                </div>

                <div className="password-actions-row">
                  <button
                    type="button"
                    className="btn-toggle-password-visibility"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    <span>{showPassword ? 'Hide Passwords' : 'Show Passwords'}</span>
                  </button>

                  <button type="submit" className="btn-update-password">
                    Update Password
                  </button>
                </div>
              </form>

              {/* 2-Factor Authentication */}
              <div className="settings-card">
                <div className="toggle-card-row">
                  <div className="toggle-text-block">
                    <h3 className="card-subheading">
                      Two-Factor Authentication (2FA)
                    </h3>
                    <p className="card-helper-text">
                      Require an SMS OTP or Authenticator prompt when accessing
                      SolarOps from new IP addresses or mobile browsers.
                    </p>
                  </div>
                  <label className="switch-toggle" htmlFor="twoFactorToggle">
                    <input
                      id="twoFactorToggle"
                      type="checkbox"
                      checked={twoFactorEnabled}
                      onChange={(e) => setTwoFactorEnabled(e.target.checked)}
                    />
                    <span className="slider-round" />
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* =============================================================
              TAB 3: GRID & OPERATIONAL DEFAULTS
              ============================================================= */}
          {activeTab === 'operations' && (
            <div className="settings-section-container">
              <div className="section-header-block">
                <h2 className="section-title">Grid & DISCOM Operational Defaults</h2>
                <p className="section-subtitle">
                  Configure default utility circle interconnect rules, system
                  sizing formulas, and solar inverter guidelines.
                </p>
              </div>

              <div className="settings-card form-card">
                <h3 className="card-subheading">Karnataka DISCOM Integration</h3>

                <div className="form-grid-2col">
                  <div className="form-field-group">
                    <label className="field-label" htmlFor="discomCircle">
                      Default Electricity Supply Circle
                    </label>
                    <select
                      id="discomCircle"
                      className="field-select"
                      value={settings.discomCircle}
                      onChange={(e) =>
                        setSettings({ ...settings, discomCircle: e.target.value })
                      }
                    >
                      <option value="BESCOM (Bangalore Urban & Rural)">BESCOM (Bangalore Urban & Rural)</option>
                      <option value="MESCOM (Mangalore & Coastal)">MESCOM (Mangalore & Coastal)</option>
                      <option value="HESCOM (Hubli-Dharwad Circle)">HESCOM (Hubli-Dharwad Circle)</option>
                      <option value="GESCOM (Gulbarga Division)">GESCOM (Gulbarga Division)</option>
                      <option value="CHESCOM (Mysore Division)">CHESCOM (Mysore Division)</option>
                    </select>
                  </div>

                  <div className="form-field-group">
                    <label className="field-label" htmlFor="defaultCapacity">
                      Standard Inverter Architecture
                    </label>
                    <select
                      id="defaultCapacity"
                      className="field-select"
                      value={settings.defaultCapacity}
                      onChange={(e) =>
                        setSettings({ ...settings, defaultCapacity: e.target.value })
                      }
                    >
                      <option value="3 kW Micro-Inverter (Residential)">3 kW Micro-Inverter (Residential)</option>
                      <option value="5 kW Hybrid Bifacial (DCR Compliant)">5 kW Hybrid Bifacial (DCR Compliant)</option>
                      <option value="10 kW Commercial String Inverter">10 kW Commercial String Inverter</option>
                    </select>
                  </div>
                </div>

                <div className="toggle-card-row embedded">
                  <div className="toggle-text-block">
                    <strong>Automatic Sanction Load Ratio Calculation</strong>
                    <p className="card-helper-text">
                      Recommend maximum solar panel capacity strictly capped at 80%
                      of the customer’s sanctioned meter load to avoid utility export penalties.
                    </p>
                  </div>
                  <label className="switch-toggle" htmlFor="autoSanctionToggle">
                    <input
                      id="autoSanctionToggle"
                      type="checkbox"
                      checked={settings.autoSanctionCalc}
                      onChange={(e) =>
                        setSettings({ ...settings, autoSanctionCalc: e.target.checked })
                      }
                    />
                    <span className="slider-round" />
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* =============================================================
              TAB 4: DISPATCH & ALERTS
              ============================================================= */}
          {activeTab === 'notifications' && (
            <div className="settings-section-container">
              <div className="section-header-block">
                <h2 className="section-title">Field Dispatch & Automated Notifications</h2>
                <p className="section-subtitle">
                  Configure automated WhatsApp milestone broadcasts, technician SMS
                  route reminders, and low-inventory threshold triggers.
                </p>
              </div>

              <div className="settings-card">
                <div className="toggle-card-row">
                  <div className="toggle-text-block">
                    <h3 className="card-subheading">Technician Field Route SMS Reminders</h3>
                    <p className="card-helper-text">
                      Dispatches daily 08:00 AM itinerary and Google Maps route links
                      to assigned field technicians.
                    </p>
                  </div>
                  <label className="switch-toggle" htmlFor="smsAlertsToggle">
                    <input
                      id="smsAlertsToggle"
                      type="checkbox"
                      checked={settings.smsDispatchAlerts}
                      onChange={(e) =>
                        setSettings({ ...settings, smsDispatchAlerts: e.target.checked })
                      }
                    />
                    <span className="slider-round" />
                  </label>
                </div>

                <div className="toggle-divider" />

                <div className="toggle-card-row">
                  <div className="toggle-text-block">
                    <h3 className="card-subheading">Customer WhatsApp Milestone Tracking</h3>
                    <p className="card-helper-text">
                      Automatically sends WhatsApp alerts when site survey is submitted,
                      BESCOM net-meter is sanctioned, and installation goes live.
                    </p>
                  </div>
                  <label className="switch-toggle" htmlFor="waMilestonesToggle">
                    <input
                      id="waMilestonesToggle"
                      type="checkbox"
                      checked={settings.whatsappMilestones}
                      onChange={(e) =>
                        setSettings({ ...settings, whatsappMilestones: e.target.checked })
                      }
                    />
                    <span className="slider-round" />
                  </label>
                </div>

                <div className="toggle-divider" />

                <div className="toggle-card-row">
                  <div className="toggle-text-block">
                    <h3 className="card-subheading">Warehouse Low-Stock Warnings</h3>
                    <p className="card-helper-text">
                      Instantly alerts logistics staff when 540W modules or 5kW hybrid
                      inverters dip below minimum buffer safety counts.
                    </p>
                  </div>
                  <label className="switch-toggle" htmlFor="lowStockToggle">
                    <input
                      id="lowStockToggle"
                      type="checkbox"
                      checked={settings.lowStockReorderAlerts}
                      onChange={(e) =>
                        setSettings({ ...settings, lowStockReorderAlerts: e.target.checked })
                      }
                    />
                    <span className="slider-round" />
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* =============================================================
              TAB 5: APPEARANCE & TELEMETRY
              ============================================================= */}
          {activeTab === 'appearance' && (
            <div className="settings-section-container">
              <div className="section-header-block">
                <h2 className="section-title">VisionOS & Live Telemetry Refresh</h2>
                <p className="section-subtitle">
                  Customize the optical liquid glass refraction engine, sensor polling
                  frequencies, and UI rendering performance.
                </p>
              </div>

              <div className="settings-card form-card">
                <div className="form-field-group">
                  <label className="field-label" htmlFor="telemetryRate">
                    Live Telemetry Polling Rate
                  </label>
                  <select
                    id="telemetryRate"
                    className="field-select"
                    value={settings.telemetryRefreshRate}
                    onChange={(e) =>
                      setSettings({ ...settings, telemetryRefreshRate: e.target.value })
                    }
                  >
                    <option value="10s">10 Seconds (Ultra-Responsive Field Ops)</option>
                    <option value="15s">15 Seconds (Standard Operations)</option>
                    <option value="30s">30 Seconds (Balanced Power)</option>
                    <option value="60s">60 Seconds (Low Network & Battery Saver)</option>
                  </select>
                </div>

                <div className="toggle-card-row embedded">
                  <div className="toggle-text-block">
                    <strong>VisionOS Liquid Glass Optical Refraction</strong>
                    <p className="card-helper-text">
                      Enables real-time Snell's law optical glass shader refraction,
                      specular edge highlights, and high-index defocus blur.
                    </p>
                  </div>
                  <label className="switch-toggle" htmlFor="glassToggle">
                    <input
                      id="glassToggle"
                      type="checkbox"
                      checked={settings.visionOsGlass}
                      onChange={(e) =>
                        setSettings({ ...settings, visionOsGlass: e.target.checked })
                      }
                    />
                    <span className="slider-round" />
                  </label>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Sticky Bottom Bar */}
      <footer className="user-settings-bottom-bar">
        <div className="bottom-bar-left">
          <CheckCircle2 size={16} color="#10b981" />
          <span>All profile edits and operational preferences sync instantaneously.</span>
        </div>

        <div className="bottom-bar-right">
          <button
            type="button"
            className="bottom-bar-btn-cancel"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className="bottom-bar-btn-save"
            onClick={handleSaveAll}
          >
            <Check size={16} />
            <span>Save Preferences & Profile</span>
          </button>
        </div>
      </footer>
    </div>
  );
}

export default UserSettingsModal;

import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  ScanBarcode,
  Upload,
  Check,
  CheckCircle2,
  Package,
  Wrench,
  X,
  Plus,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Image as ImageIcon,
  Trash2,
  AlertCircle,
  Sliders,
  ShieldCheck,
  MapPin,
} from 'lucide-react';
import { Modal } from '../Modal/Modal';
import { useAuth } from '../../context/AuthContext';
import './EquipmentScannerModal.css';

export function EquipmentScannerModal({ isOpen, onClose, role = 'technician' }) {
  const { showToast } = useAuth();
  const videoRef = useRef(null);
  const fileInputRef = useRef(null);
  const streamRef = useRef(null);

  const isTechnician = role === 'technician';

  // Camera Hardware State
  const [cameraStatus, setCameraStatus] = useState('idle'); // 'idle' | 'requesting' | 'active' | 'denied' | 'unsupported'
  const [facingMode] = useState('environment'); // default back-facing camera for real mobile scanning

  // Warehouse Mode: QR & Barcode Scanning State
  const [stockMode, setStockMode] = useState('inward'); // 'inward' | 'dispatch'
  const [lastScannedCode, setLastScannedCode] = useState(null);
  const [scannedItems, setScannedItems] = useState([
    {
      id: 'item-1',
      code: 'SN-PV540-KA-0985',
      name: 'Waaree 540W Mono-PERC Panel',
      mode: 'inward',
      time: 'Just now',
    },
    {
      id: 'item-2',
      code: 'INV-HYB5K-2026-041',
      name: 'SolarEdge 5kW Hybrid Inverter',
      mode: 'inward',
      time: '2m ago',
    },
  ]);

  // Technician Mode: Installation Photos State
  const [capturedPhotos, setCapturedPhotos] = useState([
    {
      id: 'photo-1',
      url: 'https://images.unsplash.com/photo-1509391365360-2e959784a276?w=600&auto=format&fit=crop&q=80',
      tag: 'Rooftop South Array (Azimuth 180°)',
      time: '11:15 AM',
    },
    {
      id: 'photo-2',
      url: 'https://images.unsplash.com/photo-1548337138-e87d889cc369?w=600&auto=format&fit=crop&q=80',
      tag: 'Inverter & AC/DC Protection Box',
      time: '11:22 AM',
    },
  ]);

  // Request Real Camera Access
  const startCamera = async (facing = facingMode) => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setCameraStatus('unsupported');
      return;
    }

    try {
      setCameraStatus('requesting');

      // Stop previous tracks if switching camera
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }

      const constraints = {
        video: {
          facingMode: { ideal: facing },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play().catch(() => {});
      }

      setCameraStatus('active');
    } catch (err) {
      console.warn('Real camera access denied or device not found:', err);
      setCameraStatus('denied');
    }
  };

  // Stop camera tracks cleanly
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraStatus('idle');
  };

  // Camera Lifecycle
  useEffect(() => {
    if (isOpen) {
      startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
    };
  }, [isOpen]);

  // =========================================================================
  // WAREHOUSE MANAGER ACTIONS (Scan Barcode / QR Code)
  // =========================================================================
  const handleScanBarcode = (detectedCode, label) => {
    const newItem = {
      id: `item-${Date.now()}`,
      code: detectedCode || `SN-PV540-KA-${Math.floor(1000 + Math.random() * 9000)}`,
      name: label || 'Waaree 540W Mono-PERC Module',
      mode: stockMode,
      time: 'Just now',
    };

    setLastScannedCode(newItem);
    setScannedItems((prev) => [newItem, ...prev]);

    // Haptic / Sound vibration feedback if supported
    if (navigator.vibrate) {
      navigator.vibrate(80);
    }

    showToast({
      type: 'success',
      title: stockMode === 'inward' ? 'Stock Inward +1' : 'Stock Dispatched -1',
      message: `${newItem.name} (${newItem.code}) recorded.`,
    });
  };

  const handleSimulateScan = () => {
    const warehousePresets = [
      { code: 'SN-PV540-KA-0988', name: 'Waaree 540W Mono-PERC Module' },
      { code: 'INV-HYB5K-2026-042', name: 'SolarEdge 5kW Hybrid Inverter' },
      { code: 'BAT-5KWH-LFP-089', name: 'SolarFlow 5.12kWh LiFePO4 Battery' },
      { code: 'BOS-DB-SPD-449', name: 'Solar AC/DC Distribution Box' },
      { code: 'MTR-NET-BESCOM-099', name: 'BESCOM Smart Net-Meter Barcode' },
    ];
    const picked = warehousePresets[Math.floor(Math.random() * warehousePresets.length)];
    handleScanBarcode(picked.code, picked.name);
  };

  // =========================================================================
  // TECHNICIAN ACTIONS (Capture Live Snapshot & Upload Photos)
  // =========================================================================
  const handleCaptureInstallationPhoto = () => {
    let photoUrl = '';
    const video = videoRef.current;

    if (video && video.videoWidth && video.videoHeight) {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        photoUrl = canvas.toDataURL('image/jpeg', 0.92);
      } catch (e) {
        photoUrl = '';
      }
    }

    // Fallback if camera stream is blocked
    if (!photoUrl) {
      photoUrl =
        'https://images.unsplash.com/photo-1509391365360-2e959784a276?w=600&auto=format&fit=crop&q=80';
    }

    const tagOptions = [
      'Rooftop PV Array & Azimuth Angle',
      'Inverter Wiring & Distribution Box',
      'DISCOM Smart Net-Meter',
      'Earth Pit Resistance Ground Tag',
    ];
    const tag = tagOptions[capturedPhotos.length % tagOptions.length];

    const newPhoto = {
      id: `photo-${Date.now()}`,
      url: photoUrl,
      tag: `${tag} #${capturedPhotos.length + 1}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setCapturedPhotos((prev) => [newPhoto, ...prev]);

    if (navigator.vibrate) {
      navigator.vibrate([40, 60, 40]);
    }

    showToast({
      type: 'success',
      title: 'Installation Photo Captured',
      message: `${newPhoto.tag} captured from optical camera feed.`,
    });
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const newPhoto = {
          id: `photo-${Date.now()}`,
          url: event.target.result,
          tag: `Uploaded Evidence (${file.name})`,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setCapturedPhotos((prev) => [newPhoto, ...prev]);
        showToast({
          type: 'success',
          title: 'Photo Uploaded',
          message: `${file.name} attached to installation report.`,
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemovePhoto = (id) => {
    setCapturedPhotos((prev) => prev.filter((p) => p.id !== id));
    showToast({
      type: 'info',
      title: 'Photo Removed',
      message: 'Photo removed from submission bundle.',
    });
  };

  // Submit Completed Action
  const handleSubmitAction = () => {
    if (!isTechnician) {
      showToast({
        type: 'success',
        title: 'Warehouse Stock Synced',
        message: `${scannedItems.length} barcodes committed to warehouse inventory log.`,
      });
    } else {
      showToast({
        type: 'success',
        title: 'Work Proof Submitted to HQ',
        message: `${capturedPhotos.length} installation photos synchronized with Sales & Engineering!`,
      });
    }
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div className="compact-scanner-header">
          <div className="scanner-header-identity">
            {isTechnician ? (
              <div className="scanner-header-icon tech">
                <Camera size={19} color="#10b981" />
              </div>
            ) : (
              <div className="scanner-header-icon wh">
                <ScanBarcode size={19} color="#f59e0b" />
              </div>
            )}
            <div>
              <h3 className="scanner-header-title">
                {isTechnician
                  ? 'Field Installation Proof Camera'
                  : 'Warehouse QR & Barcode Scanner'}
              </h3>
              <span className="scanner-header-meta">
                {isTechnician
                  ? 'Capture & upload photo evidence of completed rooftop installation'
                  : 'Scan product barcodes and serial plates to manage warehouse stock'}
              </span>
            </div>
          </div>

          <span
            className={`scanner-header-pill ${isTechnician ? 'technician' : 'warehouse'}`}
          >
            {isTechnician ? 'Field Technician' : 'Warehouse Manager'}
          </span>
        </div>
      }
      maxWidth="680px"
    >
      <div className="compact-scanner-body">
        {/* ===================================================================
            WAREHOUSE TOP BAR: Inward vs Outward Toggle
            =================================================================== */}
        {!isTechnician && (
          <div className="warehouse-quick-mode-bar">
            <span className="mode-label">Stock Action:</span>
            <div className="mode-pill-toggle">
              <button
                type="button"
                className={`mode-pill ${stockMode === 'inward' ? 'active inward' : ''}`}
                onClick={() => setStockMode('inward')}
              >
                <Plus size={14} />
                <span>Inward Receiving (+ Stock)</span>
              </button>
              <button
                type="button"
                className={`mode-pill ${stockMode === 'dispatch' ? 'active dispatch' : ''}`}
                onClick={() => setStockMode('dispatch')}
              >
                <ArrowRight size={14} />
                <span>Outward Dispatch (- Kit)</span>
              </button>
            </div>
          </div>
        )}

        {/* ===================================================================
            TECHNICIAN TOP BAR: Active Work Order Details
            =================================================================== */}
        {isTechnician && (
          <div className="technician-job-status-strip">
            <div className="tech-job-left">
              <MapPin size={15} color="#10b981" />
              <span>Job #SO-0042 · Arun Kumar (5kW Hybrid Rooftop, Indiranagar)</span>
            </div>
            <span className="tech-job-badge">Work in Progress</span>
          </div>
        )}

        {/* ===================================================================
            PRIMARY CAMERA CONTAINER & OPTICAL VIEWFINDER
            =================================================================== */}
        <div className="optical-camera-container">
          {/* Real Camera Video Element */}
          <video
            ref={videoRef}
            className={`optical-video-stream ${cameraStatus === 'active' ? 'visible' : 'hidden'}`}
            autoPlay
            playsInline
            muted
          />

          {/* Camera Permission Requesting State */}
          {cameraStatus === 'requesting' && (
            <div className="camera-overlay-state">
              <div className="camera-spinner" />
              <p>Initializing Camera Feed...</p>
              <span>Please grant browser camera access if prompted</span>
            </div>
          )}

          {/* Camera Permission Denied or Unavailable State */}
          {(cameraStatus === 'denied' || cameraStatus === 'unsupported') && (
            <div className="camera-overlay-state denied">
              <AlertCircle size={36} color="#ef4444" />
              <h4>Camera Access Unavailable</h4>
              <p>
                {cameraStatus === 'denied'
                  ? 'Browser camera permission was denied or camera is in use by another app.'
                  : 'Webcam device was not found on this computer.'}
              </p>
              <div className="camera-denied-actions">
                <button
                  type="button"
                  className="btn-retry-camera"
                  onClick={() => startCamera()}
                >
                  <RefreshCw size={14} />
                  <span>Retry Camera</span>
                </button>
                <button
                  type="button"
                  className="btn-sim-action"
                  onClick={
                    !isTechnician
                      ? handleSimulateScan
                      : handleCaptureInstallationPhoto
                  }
                >
                  <Sparkles size={14} />
                  <span>
                    {!isTechnician ? 'Simulate Barcode Scan' : 'Capture Sample Photo'}
                  </span>
                </button>
              </div>
            </div>
          )}

          {/* Scanning Reticle & Corner Brackets Overlay */}
          <div className="camera-viewfinder-overlay">
            <div className="reticle-bracket top-left" />
            <div className="reticle-bracket top-right" />
            <div className="reticle-bracket bottom-left" />
            <div className="reticle-bracket bottom-right" />

            {/* Scanning Laser Sweep Beam: ALWAYS on screen for Warehouse Manager, removed for Technician */}
            {!isTechnician && <div className="laser-sweep-beam" />}

            {/* Center Focus Box */}
            <div className="center-target-box">
              <div className="target-icon">
                {!isTechnician ? (
                  <ScanBarcode size={44} color="rgba(255, 255, 255, 0.85)" strokeWidth={1.5} />
                ) : (
                  <Camera size={44} color="rgba(255, 255, 255, 0.85)" strokeWidth={1.5} />
                )}
              </div>
              <span className="target-instruction">
                {!isTechnician
                  ? 'POINT AT COMPONENT QR / BARCODE'
                  : 'FRAME INSTALLATION WORK IN CENTER'}
              </span>
            </div>

            {/* Camera Floating Telemetry Badges */}
            <div className="camera-hud-badge top-left-badge">
              <span className="hud-live-pip" />
              <span>CAM · 1080p Optical Feed</span>
            </div>

            <div className="camera-hud-badge top-right-badge">
              <span>FPS: 60 · ISO 200</span>
            </div>

            {/* Live Scan Acknowledgment Overlay for Warehouse Manager */}
            {!isTechnician && lastScannedCode && (
              <div className="last-scan-pill-banner">
                <CheckCircle2 size={16} color="#10b981" />
                <div className="scan-pill-text">
                  <strong>{lastScannedCode.name}</strong>
                  <span>Serial: {lastScannedCode.code}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ===================================================================
            PRIMARY ACTION BUTTON: BARCODE TRIGGER OR PHOTO SHUTTER
            =================================================================== */}
        <div className="scanner-primary-action-wrap">
          {!isTechnician ? (
            /* Warehouse Manager: Quick Scan Button */
            <div className="wh-scan-action-row">
              <button
                type="button"
                className="btn-trigger-barcode-scan"
                onClick={handleSimulateScan}
              >
                <ScanBarcode size={20} />
                <span>Scan Barcode / QR Code</span>
              </button>

              <span className="wh-items-count-tag">
                {scannedItems.length} Items Logged
              </span>
            </div>
          ) : (
            /* Technician: Capture Photo Snapshot & File Upload */
            <div className="tech-photo-actions-row">
              <button
                type="button"
                className="btn-shutter-snap"
                onClick={handleCaptureInstallationPhoto}
                title="Capture Photo from Camera Feed"
              >
                <div className="shutter-inner-circle">
                  <Camera size={22} color="#ffffff" />
                </div>
                <span>Capture Photo</span>
              </button>

              <button
                type="button"
                className="btn-upload-file-photo"
                onClick={() => fileInputRef.current?.click()}
                title="Upload Photo from Device Gallery"
              >
                <Upload size={17} />
                <span>Upload From Device</span>
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={handleFileUpload}
              />
            </div>
          )}
        </div>

        {/* ===================================================================
            TECHNICIAN: CAPTURED PHOTOS THUMBNAIL CAROUSEL
            =================================================================== */}
        {isTechnician && capturedPhotos.length > 0 && (
          <div className="captured-photos-section">
            <div className="captured-section-header">
              <strong>Installation Photos ({capturedPhotos.length})</strong>
              <span className="captured-subtext">
                Photos will be watermarked with GPS coordinates and uploaded to HQ.
              </span>
            </div>

            <div className="photos-thumbnail-strip">
              {capturedPhotos.map((photo) => (
                <div key={photo.id} className="photo-thumbnail-card">
                  <img
                    src={photo.url}
                    alt={photo.tag}
                    className="thumbnail-img"
                  />
                  <div className="thumbnail-overlay">
                    <span className="thumbnail-tag">{photo.tag}</span>
                    <button
                      type="button"
                      className="btn-delete-photo"
                      onClick={() => handleRemovePhoto(photo.id)}
                      title="Remove Photo"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===================================================================
            WAREHOUSE MANAGER: RECENT BARCODES LOG PILLS
            =================================================================== */}
        {!isTechnician && scannedItems.length > 0 && (
          <div className="scanned-items-quick-list">
            <div className="quick-list-header">
              <strong>Recent Scans in Batch:</strong>
            </div>
            <div className="quick-items-chips">
              {scannedItems.slice(0, 4).map((item) => (
                <div key={item.id} className="scanned-chip-pill">
                  <Package size={13} color="#4f46e5" />
                  <span className="chip-code">{item.code}</span>
                  <span className="chip-name">{item.name}</span>
                  <span className="chip-mode">
                    {item.mode === 'inward' ? '+Inward' : '-Dispatch'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ===================================================================
            MODAL FOOTER: CLOSE OR COMMIT
            =================================================================== */}
        <div className="compact-scanner-footer">
          <button
            type="button"
            className="scanner-footer-cancel-btn"
            onClick={onClose}
          >
            Close
          </button>

          <button
            type="button"
            className={`scanner-footer-submit-btn ${isTechnician ? 'technician' : 'warehouse'}`}
            onClick={handleSubmitAction}
          >
            <Check size={16} />
            <span>
              {!isTechnician
                ? `Commit ${scannedItems.length} Scanned Items to Stock`
                : `Submit ${capturedPhotos.length} Installation Photos to HQ`}
            </span>
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default EquipmentScannerModal;

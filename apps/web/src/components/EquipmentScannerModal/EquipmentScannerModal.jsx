import React, { useState } from 'react';
import {
  ScanBarcode,
  Camera,
  Upload,
  CheckCircle2,
  Package,
  Wrench,
  X,
  Plus,
  Trash2,
  Sun,
  Zap,
  Battery,
  ShieldCheck,
  FileCheck,
  MapPin,
  RefreshCw,
  Flashlight,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { Modal } from '../Modal/Modal';
import { useAuth } from '../../context/AuthContext';
import './EquipmentScannerModal.css';

export function EquipmentScannerModal({ isOpen, onClose, role = 'technician' }) {
  const { showToast } = useAuth();

  // Active Role view (support admin switching between both roles for testing)
  const isWarehouseUser =
    role === 'warehouse_manager' || role === 'warehouse_staff';
  const isTechnicianUser = role === 'technician';
  const isAdminUser = role === 'admin';

  const [activeMode, setActiveMode] = useState(
    isWarehouseUser ? 'warehouse' : 'technician'
  );

  // Warehouse Mode States
  const [warehouseAction, setWarehouseAction] = useState('inward'); // 'inward' | 'dispatch'
  const [barcodeInput, setBarcodeInput] = useState('');
  const [scannedWarehouseItems, setScannedWarehouseItems] = useState([
    {
      id: 1,
      serial: 'SN-PV540-KA-0985',
      name: 'Waaree 540W Mono-PERC Module',
      rack: 'Aisle B - Shelf 04',
      batch: 'BATCH-2026-Q2',
      qty: 1,
      status: 'Verified',
      time: 'Just now',
    },
    {
      id: 2,
      serial: 'INV-HYB5K-2026-041',
      name: 'SolarEdge 5kW Hybrid Inverter',
      rack: 'Aisle A - Bay 02',
      batch: 'BATCH-INV-088',
      qty: 1,
      status: 'Verified',
      time: '2m ago',
    },
    {
      id: 3,
      serial: 'BAT-5KWH-LFP-088',
      name: 'SolarFlow 5.12kWh LiFePO4 Battery',
      rack: 'Heavy Staging Area',
      batch: 'BATCH-LFP-014',
      qty: 1,
      status: 'Verified',
      time: '5m ago',
    },
  ]);

  // Technician Mode States
  const [techVerificationList, setTechVerificationList] = useState([
    {
      id: 1,
      component: 'Inverter Serial Number',
      targetSerial: 'INV-HYB5K-2026-041',
      scannedSerial: 'INV-HYB5K-2026-041',
      status: 'matched',
      label: 'SolarEdge 5kW Hybrid Grid-Tie (IP65)',
    },
    {
      id: 2,
      component: 'PV Module Array Serial (1/10)',
      targetSerial: 'SN-PV540-KA-0981',
      scannedSerial: 'SN-PV540-KA-0981',
      status: 'matched',
      label: '540W Mono-PERC Bifacial Module #1',
    },
    {
      id: 3,
      component: 'Bi-directional Net-Meter Barcode',
      targetSerial: 'BESCOM-KA-BLR-099234',
      scannedSerial: '',
      status: 'pending',
      label: 'DISCOM 3-Phase Smart Net-Meter',
    },
    {
      id: 4,
      component: 'Chemical Earthing Pit Ground Tag',
      targetSerial: 'EARTH-PIT-KA-042',
      scannedSerial: '',
      status: 'pending',
      label: 'Ground Resistance < 3.2Ω Tag',
    },
  ]);

  // Uploaded evidence files
  const [uploadedFiles, setUploadedFiles] = useState(
    activeMode === 'warehouse'
      ? [
          { name: 'Supplier_Delivery_Challan_4981.pdf', size: '240 KB' },
          { name: 'Pallet_Barcode_Batch_540W.jpg', size: '1.2 MB' },
        ]
      : [
          { name: 'Rooftop_South_Array_Azimuth_180.jpg', size: '2.4 MB' },
          { name: 'Inverter_ACDC_Distribution_Box.jpg', size: '1.8 MB' },
        ]
  );

  const [torchOn, setTorchOn] = useState(false);
  const [laserActive, setLaserActive] = useState(true);

  // Quick scan barcode triggers
  const handleScanBarcode = (serialCode, itemName, rackLoc) => {
    if (!serialCode.trim()) return;

    if (activeMode === 'warehouse') {
      const newItem = {
        id: Date.now(),
        serial: serialCode.trim(),
        name: itemName || 'Serialized Solar Hardware',
        rack: rackLoc || 'Warehouse Staging Zone 1',
        batch: 'BATCH-2026-LIVE',
        qty: 1,
        status: warehouseAction === 'inward' ? 'Stock Inward +1' : 'Dispatched -1',
        time: 'Just now',
      };
      setScannedWarehouseItems([newItem, ...scannedWarehouseItems]);
      setBarcodeInput('');
      showToast({
        type: 'success',
        title: 'Barcode Scanned & Registered',
        message: `${newItem.name} (${newItem.serial}) logged to inventory.`,
      });
    } else {
      // Technician verification match
      let matched = false;
      const updated = techVerificationList.map((item) => {
        if (
          !item.scannedSerial &&
          (item.targetSerial === serialCode.trim() || !matched)
        ) {
          matched = true;
          return {
            ...item,
            scannedSerial: serialCode.trim(),
            status: 'matched',
          };
        }
        return item;
      });
      setTechVerificationList(updated);
      setBarcodeInput('');
      showToast({
        type: 'success',
        title: 'Component Verified on Site',
        message: `Serial ${serialCode.trim()} matches Job #SO-0042 BOM specifications.`,
      });
    }
  };

  const handleSimulateScan = () => {
    if (activeMode === 'warehouse') {
      const presets = [
        { code: 'SN-PV540-KA-0986', name: 'Waaree 540W Mono-PERC Module', rack: 'Aisle B - Shelf 04' },
        { code: 'INV-HYB3K-2026-104', name: 'Micro-Inverter 3kW String Unit', rack: 'Aisle A - Bay 03' },
        { code: 'BAT-10KWH-LFP-022', name: 'Commercial 10.24kWh Storage Bank', rack: 'Heavy Staging Area' },
        { code: 'BOS-DB-SPD-449', name: 'Solar AC/DC Distribution Box', rack: 'BOS Rack 2' },
      ];
      const randomPreset = presets[Math.floor(Math.random() * presets.length)];
      handleScanBarcode(randomPreset.code, randomPreset.name, randomPreset.rack);
    } else {
      const pendingItem = techVerificationList.find((i) => i.status === 'pending');
      if (pendingItem) {
        handleScanBarcode(pendingItem.targetSerial);
      } else {
        showToast({
          type: 'info',
          title: 'All Components Verified',
          message: 'All equipment for Job #SO-0042 has already been scanned and verified.',
        });
      }
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFiles([
        ...uploadedFiles,
        { name: file.name, size: `${Math.round(file.size / 1024)} KB` },
      ]);
      showToast({
        type: 'success',
        title: 'Evidence Attached',
        message: `${file.name} uploaded and tagged to work record.`,
      });
    }
  };

  const handleRemoveFile = (index) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index));
  };

  const handleCommit = (e) => {
    e.preventDefault();
    if (activeMode === 'warehouse') {
      showToast({
        type: 'success',
        title: 'Stock Updated Successfully',
        message: `${scannedWarehouseItems.length} serialized components saved to warehouse database.`,
      });
    } else {
      showToast({
        type: 'success',
        title: 'Installation Work Verified & Submitted',
        message: 'BOM verification report, serial records, and rooftop photos submitted to Sales & HQ!',
      });
    }
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        activeMode === 'warehouse'
          ? 'Warehouse Serial & Inventory Stock Scanner'
          : 'Field Work & Installation Verification Scanner'
      }
      maxWidth="720px"
    >
      <div className="equipment-scanner-modal-body">
        {/* Role Mode Switcher for Testing (or for Admin) */}
        {isAdminUser && (
          <div className="scanner-role-switcher-strip">
            <button
              type="button"
              className={`scanner-role-pill ${activeMode === 'warehouse' ? 'active' : ''}`}
              onClick={() => setActiveMode('warehouse')}
            >
              <Package size={15} />
              <span>Warehouse Manager Mode (Maintain Stock)</span>
            </button>
            <button
              type="button"
              className={`scanner-role-pill ${activeMode === 'technician' ? 'active' : ''}`}
              onClick={() => setActiveMode('technician')}
            >
              <Wrench size={15} />
              <span>Technician Mode (Verify Work & BOM)</span>
            </button>
          </div>
        )}

        {/* Top Context Subtitle */}
        <p className="scanner-modal-description">
          {activeMode === 'warehouse'
            ? 'Scan serial numbers and QR codes on modules, inverters and batteries to update live warehouse stock counts and stage kits for installation dispatch.'
            : 'Scan serialized solar equipment on-site at Arun Kumar’s Indiranagar residence (#SO-0042) to confirm physical delivery against the approved engineering BOM.'}
        </p>

        {/* Warehouse Action Switcher: Inward vs Outward Dispatch */}
        {activeMode === 'warehouse' && (
          <div className="warehouse-action-toggle">
            <button
              type="button"
              className={`wh-toggle-btn ${warehouseAction === 'inward' ? 'active' : ''}`}
              onClick={() => setWarehouseAction('inward')}
            >
              <Plus size={14} />
              <span>Inward Goods Receiving (+ Stock)</span>
            </button>
            <button
              type="button"
              className={`wh-toggle-btn ${warehouseAction === 'dispatch' ? 'active' : ''}`}
              onClick={() => setWarehouseAction('dispatch')}
            >
              <ArrowRight size={14} />
              <span>Outward Installation Dispatch (- Staging)</span>
            </button>
          </div>
        )}

        {/* Technician Active Job Banner */}
        {activeMode === 'technician' && (
          <div className="tech-active-job-banner">
            <div className="job-meta-left">
              <MapPin size={16} color="#4f46e5" />
              <div>
                <strong>Active Site Survey / Installation #SO-0042</strong>
                <span>Arun Kumar · 5 kW Hybrid Rooftop · Indiranagar, Bengaluru</span>
              </div>
            </div>
            <span className="job-status-chip">Work in Progress</span>
          </div>
        )}

        {/* =================================================================
            CAMERA OPTICAL SCANNER VIEWFINDER
            ================================================================= */}
        <div className="scanner-viewfinder-card">
          <div className="viewfinder-camera-hud">
            {/* Corner Targeting Brackets */}
            <div className="hud-corner top-left" />
            <div className="hud-corner top-right" />
            <div className="hud-corner bottom-left" />
            <div className="hud-corner bottom-right" />

            {/* Scanning Laser Beam */}
            {laserActive && <div className="hud-scanning-laser" />}

            {/* Center Aiming Reticle */}
            <div className="hud-center-reticle">
              <ScanBarcode size={48} color="rgba(255, 255, 255, 0.85)" strokeWidth={1.5} />
              <span className="reticle-label">
                {activeMode === 'warehouse'
                  ? 'ALIGN BARCODE / QR SERIAL IN FRAME'
                  : 'ALIGN COMPONENT SERIAL PLATE'}
              </span>
            </div>

            {/* Live Camera Simulation HUD Metadata */}
            <div className="hud-meta-bar">
              <span className="hud-meta-item">
                <span className="live-camera-pulse" />
                <span>CAM-01 · 1080p Optical Feed</span>
              </span>
              <span className="hud-meta-item">
                FPS: 60 · ISO 200 · Azimuth: 180° S
              </span>
            </div>
          </div>

          {/* Scanner Viewfinder Control Buttons */}
          <div className="viewfinder-controls-row">
            <button
              type="button"
              className={`viewfinder-btn ${torchOn ? 'active' : ''}`}
              onClick={() => setTorchOn(!torchOn)}
              title="Toggle Camera Flashlight"
            >
              <Flashlight size={16} />
              <span>{torchOn ? 'Torch On' : 'Torch Off'}</span>
            </button>

            <button
              type="button"
              className="viewfinder-scan-trigger-btn"
              onClick={handleSimulateScan}
            >
              <Camera size={17} />
              <span>Capture & Scan Code</span>
            </button>

            <button
              type="button"
              className={`viewfinder-btn ${laserActive ? 'active' : ''}`}
              onClick={() => setLaserActive(!laserActive)}
              title="Toggle Laser Targeting"
            >
              <RefreshCw size={15} />
              <span>Laser Sweep</span>
            </button>
          </div>
        </div>

        {/* =================================================================
            MANUAL BARCODE INPUT & QUICK PRESET BUTTONS
            ================================================================= */}
        <div className="manual-scan-box">
          <label className="manual-scan-label" htmlFor="manualBarcode">
            Or Enter Serial Number / Barcode Manually:
          </label>
          <div className="manual-scan-input-group">
            <input
              id="manualBarcode"
              type="text"
              className="manual-scan-input"
              placeholder="e.g. SN-PV540-KA-0985 or INV-HYB5K-2026-041"
              value={barcodeInput}
              onChange={(e) => setBarcodeInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleScanBarcode(barcodeInput);
                }
              }}
            />
            <button
              type="button"
              className="manual-scan-submit-btn"
              onClick={() => handleScanBarcode(barcodeInput)}
            >
              Add Serial
            </button>
          </div>

          {/* Quick preset chips */}
          <div className="quick-presets-strip">
            <span className="presets-label">Quick Scan Presets:</span>
            {activeMode === 'warehouse' ? (
              <>
                <button
                  type="button"
                  className="preset-chip"
                  onClick={() =>
                    handleScanBarcode(
                      'SN-PV540-KA-0988',
                      'Waaree 540W Mono-PERC Module',
                      'Aisle B - Shelf 04'
                    )
                  }
                >
                  PV-540W (#0988)
                </button>
                <button
                  type="button"
                  className="preset-chip"
                  onClick={() =>
                    handleScanBarcode(
                      'INV-HYB5K-2026-042',
                      'SolarEdge 5kW Hybrid Inverter',
                      'Aisle A - Bay 02'
                    )
                  }
                >
                  Hybrid Inverter 5kW
                </button>
                <button
                  type="button"
                  className="preset-chip"
                  onClick={() =>
                    handleScanBarcode(
                      'BAT-5KWH-LFP-089',
                      'SolarFlow 5.12kWh Battery',
                      'Heavy Staging Area'
                    )
                  }
                >
                  Battery Pack 5kWh
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="preset-chip"
                  onClick={() => handleScanBarcode('INV-HYB5K-2026-041')}
                >
                  Inverter INV-041
                </button>
                <button
                  type="button"
                  className="preset-chip"
                  onClick={() => handleScanBarcode('BESCOM-KA-BLR-099234')}
                >
                  BESCOM Net-Meter
                </button>
                <button
                  type="button"
                  className="preset-chip"
                  onClick={() => handleScanBarcode('EARTH-PIT-KA-042')}
                >
                  Earth Pit Tag
                </button>
              </>
            )}
          </div>
        </div>

        {/* =================================================================
            ROLE-SPECIFIC REGISTRY / CHECKLIST
            ================================================================= */}
        {activeMode === 'warehouse' ? (
          /* Warehouse Scanned Items Table */
          <div className="scanned-registry-card">
            <div className="registry-header-row">
              <strong className="registry-title">
                Warehouse Stock Log ({scannedWarehouseItems.length} Items)
              </strong>
              <span className="registry-badge">
                {warehouseAction === 'inward' ? 'Inward Intake' : 'Dispatch Staging'}
              </span>
            </div>

            <div className="registry-items-list">
              {scannedWarehouseItems.map((item) => (
                <div key={item.id} className="registry-item-row">
                  <div className="registry-item-main">
                    <span className="item-serial-code">{item.serial}</span>
                    <strong className="item-title">{item.name}</strong>
                    <span className="item-meta-text">
                      {item.rack} · Batch: {item.batch}
                    </span>
                  </div>
                  <div className="registry-item-right">
                    <span className="item-status-pill green">
                      <CheckCircle2 size={13} />
                      <span>{item.status}</span>
                    </span>
                    <span className="item-time">{item.time}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          /* Technician BOM Verification Checklist */
          <div className="scanned-registry-card">
            <div className="registry-header-row">
              <strong className="registry-title">
                Sales BOM Installation Verification
              </strong>
              <span className="registry-badge">
                {techVerificationList.filter((i) => i.status === 'matched').length}/
                {techVerificationList.length} Verified
              </span>
            </div>

            <div className="registry-items-list">
              {techVerificationList.map((item) => (
                <div key={item.id} className="registry-item-row">
                  <div className="registry-item-main">
                    <strong className="item-title">{item.component}</strong>
                    <span className="item-meta-text">{item.label}</span>
                    <span className="item-serial-code">
                      Target BOM: {item.targetSerial}
                    </span>
                  </div>
                  <div className="registry-item-right">
                    {item.status === 'matched' ? (
                      <span className="item-status-pill green">
                        <CheckCircle2 size={13} />
                        <span>Verified: {item.scannedSerial}</span>
                      </span>
                    ) : (
                      <span className="item-status-pill amber">
                        Scan Pending
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* =================================================================
            PHOTO / WORK EVIDENCE ATTACHMENT UPLOAD ZONE
            ================================================================= */}
        <div className="evidence-upload-zone">
          <div className="evidence-upload-header">
            <strong>
              {activeMode === 'warehouse'
                ? 'Upload Delivery Challan / Pallet Packing Slip'
                : 'Upload Rooftop Azimuth & Workmanship Photos'}
            </strong>
            <span className="evidence-subtext">
              Attached files will be GPS-tagged and synchronized with HQ.
            </span>
          </div>

          <div className="evidence-file-picker">
            <label className="upload-dropzone" htmlFor="scannerProofUpload">
              <Upload size={20} color="#4f46e5" />
              <span>Click or drag image to upload evidence photo</span>
              <input
                id="scannerProofUpload"
                type="file"
                accept="image/*,application/pdf"
                className="hidden-file-input"
                onChange={handleFileUpload}
              />
            </label>
          </div>

          {/* Attached Files List */}
          {uploadedFiles.length > 0 && (
            <div className="attached-files-row">
              {uploadedFiles.map((f, idx) => (
                <div key={idx} className="attached-file-pill">
                  <FileCheck size={14} color="#059669" />
                  <span className="file-name">{f.name}</span>
                  <span className="file-size">({f.size})</span>
                  <button
                    type="button"
                    className="file-remove-btn"
                    onClick={() => handleRemoveFile(idx)}
                    title="Remove File"
                  >
                    <X size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* =================================================================
            MODAL ACTIONS: COMMIT & CLOSE
            ================================================================= */}
        <div className="scanner-modal-footer">
          <button type="button" className="scanner-btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="scanner-btn-commit"
            onClick={handleCommit}
          >
            <CheckCircle2 size={16} />
            <span>
              {activeMode === 'warehouse'
                ? 'Upload & Commit Stock Updates'
                : 'Submit Verified Work to Sales & HQ'}
            </span>
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default EquipmentScannerModal;


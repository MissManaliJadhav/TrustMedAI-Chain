import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Avatar,
  Badge,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  MenuItem,
  TextField,
} from '@mui/material';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import AutoGraphIcon from '@mui/icons-material/AutoGraph';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import DownloadIcon from '@mui/icons-material/Download';
import EmergencyIcon from '@mui/icons-material/Emergency';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import HistoryIcon from '@mui/icons-material/History';
import LogoutIcon from '@mui/icons-material/Logout';
import MedicalInformationIcon from '@mui/icons-material/MedicalInformation';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';
import PersonSearchIcon from '@mui/icons-material/PersonSearch';
import RateReviewIcon from '@mui/icons-material/RateReview';
import SaveIcon from '@mui/icons-material/Save';
import SettingsIcon from '@mui/icons-material/Settings';
import ShieldIcon from '@mui/icons-material/Shield';
import UploadIcon from '@mui/icons-material/Upload';
import { Link, useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import { api } from '../api/client';
import { useAppDispatch } from '../store';
import { logout } from '../store/authSlice';

interface DiagnosisRecord {
  diagnosis_id: string;
  patient_id: string | null;
  patient_name: string | null;
  patient_email: string | null;
  doctor_id: string | null;
  disease_key: string;
  prediction: string;
  confidence: number;
  trust_score: number;
  blockchain_hash: string;
  ethereum_tx_hash: string | null;
  fabric_tx_id: string | null;
  doctor_notes: string | null;
  review_status: string | null;
  doctor_decision: string | null;
  final_clinical_decision: string | null;
  review_notes: string | null;
  reviewed_by_id: string | null;
  reviewed_at: string | null;
  priority: string | null;
  created_at: string;
}

interface DoctorSummary {
  total_assigned_patients: number;
  pending_diagnosis_reviews: number;
  high_risk_cases: number;
  reviewed_diagnoses: number;
  todays_new_cases: number;
  average_ai_trust_score: number;
  blockchain_verified_records: number;
  unread_notifications: number;
}

interface DoctorProfile {
  id: string;
  email: string;
  full_name: string;
  doctor_id: string;
  profile_photo_available: boolean;
  medical_registration_number: string | null;
  specialization: string | null;
  qualifications: string | null;
  experience: string | null;
  hospital_organization: string | null;
  contact_information: string | null;
  phone_number: string | null;
  account_status: string;
  last_login: string | null;
  profile_verification_status: string;
  created_at: string;
  profile_updated_at: string | null;
}

interface PatientSummary {
  patient_id: string | null;
  patient_name: string | null;
  patient_email: string | null;
  total_diagnoses: number;
  active_cases: number;
  latest_diagnosis_at: string | null;
  average_trust_score: number;
}

interface DoctorNotification {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  diagnosis_id: string | null;
  severity: string;
  is_read: boolean;
  created_at: string;
}

type SectionKey =
  | 'dashboard'
  | 'patients'
  | 'pending'
  | 'reviews'
  | 'high-risk'
  | 'history'
  | 'ai'
  | 'reports'
  | 'blockchain'
  | 'notifications'
  | 'profile'
  | 'settings';

const navItems: Array<{ key: SectionKey | 'logout'; label: string; icon: JSX.Element }> = [
  { key: 'dashboard', label: 'Dashboard', icon: <MedicalInformationIcon /> },
  { key: 'patients', label: 'My Patients', icon: <PeopleAltIcon /> },
  { key: 'pending', label: 'Pending Reviews', icon: <RateReviewIcon /> },
  { key: 'reviews', label: 'Diagnosis Reviews', icon: <AssignmentTurnedInIcon /> },
  { key: 'high-risk', label: 'High-Risk Cases', icon: <EmergencyIcon /> },
  { key: 'history', label: 'Medical History', icon: <HistoryIcon /> },
  { key: 'ai', label: 'AI Analysis', icon: <AutoGraphIcon /> },
  { key: 'reports', label: 'Reports', icon: <DownloadIcon /> },
  { key: 'blockchain', label: 'Blockchain Verification', icon: <ShieldIcon /> },
  { key: 'notifications', label: 'Notifications', icon: <NotificationsActiveIcon /> },
  { key: 'profile', label: 'My Profile', icon: <AccountCircleIcon /> },
  { key: 'settings', label: 'Settings', icon: <SettingsIcon /> },
  { key: 'logout', label: 'Logout', icon: <LogoutIcon /> },
];

const emptyProfile = {
  full_name: '',
  specialization: '',
  qualifications: '',
  experience: '',
  hospital_organization: '',
  phone_number: '',
  contact_information: '',
  availability: '',
};

function pct(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function clean(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return 'Not Available';
  return String(value);
}

function highRisk(record: DiagnosisRecord) {
  const prediction = record.prediction.toLowerCase();
  return (
    (record.confidence >= 0.85 && !['normal', 'negative', 'healthy', 'controlled', 'no_tumor'].some((token) => prediction.includes(token))) ||
    record.trust_score < 0.55 ||
    prediction.includes('high') ||
    prediction.includes('risk')
  );
}

export default function DoctorDashboardPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [section, setSection] = useState<SectionKey>('dashboard');
  const [summary, setSummary] = useState<DoctorSummary | null>(null);
  const [profile, setProfile] = useState<DoctorProfile | null>(null);
  const [profileForm, setProfileForm] = useState(emptyProfile);
  const [photoUrl, setPhotoUrl] = useState('');
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [notifications, setNotifications] = useState<DoctorNotification[]>([]);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [downloadingId, setDownloadingId] = useState('');
  const [confirmRecord, setConfirmRecord] = useState<DiagnosisRecord | null>(null);
  const [decision, setDecision] = useState('Confirmed');
  const [finalDecision, setFinalDecision] = useState('Confirmed');
  const [reviewNotes, setReviewNotes] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadPhoto = async (hasPhoto: boolean) => {
    if (!hasPhoto) {
      setPhotoUrl('');
      return;
    }
    try {
      const response = await api.get('/doctors/profile/photo', { responseType: 'blob', timeout: 60000 });
      const url = URL.createObjectURL(response.data);
      setPhotoUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return url;
      });
    } catch {
      setPhotoUrl('');
    }
  };

  const refresh = async () => {
    setLoading(true);
    setError('');
    try {
      const [summaryRes, profileRes, reviewsRes, patientsRes, notificationsRes] = await Promise.all([
        api.get<DoctorSummary>('/doctors/dashboard'),
        api.get<DoctorProfile>('/doctors/profile'),
        api.get<DiagnosisRecord[]>('/doctors/reviews'),
        api.get<PatientSummary[]>('/doctors/patients'),
        api.get<DoctorNotification[]>('/doctors/notifications'),
      ]);
      setSummary(summaryRes.data);
      setProfile(profileRes.data);
      setProfileForm({
        ...emptyProfile,
        full_name: profileRes.data.full_name,
        specialization: profileRes.data.specialization ?? '',
        qualifications: profileRes.data.qualifications ?? '',
        experience: profileRes.data.experience ?? '',
        hospital_organization: profileRes.data.hospital_organization ?? '',
        phone_number: profileRes.data.phone_number ?? '',
        contact_information: profileRes.data.contact_information ?? '',
      });
      setRecords(reviewsRes.data);
      setPatients(patientsRes.data);
      setNotifications(notificationsRes.data);
      await loadPhoto(profileRes.data.profile_photo_available);
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Doctor workspace could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    return () => {
      if (photoUrl) URL.revokeObjectURL(photoUrl);
    };
  }, []);

  const filteredPatients = useMemo(() => {
    const q = search.trim().toLowerCase();
    return patients.filter((patient) => {
      const matchesFilter = filter === 'all' || (filter === 'active' && patient.active_cases > 0) || (filter === 'high-risk' && records.some((record) => (record.patient_id === patient.patient_id || record.patient_email === patient.patient_email) && highRisk(record)));
      const haystack = `${patient.patient_name ?? ''} ${patient.patient_email ?? ''} ${patient.patient_id ?? ''}`.toLowerCase();
      return matchesFilter && (!q || haystack.includes(q));
    });
  }, [patients, records, search, filter]);

  const pendingRecords = records.filter((record) => (record.review_status ?? 'pending') === 'pending');
  const reviewedRecords = records.filter((record) => (record.review_status ?? 'pending') !== 'pending');
  const highRiskRecords = records.filter(highRisk);
  const displayedRecords = section === 'pending' ? pendingRecords : section === 'high-risk' ? highRiskRecords : records;
  const unreadCount = notifications.filter((item) => !item.is_read).length || summary?.unread_notifications || 0;

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingProfile(true);
    setError('');
    setSuccess('');
    try {
      const payload = Object.fromEntries(Object.entries(profileForm).map(([key, value]) => [key, value.trim() || null]));
      const response = await api.put<DoctorProfile>('/doctors/profile', payload);
      setProfile(response.data);
      setSuccess('Doctor profile updated.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Doctor profile update failed.');
    } finally {
      setSavingProfile(false);
    }
  };

  const uploadPhoto = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setError('');
    setSuccess('');
    try {
      const upload = new FormData();
      upload.append('photo', file);
      const response = await api.post<DoctorProfile>('/doctors/profile/photo', upload, { timeout: 120000 });
      setProfile(response.data);
      await loadPhoto(true);
      setSuccess('Doctor profile photo updated.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Photo upload failed.');
    } finally {
      event.target.value = '';
    }
  };

  const downloadReport = async (record: DiagnosisRecord) => {
    setDownloadingId(record.diagnosis_id);
    setError('');
    setSuccess('');
    try {
      const response = await api.get(`/reports/${record.diagnosis_id}.pdf`, { responseType: 'blob', timeout: 120000 });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `trustmedai-${record.diagnosis_id}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
      setSuccess('Report downloaded.');
    } catch {
      setError('Report download failed.');
    } finally {
      setDownloadingId('');
    }
  };

  const verifyBlockchain = async (record: DiagnosisRecord) => {
    setError('');
    setSuccess('');
    try {
      await api.post(`/doctors/blockchain/verify/${record.diagnosis_id}`);
      setSuccess('Blockchain verification recorded in audit trail.');
      await refresh();
    } catch {
      setError('Blockchain verification failed.');
    }
  };

  const finalizeReview = async () => {
    if (!confirmRecord) return;
    setError('');
    setSuccess('');
    try {
      await api.post(`/doctors/diagnoses/${confirmRecord.diagnosis_id}/finalize`, {
        doctor_decision: decision,
        final_clinical_decision: finalDecision,
        review_notes: reviewNotes,
        review_status: decision.toLowerCase() === 'rejected' ? 'rejected' : 'reviewed',
      });
      setConfirmRecord(null);
      setReviewNotes('');
      setSuccess('Clinical review finalized and audited.');
      await refresh();
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Clinical review could not be finalized.');
    }
  };

  const handleNav = (key: SectionKey | 'logout') => {
    if (key === 'logout') {
      dispatch(logout());
      navigate('/login');
      return;
    }
    setSection(key);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7fbfa]">
        <Header />
        <main className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-16">
          <CircularProgress size={28} />
          <span>Loading doctor workspace...</span>
        </main>
      </div>
    );
  }

  const initials = (profile?.full_name ?? 'Doctor').split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  const cards = [
    ['Total Assigned Patients', summary?.total_assigned_patients ?? 0, <PeopleAltIcon />, 'bg-teal-50 text-teal-700'],
    ['Pending Diagnosis Reviews', summary?.pending_diagnosis_reviews ?? 0, <RateReviewIcon />, 'bg-amber-50 text-amber-700'],
    ['High-Risk Cases', summary?.high_risk_cases ?? 0, <EmergencyIcon />, 'bg-rose-50 text-rose-700'],
    ['Reviewed Diagnoses', summary?.reviewed_diagnoses ?? 0, <AssignmentTurnedInIcon />, 'bg-blue-50 text-blue-700'],
    ["Today's New Cases", summary?.todays_new_cases ?? 0, <CalendarMonthIcon />, 'bg-indigo-50 text-indigo-700'],
    ['Average AI Trust Score', pct(summary?.average_ai_trust_score ?? 0), <AutoGraphIcon />, 'bg-cyan-50 text-cyan-700'],
    ['Blockchain-Verified Records', summary?.blockchain_verified_records ?? 0, <ShieldIcon />, 'bg-emerald-50 text-emerald-700'],
    ['Unread Notifications', unreadCount, <NotificationsActiveIcon />, 'bg-slate-100 text-slate-700'],
  ];

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto grid max-w-[1500px] gap-6 px-4 py-6 xl:grid-cols-[280px_1fr]">
        <aside className="rounded border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
            <Avatar src={photoUrl || undefined} sx={{ width: 54, height: 54, bgcolor: '#0f766e', fontWeight: 900 }}>{initials}</Avatar>
            <div className="min-w-0">
              <p className="truncate font-black text-slate-950">{profile?.full_name ?? 'Doctor'}</p>
              <p className="truncate text-xs text-slate-500">{profile?.specialization ?? 'Specialization not set'}</p>
            </div>
          </div>
          <nav className="mt-4 space-y-1">
            {navItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => handleNav(item.key)}
                className={`flex w-full items-center gap-3 rounded px-3 py-2 text-left text-sm font-bold transition ${section === item.key ? 'bg-teal-50 text-teal-800' : 'text-slate-600 hover:bg-slate-50'}`}
              >
                {item.key === 'notifications' ? <Badge color="error" badgeContent={unreadCount}>{item.icon}</Badge> : item.icon}
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        <section className="min-w-0">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-black">Doctor Workspace</h1>
              <p className="mt-1 text-slate-600">Clinical reviews, patient timelines, reports, notifications, and audit-ready decisions.</p>
            </div>
            <Button component={Link} to="/diagnosis" variant="contained">New Diagnosis</Button>
          </div>

          {error && <Alert className="mb-5" severity="error">{error}</Alert>}
          {success && <Alert className="mb-5" severity="success" onClose={() => setSuccess('')}>{success}</Alert>}

          {section === 'dashboard' && (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {cards.map(([label, value, icon, tone]) => (
                <article key={String(label)} className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-500">{label}</p>
                      <p className="mt-2 text-3xl font-black text-slate-950">{value}</p>
                    </div>
                    <span className={`grid h-11 w-11 place-items-center rounded ${tone}`}>{icon}</span>
                  </div>
                </article>
              ))}
            </div>
          )}

          {section === 'patients' && (
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-black">My Patients</h2>
                  <p className="mt-1 text-sm text-slate-500">Search, filter, and open active patient histories.</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <TextField size="small" label="Search patient" value={search} onChange={(event) => setSearch(event.target.value)} InputProps={{ startAdornment: <PersonSearchIcon className="mr-2 text-slate-400" /> }} />
                  <TextField size="small" select label="Filter" value={filter} onChange={(event) => setFilter(event.target.value)}>
                    <MenuItem value="all">All patients</MenuItem>
                    <MenuItem value="active">Active cases</MenuItem>
                    <MenuItem value="high-risk">High-risk</MenuItem>
                  </TextField>
                </div>
              </div>
              <div className="mt-5 grid gap-3">
                {filteredPatients.map((patient) => (
                  <article key={`${patient.patient_id ?? patient.patient_email}`} className="rounded border border-slate-200 bg-slate-50 p-4">
                    <div className="grid gap-3 lg:grid-cols-[1fr_260px]">
                      <div>
                        <p className="font-black">{clean(patient.patient_name)}</p>
                        <p className="text-sm text-slate-500">{clean(patient.patient_email)} | {clean(patient.patient_id)}</p>
                        <p className="mt-2 text-sm">Diagnoses: {patient.total_diagnoses} | Active cases: {patient.active_cases} | Avg trust {pct(patient.average_trust_score)}</p>
                      </div>
                      <Button variant="outlined" onClick={() => { setSearch(patient.patient_email ?? patient.patient_id ?? patient.patient_name ?? ''); setSection('history'); }}>
                        View Medical History
                      </Button>
                    </div>
                  </article>
                ))}
                {!filteredPatients.length && <p className="rounded bg-slate-50 p-6 text-slate-500">No patients match the current filter.</p>}
              </div>
            </div>
          )}

          {['pending', 'reviews', 'high-risk', 'history', 'ai', 'reports', 'blockchain'].includes(section) && (
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">
                {section === 'pending' ? 'Pending Reviews' : section === 'high-risk' ? 'High-Risk Cases' : section === 'history' ? 'Patient Medical History' : section === 'ai' ? 'AI Analysis' : section === 'reports' ? 'Reports' : section === 'blockchain' ? 'Blockchain Verification' : 'Diagnosis Reviews'}
              </h2>
              <div className="mt-5 grid gap-4">
                {displayedRecords.map((record) => (
                  <article key={record.diagnosis_id} className="rounded border border-slate-200 bg-slate-50 p-4">
                    <div className="grid gap-4 xl:grid-cols-[1fr_330px]">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`rounded px-2 py-1 text-xs font-black ${highRisk(record) ? 'bg-rose-100 text-rose-700' : 'bg-teal-100 text-teal-700'}`}>
                            {highRisk(record) ? 'High Risk' : clean(record.priority)}
                          </span>
                          <span className="rounded bg-white px-2 py-1 text-xs font-black text-slate-600">{clean(record.review_status ?? 'pending')}</span>
                        </div>
                        <h3 className="mt-3 font-black capitalize">{record.patient_name ?? 'Unnamed patient'} | {record.disease_key.replace(/_/g, ' ')}</h3>
                        <p className="mt-1 text-sm text-slate-600">Original AI Result: <strong>{record.prediction.replace(/_/g, ' ')}</strong> at {pct(record.confidence)}</p>
                        <p className="mt-1 text-sm text-slate-600">Doctor Decision: <strong>{clean(record.doctor_decision)}</strong> | Final: {clean(record.final_clinical_decision)}</p>
                        <p className="mt-1 text-sm text-slate-500">Diagnosis date: {new Date(record.created_at).toLocaleString()}</p>
                        {record.review_notes && <p className="mt-3 rounded bg-white p-3 text-sm text-slate-600">{record.review_notes}</p>}
                      </div>
                      <div className="rounded bg-white p-4">
                        <p className="text-sm font-bold text-slate-500">AI Trust Score</p>
                        <p className="mt-1 text-2xl font-black">{pct(record.trust_score)}</p>
                        <LinearProgress className="mt-2" variant="determinate" value={record.trust_score * 100} />
                        <div className="mt-4 flex flex-wrap gap-2">
                          <Button size="small" variant="contained" startIcon={<FactCheckIcon />} onClick={() => { setConfirmRecord(record); setDecision('Confirmed'); setFinalDecision('Confirmed'); }}>
                            Finalize
                          </Button>
                          <Button size="small" variant="outlined" startIcon={downloadingId === record.diagnosis_id ? <CircularProgress size={14} /> : <DownloadIcon />} onClick={() => downloadReport(record)} disabled={downloadingId === record.diagnosis_id}>
                            Report
                          </Button>
                          <Button size="small" variant="outlined" startIcon={<ShieldIcon />} onClick={() => verifyBlockchain(record)}>
                            Verify
                          </Button>
                        </div>
                      </div>
                    </div>
                  </article>
                ))}
                {!displayedRecords.length && <p className="rounded bg-slate-50 p-6 text-slate-500">No records found for this section.</p>}
              </div>
            </div>
          )}

          {section === 'notifications' && (
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Notifications</h2>
              <div className="mt-5 grid gap-3">
                {notifications.map((notification) => (
                  <article key={notification.id} className={`rounded border p-4 ${notification.is_read ? 'border-slate-200 bg-slate-50' : 'border-teal-200 bg-teal-50'}`}>
                    <div className="flex flex-wrap justify-between gap-3">
                      <div>
                        <p className="font-black">{notification.title}</p>
                        <p className="mt-1 text-sm text-slate-600">{notification.message}</p>
                        <p className="mt-2 text-xs text-slate-500">{new Date(notification.created_at).toLocaleString()} | {notification.severity}</p>
                      </div>
                      {!notification.is_read && (
                        <Button size="small" onClick={async () => { await api.post(`/doctors/notifications/${notification.id}/read`); await refresh(); }}>
                          Mark Read
                        </Button>
                      )}
                    </div>
                  </article>
                ))}
                {!notifications.length && <p className="rounded bg-slate-50 p-6 text-slate-500">No notifications yet.</p>}
              </div>
            </div>
          )}

          {section === 'profile' && (
            <form onSubmit={saveProfile} className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex items-center gap-4">
                  <Avatar src={photoUrl || undefined} sx={{ width: 86, height: 86, bgcolor: '#0f766e', fontSize: 28, fontWeight: 900 }}>{initials}</Avatar>
                  <div>
                    <h2 className="text-xl font-black">Doctor Profile</h2>
                    <p className="mt-1 text-sm text-slate-500">Doctor ID: {clean(profile?.doctor_id)}</p>
                    <p className="text-sm text-slate-500">Verification: {clean(profile?.profile_verification_status)}</p>
                  </div>
                </div>
                <Button component="label" variant="outlined" startIcon={<UploadIcon />}>
                  Change Photo
                  <input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadPhoto} />
                </Button>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <TextField label="Full Name" value={profileForm.full_name} onChange={(event) => setProfileForm((current) => ({ ...current, full_name: event.target.value }))} />
                <TextField label="Specialization" value={profileForm.specialization} onChange={(event) => setProfileForm((current) => ({ ...current, specialization: event.target.value }))} />
                <TextField label="Qualifications" value={profileForm.qualifications} onChange={(event) => setProfileForm((current) => ({ ...current, qualifications: event.target.value }))} multiline minRows={2} />
                <TextField label="Experience" value={profileForm.experience} onChange={(event) => setProfileForm((current) => ({ ...current, experience: event.target.value }))} />
                <TextField label="Hospital / Organization" value={profileForm.hospital_organization} onChange={(event) => setProfileForm((current) => ({ ...current, hospital_organization: event.target.value }))} />
                <TextField label="Phone Number" value={profileForm.phone_number} onChange={(event) => setProfileForm((current) => ({ ...current, phone_number: event.target.value }))} />
                <TextField label="Contact Information" value={profileForm.contact_information} onChange={(event) => setProfileForm((current) => ({ ...current, contact_information: event.target.value }))} multiline minRows={2} />
                <TextField label="Availability" value={profileForm.availability} onChange={(event) => setProfileForm((current) => ({ ...current, availability: event.target.value }))} multiline minRows={2} />
              </div>
              <div className="mt-5 rounded bg-slate-50 p-4 text-sm text-slate-600">
                Protected identity fields require admin authorization: medical registration number, profile verification status, and account status.
                <div className="mt-2 grid gap-2 md:grid-cols-3">
                  <span>Registration: {clean(profile?.medical_registration_number)}</span>
                  <span>Email: {clean(profile?.email)}</span>
                  <span>Last Login: {profile?.last_login ? new Date(profile.last_login).toLocaleString() : 'Not Available'}</span>
                </div>
              </div>
              <Button className="mt-5" type="submit" variant="contained" startIcon={<SaveIcon />} disabled={savingProfile}>
                {savingProfile ? 'Saving...' : 'Save Doctor Profile'}
              </Button>
            </form>
          )}

          {section === 'settings' && (
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Settings</h2>
              <p className="mt-3 text-slate-600">Professional identity changes are intentionally restricted to admin authorization. Notification and review activity are stored in the audit trail.</p>
            </div>
          )}
        </section>
      </main>

      <Dialog open={Boolean(confirmRecord)} onClose={() => setConfirmRecord(null)} maxWidth="sm" fullWidth>
        <DialogTitle>You are about to finalize this clinical review.</DialogTitle>
        <DialogContent className="space-y-4">
          <Alert severity="warning">
            AI Prediction: {confirmRecord?.prediction.replace(/_/g, ' ')} | Doctor Decision: {decision}. After submission, this action will be recorded in the audit trail.
          </Alert>
          <TextField select fullWidth label="Doctor Decision" value={decision} onChange={(event) => { setDecision(event.target.value); setFinalDecision(event.target.value); }}>
            <MenuItem value="Confirmed">Confirmed</MenuItem>
            <MenuItem value="Rejected">Rejected</MenuItem>
            <MenuItem value="Overridden">Overridden</MenuItem>
          </TextField>
          <TextField fullWidth label="Final Clinical Decision" value={finalDecision} onChange={(event) => setFinalDecision(event.target.value)} />
          <TextField fullWidth label="Doctor Notes" value={reviewNotes} onChange={(event) => setReviewNotes(event.target.value)} multiline minRows={4} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmRecord(null)}>Cancel</Button>
          <Button variant="contained" onClick={finalizeReview}>Submit Final Review</Button>
        </DialogActions>
      </Dialog>
    </div>
  );
}

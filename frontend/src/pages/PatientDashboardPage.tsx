import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { Alert, Avatar, Button, CircularProgress, LinearProgress, TextField } from '@mui/material';
import BadgeIcon from '@mui/icons-material/Badge';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import ContactEmergencyIcon from '@mui/icons-material/ContactEmergency';
import DownloadIcon from '@mui/icons-material/Download';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import HistoryIcon from '@mui/icons-material/History';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import MedicationIcon from '@mui/icons-material/Medication';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import PhotoCameraIcon from '@mui/icons-material/PhotoCamera';
import SaveIcon from '@mui/icons-material/Save';
import VaccinesIcon from '@mui/icons-material/Vaccines';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import { api } from '../api/client';
import type { TrustPoint } from '../types';

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
  doctor_notes: string | null;
  created_at: string;
}

interface PatientProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  patient_id: string;
  registration_date: string;
  last_profile_update: string | null;
  profile_photo_url: string | null;
  profile_photo_available: boolean;
  age: number | null;
  profile_completion: number;
  profile: Record<string, string | null>;
}

type ProfileForm = {
  full_name: string;
  date_of_birth: string;
  sex: string;
  gender: string;
  blood_group: string;
  phone_number: string;
  address: string;
  city: string;
  state: string;
  country: string;
  emergency_contact_name: string;
  emergency_contact_phone: string;
  medical_information: string;
  allergies: string;
  medications: string;
  insurance: string;
  lifestyle: string;
  vaccination_history: string;
};

const emptyProfileForm: ProfileForm = {
  full_name: '',
  date_of_birth: '',
  sex: '',
  gender: '',
  blood_group: '',
  phone_number: '',
  address: '',
  city: '',
  state: '',
  country: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  medical_information: '',
  allergies: '',
  medications: '',
  insurance: '',
  lifestyle: '',
  vaccination_history: '',
};

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function show(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return 'Not Available';
  return String(value);
}

function profileToForm(profile: PatientProfile | null): ProfileForm {
  if (!profile) return emptyProfileForm;
  return {
    ...emptyProfileForm,
    ...Object.fromEntries(
      Object.keys(emptyProfileForm).map((key) => [
        key,
        key === 'full_name' ? profile.full_name : String(profile.profile[key] ?? ''),
      ]),
    ),
  };
}

export default function PatientDashboardPage() {
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [trust, setTrust] = useState<TrustPoint[]>([]);
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileForm>(emptyProfileForm);
  const [photoUrl, setPhotoUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [downloadingId, setDownloadingId] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadPhoto = async (hasPhoto: boolean) => {
    if (!hasPhoto) {
      setPhotoUrl('');
      return;
    }
    try {
      const response = await api.get('/patients/profile/photo', { responseType: 'blob', timeout: 60000 });
      const url = URL.createObjectURL(response.data);
      setPhotoUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return url;
      });
    } catch {
      setPhotoUrl('');
    }
  };

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const [recordsResponse, trustResponse, profileResponse] = await Promise.all([
        api.get('/predictions').catch(() => ({ data: [] })),
        api.get('/trust/history').catch(() => ({ data: [] })),
        api.get<PatientProfile>('/patients/profile'),
      ]);
      setRecords(recordsResponse.data);
      setTrust(trustResponse.data);
      setProfile(profileResponse.data);
      setProfileForm(profileToForm(profileResponse.data));
      await loadPhoto(profileResponse.data.profile_photo_available);
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Patient dashboard could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    return () => {
      if (photoUrl) URL.revokeObjectURL(photoUrl);
    };
  }, []);

  const updateField = (field: keyof ProfileForm) => (event: ChangeEvent<HTMLInputElement>) => {
    setProfileForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSavingProfile(true);
    setError('');
    setSuccess('');
    try {
      const payload = Object.fromEntries(
        Object.entries(profileForm).map(([key, value]) => [key, value.trim() || null]),
      );
      const response = await api.put<PatientProfile>('/patients/profile', payload);
      setProfile(response.data);
      setProfileForm(profileToForm(response.data));
      setSuccess('Profile updated successfully.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Profile update failed.');
    } finally {
      setSavingProfile(false);
    }
  };

  const uploadPhoto = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadingPhoto(true);
    setError('');
    setSuccess('');
    try {
      const upload = new FormData();
      upload.append('photo', file);
      const response = await api.post<PatientProfile>('/patients/profile/photo', upload, { timeout: 120000 });
      setProfile(response.data);
      await loadPhoto(true);
      setSuccess('Profile photo updated successfully.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Profile photo upload failed.');
    } finally {
      setUploadingPhoto(false);
      event.target.value = '';
    }
  };

  const downloadReport = async (record: DiagnosisRecord) => {
    setDownloadingId(record.diagnosis_id);
    setError('');
    setSuccess('');
    try {
      const response = await api.get(`/reports/${record.diagnosis_id}.pdf`, {
        responseType: 'blob',
        timeout: 120000,
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `trustmedai-${record.diagnosis_id}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
      setSuccess('Report downloaded successfully.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'The report could not be downloaded.');
    } finally {
      setDownloadingId('');
    }
  };

  const latestRecord = records[0];
  const averageTrust = records.length
    ? records.reduce((sum, record) => sum + record.trust_score, 0) / records.length
    : trust.length ? trust[trust.length - 1].dtei : 0.86;
  const healthScore = latestRecord ? Math.min(0.99, (latestRecord.confidence + latestRecord.trust_score) / 2) : 0.82;
  const completion = (profile?.profile_completion ?? 0) / 100;
  const notifications = [
    records.length ? `${records.length} diagnosis record${records.length === 1 ? '' : 's'} available` : 'No diagnosis records yet',
    latestRecord ? `Latest AI review: ${latestRecord.prediction.replace(/_/g, ' ')}` : 'Create your first AI diagnosis',
    profile ? `Profile completion: ${profile.profile_completion}%` : 'Complete your patient profile',
  ];

  const timeline = useMemo(() => records.slice(0, 8), [records]);
  const initials = (profile?.full_name ?? latestRecord?.patient_name ?? 'Patient')
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  const dashboardCards = [
    { label: 'Health Score', value: percent(healthScore), progress: healthScore, icon: <MonitorHeartIcon />, tone: 'bg-teal-50 text-teal-700' },
    { label: 'AI Trust Score', value: percent(averageTrust), progress: averageTrust, icon: <HealthAndSafetyIcon />, tone: 'bg-blue-50 text-blue-700' },
    {
      label: 'Recent Diagnosis',
      value: latestRecord ? latestRecord.prediction.replace(/_/g, ' ') : 'None',
      progress: latestRecord?.confidence ?? 0,
      icon: <LocalHospitalIcon />,
      tone: 'bg-rose-50 text-rose-700',
    },
    { label: 'Upcoming Appointments', value: '0', progress: 0, icon: <CalendarMonthIcon />, tone: 'bg-amber-50 text-amber-700' },
    { label: 'Notifications', value: String(notifications.length), progress: 0.75, icon: <NotificationsActiveIcon />, tone: 'bg-indigo-50 text-indigo-700' },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7fbfa]">
        <Header />
        <main className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-16">
          <CircularProgress size={28} />
          <span>Loading patient portal...</span>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black">Patient Portal</h1>
            <p className="mt-1 text-slate-600">Dashboard, diagnosis history, profile, notifications, and downloadable reports.</p>
          </div>
          <Button component={Link} to="/diagnosis" variant="contained">
            Start Diagnosis
          </Button>
        </div>

        {error && <Alert className="mb-5" severity="error">{error}</Alert>}
        {success && <Alert className="mb-5" severity="success" onClose={() => setSuccess('')}>{success}</Alert>}

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          {dashboardCards.map((card) => (
            <article key={card.label} className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-500">{card.label}</p>
                  <p className="mt-2 text-2xl font-black capitalize text-slate-950">{card.value}</p>
                </div>
                <span className={`grid h-11 w-11 shrink-0 place-items-center rounded ${card.tone}`}>{card.icon}</span>
              </div>
              <LinearProgress className="mt-4" variant="determinate" value={card.progress * 100} />
            </article>
          ))}
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[390px_1fr]">
          <aside className="space-y-6">
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-4">
                <Avatar src={photoUrl || undefined} sx={{ width: 88, height: 88, bgcolor: '#0f766e', fontSize: 28, fontWeight: 900 }}>
                  {initials}
                </Avatar>
                <div className="min-w-0">
                  <p className="break-words text-lg font-black text-slate-950">{show(profile?.full_name)}</p>
                  <p className="break-words text-sm text-slate-500">{show(profile?.email)}</p>
                  <p className="mt-1 text-xs font-semibold text-teal-700">Patient ID: {show(profile?.patient_id)}</p>
                </div>
              </div>
              <div className="mt-5">
                <div className="mb-2 flex justify-between text-sm">
                  <span className="font-semibold text-slate-600">Profile Completion</span>
                  <span className="font-black text-teal-700">{profile?.profile_completion ?? 0}%</span>
                </div>
                <LinearProgress variant="determinate" value={completion * 100} />
              </div>
              <Button className="mt-5" component="label" variant="outlined" startIcon={<PhotoCameraIcon />} disabled={uploadingPhoto}>
                {uploadingPhoto ? 'Uploading...' : 'Upload Photo'}
                <input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadPhoto} />
              </Button>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Account Information</h2>
              <dl className="mt-4 space-y-3 text-sm">
                {[
                  ['Patient ID', profile?.patient_id],
                  ['Registration Date', profile?.registration_date ? new Date(profile.registration_date).toLocaleString() : null],
                  ['Last Profile Update', profile?.last_profile_update ? new Date(profile.last_profile_update).toLocaleString() : null],
                  ['Age', profile?.age],
                ].map(([label, value]) => (
                  <div key={label} className="rounded bg-slate-50 p-3">
                    <dt className="font-semibold text-slate-500">{label}</dt>
                    <dd className="mt-1 break-words font-bold text-slate-900">{show(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Notifications</h2>
              <div className="mt-4 space-y-3">
                {notifications.map((notification) => (
                  <p key={notification} className="rounded bg-slate-50 p-3 text-sm text-slate-600">{notification}</p>
                ))}
              </div>
            </div>
          </aside>

          <div className="space-y-6">
            <form onSubmit={saveProfile} className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xl font-black">Patient Profile</h2>
                <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={savingProfile}>
                  {savingProfile ? 'Saving...' : 'Save Profile'}
                </Button>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <TextField label="Full Name" value={profileForm.full_name} onChange={updateField('full_name')} required />
                <TextField label="Date of Birth" type="date" value={profileForm.date_of_birth} onChange={updateField('date_of_birth')} InputLabelProps={{ shrink: true }} />
                <TextField label="Sex" value={profileForm.sex} onChange={updateField('sex')} />
                <TextField label="Gender" value={profileForm.gender} onChange={updateField('gender')} />
                <TextField label="Blood Group" value={profileForm.blood_group} onChange={updateField('blood_group')} />
                <TextField label="Phone Number" value={profileForm.phone_number} onChange={updateField('phone_number')} />
                <TextField label="Address" value={profileForm.address} onChange={updateField('address')} />
                <TextField label="City" value={profileForm.city} onChange={updateField('city')} />
                <TextField label="State" value={profileForm.state} onChange={updateField('state')} />
                <TextField label="Country" value={profileForm.country} onChange={updateField('country')} />
                <TextField label="Emergency Contact Name" value={profileForm.emergency_contact_name} onChange={updateField('emergency_contact_name')} />
                <TextField label="Emergency Contact Phone" value={profileForm.emergency_contact_phone} onChange={updateField('emergency_contact_phone')} />
              </div>

              <div className="mt-4 grid gap-4 md:grid-cols-2">
                {[
                  ['medical_information', 'Medical Information'],
                  ['allergies', 'Allergies'],
                  ['medications', 'Medications'],
                  ['insurance', 'Insurance'],
                  ['lifestyle', 'Lifestyle'],
                  ['vaccination_history', 'Vaccination History'],
                ].map(([field, label]) => (
                  <TextField
                    key={field}
                    label={label}
                    value={profileForm[field as keyof ProfileForm]}
                    onChange={updateField(field as keyof ProfileForm)}
                    multiline
                    minRows={2}
                  />
                ))}
              </div>
            </form>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Profile Modules</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {[
                  { title: 'Personal Information', icon: <BadgeIcon />, items: [`Name: ${show(profile?.full_name)}`, `DOB: ${show(profileForm.date_of_birth)}`, `Sex/Gender: ${show(profileForm.sex || profileForm.gender)}`] },
                  { title: 'Medical History', icon: <HistoryIcon />, items: records.length ? records.slice(0, 2).map((record) => `${record.disease_key}: ${record.prediction}`) : ['No diagnosis records yet'] },
                  { title: 'Allergies', icon: <LocalHospitalIcon />, items: [show(profileForm.allergies)] },
                  { title: 'Medications', icon: <MedicationIcon />, items: [show(profileForm.medications)] },
                  { title: 'Lifestyle', icon: <MonitorHeartIcon />, items: [show(profileForm.lifestyle)] },
                  { title: 'Emergency Contact', icon: <ContactEmergencyIcon />, items: [`${show(profileForm.emergency_contact_name)} ${profileForm.emergency_contact_phone ? `(${profileForm.emergency_contact_phone})` : ''}`] },
                  { title: 'Insurance', icon: <BadgeIcon />, items: [show(profileForm.insurance)] },
                  { title: 'Vaccination History', icon: <VaccinesIcon />, items: [show(profileForm.vaccination_history)] },
                ].map((section) => (
                  <article key={section.title} className="rounded border border-slate-200 bg-slate-50 p-4">
                    <div className="flex items-center gap-2">
                      <span className="text-trust-teal">{section.icon}</span>
                      <h3 className="font-black text-slate-950">{section.title}</h3>
                    </div>
                    <ul className="mt-3 space-y-2 text-sm text-slate-600">
                      {section.items.map((item) => <li key={item} className="break-words">{item}</li>)}
                    </ul>
                  </article>
                ))}
              </div>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Diagnosis History</h2>
              <div className="mt-4 space-y-3">
                {timeline.length ? timeline.map((record) => (
                  <article key={record.diagnosis_id} className="rounded border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="font-black capitalize">{record.disease_key.replace(/_/g, ' ')}</p>
                        <p className="mt-1 text-sm text-slate-600">Result: {record.prediction.replace(/_/g, ' ')}</p>
                        <p className="mt-1 text-sm text-slate-500">Trust {(record.trust_score * 100).toFixed(1)}% | Confidence {(record.confidence * 100).toFixed(1)}%</p>
                      </div>
                      <div className="flex flex-col items-start gap-2 sm:items-end">
                        <p className="text-sm text-slate-500">{new Date(record.created_at).toLocaleString()}</p>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={downloadingId === record.diagnosis_id ? <CircularProgress size={14} /> : <DownloadIcon />}
                          onClick={() => downloadReport(record)}
                          disabled={downloadingId === record.diagnosis_id}
                        >
                          {downloadingId === record.diagnosis_id ? 'Downloading...' : 'Download Report'}
                        </Button>
                      </div>
                    </div>
                  </article>
                )) : (
                  <p className="rounded bg-slate-50 p-6 text-slate-500">No diagnosis timeline yet.</p>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

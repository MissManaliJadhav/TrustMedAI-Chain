import { FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, MenuItem, TextField } from '@mui/material';
import Header from '../components/Header';
import { api } from '../api/client';

const signupRoles = [
  { value: 'PATIENT', label: 'Patient' },
  { value: 'DOCTOR', label: 'Doctor' },
  { value: 'SUPER_ADMIN', label: 'Admin' },
];

export default function SignupPage() {
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [createdRole, setCreatedRole] = useState('PATIENT');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    const data = new FormData(event.currentTarget);
    const role = String(data.get('role') ?? 'PATIENT');
    try {
      await api.post('/auth/signup', {
        full_name: data.get('full_name'),
        email: data.get('email'),
        password: data.get('password'),
        role,
      });
      setCreatedRole(role);
      setDone(true);
    } catch {
      setError('Signup failed. Try another email.');
    }
  };

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-md px-4 py-12">
        <form onSubmit={submit} className="grid gap-4 rounded border border-slate-200 bg-white p-6 shadow-panel">
          <h1 className="text-2xl font-black">Signup</h1>
          {done && <Alert severity="success">{createdRole.replace('_', ' ')} account created. You can login now.</Alert>}
          {error && <Alert severity="error">{error}</Alert>}
          <TextField name="full_name" label="Full name" required />
          <TextField name="email" label="Email" type="email" required />
          <TextField name="password" label="Password" type="password" required />
          <TextField name="role" label="Role" select defaultValue="PATIENT" required>
            {signupRoles.map((role) => (
              <MenuItem key={role.value} value={role.value}>{role.label}</MenuItem>
            ))}
          </TextField>
          <Alert severity="info">Choose the role you want to use locally: patient, doctor, or admin.</Alert>
          <Button type="submit" variant="contained">Create Account</Button>
          <Link className="text-sm" to="/login">Already have an account?</Link>
        </form>
      </main>
    </div>
  );
}

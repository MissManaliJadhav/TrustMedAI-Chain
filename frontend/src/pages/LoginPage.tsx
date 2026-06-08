import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Alert, Button, TextField } from '@mui/material';
import Header from '../components/Header';
import { api } from '../api/client';
import { setCredentials } from '../store/authSlice';
import { useAppDispatch } from '../store';

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    const data = new FormData(event.currentTarget);
    try {
      const res = await api.post('/auth/login', {
        email: data.get('email'),
        password: data.get('password'),
      });
      dispatch(setCredentials({ accessToken: res.data.access_token, refreshToken: res.data.refresh_token, role: res.data.role }));
      navigate('/dashboard');
    } catch {
      setError('Invalid credentials.');
    }
  };

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-md px-4 py-12">
        <form onSubmit={submit} className="grid gap-4 rounded border border-slate-200 bg-white p-6 shadow-panel">
          <h1 className="text-2xl font-black">Login</h1>
          {error && <Alert severity="error">{error}</Alert>}
          <TextField name="email" label="Email" type="email" defaultValue="admin@trustmedai.local" required />
          <TextField name="password" label="Password" type="password" defaultValue="ChangeMe123!" required />
          <Button type="submit" variant="contained">Login</Button>
          <div className="flex justify-between text-sm">
            <Link to="/forgot-password">Forgot password</Link>
            <Link to="/signup">Create account</Link>
          </div>
        </form>
      </main>
    </div>
  );
}

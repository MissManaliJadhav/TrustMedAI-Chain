import { FormEvent, useState } from 'react';
import { Alert, Button, TextField } from '@mui/material';
import Header from '../components/Header';
import { api } from '../api/client';

export default function ForgotPasswordPage() {
  const [done, setDone] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await api.post('/auth/forgot-password', { email: data.get('email') });
    setDone(true);
  };

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-md px-4 py-12">
        <form onSubmit={submit} className="grid gap-4 rounded border border-slate-200 bg-white p-6 shadow-panel">
          <h1 className="text-2xl font-black">Forgot Password</h1>
          {done && <Alert severity="success">Reset workflow accepted.</Alert>}
          <TextField name="email" label="Email" type="email" required />
          <Button type="submit" variant="contained">Send Reset Link</Button>
        </form>
      </main>
    </div>
  );
}

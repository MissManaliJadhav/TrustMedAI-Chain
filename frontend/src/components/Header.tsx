import { Link, useNavigate } from 'react-router-dom';
import { Button } from '@mui/material';
import LogoutIcon from '@mui/icons-material/Logout';
import LoginIcon from '@mui/icons-material/Login';
import { logout } from '../store/authSlice';
import { useAppDispatch, useAppSelector } from '../store';

export default function Header() {
  const token = useAppSelector((state) => state.auth.accessToken);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const handleLogout = () => {
    dispatch(logout());
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-30 border-b border-teal-900/10 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-3 text-lg font-bold text-trust-ink no-underline">
          <span className="grid h-9 w-9 place-items-center rounded bg-trust-teal text-white">T</span>
          TrustMedAI-Chain
        </Link>
        <nav className="flex items-center gap-2">
          <Button component={Link} to="/dashboard" color="primary">
            Dashboard
          </Button>
          {token && (
            <Button component={Link} to="/diagnosis" color="primary">
              Disease Diagnosis
            </Button>
          )}
          {token ? (
            <Button startIcon={<LogoutIcon />} variant="outlined" onClick={handleLogout}>
              Logout
            </Button>
          ) : (
            <Button component={Link} to="/login" startIcon={<LoginIcon />} variant="contained">
              Login
            </Button>
          )}
        </nav>
      </div>
    </header>
  );
}

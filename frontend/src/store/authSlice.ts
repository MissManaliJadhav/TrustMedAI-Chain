import { PayloadAction, createSlice } from '@reduxjs/toolkit';

type Role = 'SUPER_ADMIN' | 'HOSPITAL_ADMIN' | 'DOCTOR' | 'PATIENT' | 'RESEARCHER';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  role: Role | null;
}

const initialState: AuthState = {
  accessToken: localStorage.getItem('trustmedai_access'),
  refreshToken: localStorage.getItem('trustmedai_refresh'),
  role: (localStorage.getItem('trustmedai_role') as Role | null) ?? null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials(state, action: PayloadAction<{ accessToken: string; refreshToken: string; role: Role }>) {
      state.accessToken = action.payload.accessToken;
      state.refreshToken = action.payload.refreshToken;
      state.role = action.payload.role;
      localStorage.setItem('trustmedai_access', action.payload.accessToken);
      localStorage.setItem('trustmedai_refresh', action.payload.refreshToken);
      localStorage.setItem('trustmedai_role', action.payload.role);
    },
    logout(state) {
      state.accessToken = null;
      state.refreshToken = null;
      state.role = null;
      localStorage.removeItem('trustmedai_access');
      localStorage.removeItem('trustmedai_refresh');
      localStorage.removeItem('trustmedai_role');
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;

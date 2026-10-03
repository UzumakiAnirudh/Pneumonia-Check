import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { safeNext, useAuth } from '@/features/auth/authStore';
import { passwordChecks } from '@/features/auth/password';
import { RequireAuth } from '@/features/auth/RequireAuth';
import { LoginPage } from '@/pages/LoginPage';
import { api } from '@/api/client';
import { ApiError } from '@/api/types';

describe('safeNext', () => {
  it('only allows same-site relative paths', () => {
    expect(safeNext('/history')).toBe('/history');
    expect(safeNext('//evil.example')).toBe('/analyze');
    expect(safeNext('https://evil.example')).toBe('/analyze');
    expect(safeNext(null)).toBe('/analyze');
  });
});

describe('passwordChecks', () => {
  it('mirrors the backend rules', () => {
    expect(passwordChecks('short1').every((c) => c.ok)).toBe(false);
    expect(passwordChecks('lettersonly').every((c) => c.ok)).toBe(false);
    expect(passwordChecks('s3cure-pass').every((c) => c.ok)).toBe(true);
  });
});

describe('RequireAuth', () => {
  it('redirects anonymous users to login, remembering the destination', () => {
    useAuth.setState({ user: null, status: 'anonymous' });
    render(
      <MemoryRouter initialEntries={['/history']}>
        <Routes>
          <Route path="/history" element={<RequireAuth>secret history</RequireAuth>} />
          <Route path="/login" element={<p>login page</p>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('login page')).toBeInTheDocument();
    expect(screen.queryByText('secret history')).not.toBeInTheDocument();
  });

  it('renders the page for a signed-in user', () => {
    useAuth.setState({
      user: { id: '1', name: 'Dr A', email: 'a@b.co', created_at: '' },
      status: 'authenticated',
    });
    render(
      <MemoryRouter initialEntries={['/history']}>
        <Routes>
          <Route path="/history" element={<RequireAuth>secret history</RequireAuth>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('secret history')).toBeInTheDocument();
  });
});

describe('LoginPage', () => {
  it('shows the server error for wrong credentials', async () => {
    useAuth.setState({ user: null, status: 'anonymous' });
    vi.spyOn(api, 'login').mockRejectedValueOnce(
      new ApiError(401, { code: 'invalid_credentials', message: 'Incorrect email or password.' }),
    );
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    );
    await userEvent.type(screen.getByLabelText('Email'), 'a@b.co');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-pass1');
    await userEvent.click(screen.getByRole('button', { name: /log in/i }));
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Incorrect email or password.'),
    );
  });
});

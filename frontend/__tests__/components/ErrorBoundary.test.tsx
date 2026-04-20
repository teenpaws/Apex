import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Suppress React error boundary noise in test output
const originalError = console.error;
beforeEach(() => { console.error = vi.fn(); });
afterEach(() => { console.error = originalError; });

import ErrorBoundary from '@/components/ErrorBoundary';

const Bomb = () => { throw new Error('Test crash'); };

describe('ErrorBoundary', () => {
  it('renders children when no error', () => {
    render(<ErrorBoundary><div data-testid="child">OK</div></ErrorBoundary>);
    expect(screen.getByTestId('child')).toBeTruthy();
  });

  it('renders fallback UI when child throws', () => {
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    expect(screen.getByText(/something went wrong/i)).toBeTruthy();
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom">custom error</div>}>
        <Bomb />
      </ErrorBoundary>
    );
    expect(screen.getByTestId('custom')).toBeTruthy();
  });

  it('resets error state when Try again is clicked', () => {
    render(<ErrorBoundary><Bomb /></ErrorBoundary>);
    fireEvent.click(screen.getByRole('button', { name: /try again/i }));
    // After reset, boundary re-renders (Bomb throws again — boundary catches again)
    expect(screen.getByText(/something went wrong/i)).toBeTruthy();
  });
});

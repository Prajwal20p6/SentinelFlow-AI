import '@testing-library/jest-dom'

jest.mock('next/navigation', () => ({
  useRouter() {
    return {
      prefetch: () => null,
      push: () => null,
      replace: () => null,
      back: () => null,
      forward: () => null,
    };
  },
  usePathname() {
    return '/dashboard';
  },
  useSearchParams() {
    return new URLSearchParams();
  },
}));

"use client";

import { AuthProvider, useAuth } from "@/components/AuthProvider";
import { Dashboard } from "@/components/Dashboard";
import { LoginForm } from "@/components/LoginForm";

function Gate() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-ink-muted text-sm">Loading…</p>
      </div>
    );
  }

  return user ? <Dashboard /> : <LoginForm />;
}

export default function Page() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  );
}

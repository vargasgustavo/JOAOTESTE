"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { api } from "@/lib/api";
import type { User } from "@/lib/types";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") ?? "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const user = await api.post<User>("/auth/login", { email, password });
      const fallback = user.role === "STAFF" ? "/staff" : "/admin";
      router.push(next || fallback);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel entrar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h1>Entrar</h1>
      <p className="subtitle">Acesso para equipe do restaurante.</p>
      <form className="form" onSubmit={submit}>
        <label>
          E-mail
          <input
            type="email"
            name="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Senha
          <input
            type="password"
            name="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error ? <p className="error">{error}</p> : null}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </section>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="muted">Carregando...</p>}>
      <LoginForm />
    </Suspense>
  );
}

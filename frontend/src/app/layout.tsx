import type { Metadata } from "next";
import Link from "next/link";

import { ToastProvider } from "@/components/Toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mesas e Filas",
  description: "Gestao de mesas e filas para restaurantes",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <ToastProvider>
          <header className="topbar">
            <Link href="/" className="brand">
              Mesas &amp; Filas
            </Link>
            <nav>
              <Link href="/">Restaurantes</Link>
              <Link href="/staff">Salao</Link>
              <Link href="/admin">Admin</Link>
            </nav>
          </header>
          <main className="container">{children}</main>
        </ToastProvider>
      </body>
    </html>
  );
}

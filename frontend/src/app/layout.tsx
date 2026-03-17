import type { Metadata } from 'next';
import { Space_Grotesk, Instrument_Sans } from 'next/font/google';
import '@/styles/globals.css';
import ClientProviders from './providers';

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Briefwave',
  description: 'Global drone & AI news intelligence platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className={`${spaceGrotesk.variable} ${instrumentSans.variable}`}>
      <body className="font-body antialiased bg-bg min-h-screen">
        <ClientProviders>
          {children}
        </ClientProviders>
      </body>
    </html>
  );
}

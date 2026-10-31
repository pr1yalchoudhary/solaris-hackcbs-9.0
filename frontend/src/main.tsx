import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

function App() {
  const [status, setStatus] = useState('Checking API…');
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${import.meta.env.VITE_API_BASE_URL || '/api'}/health`, { signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('API unavailable');
        const data = await response.json();
        if (data.status !== 'ok') throw new Error('Unexpected response');
        setStatus('API connected');
      })
      .catch(error => { if (error.name !== 'AbortError') setStatus('API offline · start FastAPI on port 8000'); });
    return () => controller.abort();
  }, []);
  return <main className="mx-auto max-w-5xl px-6 py-16 md:py-28">
    <p className="text-sm uppercase tracking-[0.3em] text-amber-300">HackCBS 2026</p>
    <h1 className="mt-5 text-6xl font-semibold tracking-tight md:text-8xl">Solaris<span className="text-amber-300">.</span></h1>
    <p className="mt-6 max-w-xl text-xl text-slate-300">The foundation for smarter solar decisions.</p>
    <p role="status" className="mt-8 inline-block rounded-full border border-slate-600 px-4 py-2 text-sm">{status}</p>
    <section className="mt-16 grid gap-4 md:grid-cols-3" aria-label="Project foundation">
      {[
        ['Data foundation', 'MongoDB Atlas through FastAPI. Configuration required.'],
        ['Optimisation', 'OR-Tools CP-SAT installed for local modelling.'],
        ['SmartExit', 'Consent-led exit planning. No automatic ownership or VNM allocation changes.'],
      ].map(([title, description]) => <article key={title} className="rounded-2xl border border-slate-700 bg-slate-900 p-6"><h2 className="text-lg font-medium">{title}</h2><p className="mt-3 text-sm leading-6 text-slate-400">{description}</p></article>)}
    </section>
    <p className="mt-8 text-sm text-slate-400">Local development · No live AI calls · Authentication setup pending</p>
  </main>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);

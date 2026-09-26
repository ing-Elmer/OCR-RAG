import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from '@/app/App';
import '@/styles/global.css';

const contenedor = document.getElementById('root');
if (!contenedor) {
  throw new Error('No se encontró el elemento #root en index.html.');
}

createRoot(contenedor).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
